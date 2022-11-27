"""
Copyright 2022 Joe Maples <joe@maples.dev>

This file is part of swlm.

swlm is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

swlm is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
swlm. If not, see <https://www.gnu.org/licenses/>.
"""
from collections import deque

from managers.WorkspaceLayoutManager import WorkspaceLayoutManager
import utils

KEY_MASTER_WIDTH = "masterWidth"
KEY_STACK_LAYOUT = "stackLayout"


class MasterStackLayoutManager(WorkspaceLayoutManager):
    shortName = "MasterStack"
    overridesMoveBinds = True

    def __init__(self, con, workspace, options):
        super().__init__(con, workspace, options)
        self.masterId = 0
        self.stackConId = 0
        self.stackIds = deque([])
        self.masterWidth = options.getForWorkspace(self.workspaceNum, KEY_MASTER_WIDTH) or 50
        self.stackLayout = options.getForWorkspace(self.workspaceNum, KEY_STACK_LAYOUT) or "splitv"

        # Handle window if it's not currently being tracked
        self.arrangeExistingLayout()


    def windowAdded(self, event, window):
        # Ignore excluded windows
        if self.isExcluded(window):
            return

        # New window replaces master, master gets pushed to stack
        self.log("Added window id: %d" % window.id)
        self.pushWindow(window.id)


    def windowRemoved(self, event, window):
        if self.masterId == window.id:
            # If window is master, pop the next one off the stack
            self.popWindow()
        else:
            # If window is not master, remove from stack and exist
            try:
                self.stackIds.remove(window.id)
            except BaseException:
                # This should only happen if an untracked window was closed
                self.log("WTF: window not master or in stack")

        self.log("Removed window id: %d" % window.id)


    def windowFocused(self, event, window):
        # Ignore excluded windows
        if self.isExcluded(window):
            return

        # Make sure the focused window is visible
        if self.stackLayout != "splitv" and window.id in self.stackIds:
            self.con.command("focus child")


    def onBinding(self, command):
        if command == "nop swlm move up":
            self.moveUp()
        elif command == "nop swlm move down":
            self.moveDown()
        elif command == "nop swlm rotate ccw" or command == "nop swlm move left":
            self.rotateCCW()
        elif command == "nop swlm rotate cw" or command == "nop swlm move right":
            self.rotateCW()
        elif command == "nop swlm swap master":
            self.swapMaster()
        elif command == "nop swlm stack toggle":
            self.toggleStackLayout()


    def isExcluded(self, window):
        if window is None:
            return True

        if window.type != "con":
            return True

        workspace = window.workspace()

        if workspace is None:
            return True

        if window.floating is not None and "on" in window.floating:
            return True

        if workspace.floating_nodes is not None and any(node.id == window.id for node in workspace.floating_nodes):
            return True

        return False


    def setMasterWidth(self):
        if self.masterWidth is not None:
            self.con.command("[con_id=%s] resize set %s 0 ppt" % (self.masterId, self.masterWidth))
            self.logCaller("Set window %d width to %d" % (self.masterId, self.masterWidth))


    def moveWindow(self, moveId, targetId):
        self.con.command("[con_id=%d] mark --add move_target" % targetId)
        self.con.command("[con_id=%d] move window to mark move_target" % moveId)
        self.con.command("[con_id=%d] unmark move_target" % targetId)
        self.logCaller("Moved window %s to mark on window %s" % (moveId, targetId))


    def pushWindow(self, windowId):
        # Check if master is empty
        if self.masterId == 0:
            self.log("Made window %d master" % windowId)
            self.masterId = windowId
            self.setStackLayout()
            return

        # Check if we need to initialize the stack
        if len(self.stackIds) == 0:
            # Make sure the new window is in a valid position
            self.moveWindow(windowId, self.workspaceId)

            # Swap with master
            self.stackIds.append(self.masterId)
            self.con.command("[con_id=%d] swap container with con_id %d" % (windowId, self.masterId))
            prevMasterId = self.masterId
            self.masterId = windowId
            self.log("Initialized stack with %d, new master %d" % (self.stackIds[0], windowId))
            self.setMasterWidth()
            self.setStackLayout()

            # Get stack container id
            self.con.command("[con_id=%s] focus" % prevMasterId)
            self.con.command("focus parent")
            self.stackConId = utils.findFocusedWindow(self.con).id

            # Refocus Master
            self.con.command("[con_id=%s] focus" % windowId)
            return

        # Put new window at top of stack
        self.moveWindow(windowId, self.stackConId)
        if not self.stackLayout or self.stackLayout == "splitv":
            self.con.command("[con_id=%s] focus" % windowId)
            for i in range(len(self.stackIds)):
                self.con.command("move up")

        # Swap with master
        prevMasterId = self.masterId
        self.con.command("[con_id=%s] swap container with con_id %s" % (windowId, prevMasterId))
        self.stackIds.append(self.masterId)
        self.masterId = windowId
        self.con.command("[con_id=%s] focus" % windowId)


    def popWindow(self):
        # Check if last window is being popped
        if len(self.stackIds) == 0:
            self.masterId = 0
            self.log("Closed last window, nothing to do")
            return

        # Move top of stack to master position
        self.masterId = self.stackIds.pop()
        self.con.command("[con_id=%s] focus" % self.masterId)

        # If stack is not empty, we need to move the view to the master position
        if len(self.stackIds) != 0:
            if self.stackLayout != "tabbed":
                self.con.command("move left")
            else:
                self.con.command("move right")
                self.con.command("[con_id=%s] swap container with con_id %s" % (self.stackConId, self.masterId))
                self.con.command("[con_id=%s] focus" % self.masterId)

            self.setMasterWidth()

        self.log("Moved top of stack to master")


    def setStackLayout(self):
        self.con.command("[con_id=%d] layout %s" % (self.masterId, "splith"))
        if len(self.stackIds) != 0:
            bottom = self.stackIds[0]
            self.con.command("[con_id=%d] split vertical" % bottom)
            self.con.command("[con_id=%d] layout %s" % (bottom, self.stackLayout))


    def toggleStackLayout(self):
        # Pick next stack layout
        if self.stackLayout == "splitv":
            self.stackLayout = "tabbed"
        elif self.stackLayout == "tabbed":
            self.stackLayout = "stacking"
        elif self.stackLayout == "stacking":
            self.stackLayout = "splitv"
        else:
            return

        # Apply the new stack layout
        if len(self.stackIds) != 0:
            self.con.command("[con_id=%d] layout %s" % (self.stackIds[0], self.stackLayout))
            self.log("Changed stackLayout to %s" % self.stackLayout)


    def floatToggleAllWindows(self, container):
        for node in container.nodes:
            if node.nodes is not None and len(node.nodes) > 0:
                # Node is a container, float its children instead of the container
                self.floatToggleAllWindows(node)
            else:
                self.con.command("[con_id=%s] focus" % node.id)
                self.con.command("floating toggle")


    def arrangeExistingLayout(self):
        workspace = utils.findFocusedWindow(self.con).workspace()
        self.floatToggleAllWindows(workspace)

        workspace = utils.findFocusedWindow(self.con).workspace()
        for node in workspace.floating_nodes:
            self.con.command("[con_id=%s] focus" % node.id)
            self.con.command("floating tooggle")
            self.pushWindow(node.id)


    def moveUp(self):
        focusedWindow = utils.findFocusedWindow(self.con)

        if focusedWindow is None:
            self.log("No window focused, can't move")
            return

        # Swap master and top of stack if only two windows, or focus is top of stack
        if len(self.stackIds) < 2 or focusedWindow.id == self.stackIds[-1]:
            targetId = self.stackIds.pop()
            self.con.command("[con_id=%d] swap container with con_id %d" % (targetId, self.masterId))
            self.stackIds.append(self.masterId)
            self.masterId = targetId
            self.log("Swapped window %d with master" % targetId)
            return

        # Swap window with window above
        try:
            index = self.stackIds.index(focusedWindow.id)
        except ValueError:
            self.log("Window %d not found in stack" % focusedWindow.id)
            return

        self.con.command("[con_id=%d] swap container with con_id %d" % (focusedWindow.id, self.stackIds[index+1]))
        self.stackIds[index] = self.stackIds[index+1]
        self.stackIds[index+1] = focusedWindow.id
        self.log("Swapped window %d with %d" % (focusedWindow.id, self.stackIds[index]))


    def moveDown(self):
        # Check if stack only has one window
        if len(self.stackIds) < 2:
            return

        focusedWindow = utils.findFocusedWindow(self.con)
        if focusedWindow is None:
            self.log("No window focused, can't move")
            return

        # Check if we hit bottom of stack
        if focusedWindow.id == self.stackIds[0]:
            self.log("Bottom of stack, nowhere to go")
            return

        # Swap with top of stack if master is focused
        if focusedWindow.id == self.masterId:
            self.con.command("[con_id=%d] swap container with con_id %d" % (focusedWindow.id, self.stackIds[-1]))
            self.masterId = self.stackIds.pop()
            self.stackIds.append(focusedWindow.id)
            self.log("Swapped master %d with top of stack %d" % (self.stackIds[-1], self.masterId))
            return

        # Swap window with window below
        try:
            index = self.stackIds.index(focusedWindow.id)
        except ValueError:
            self.log("Window %d not found in stack" % focusedWindow.id)
            return

        self.con.command("[con_id=%d] swap container with con_id %d" % (focusedWindow.id, self.stackIds[index-1]))
        self.stackIds[index] = self.stackIds[index-1]
        self.stackIds[index-1] = focusedWindow.id
        self.log("Swapped window %d with %d" % (focusedWindow.id, self.stackIds[index]))


    def rotateCCW(self):
        # Exit if less than three windows
        if len(self.stackIds) < 2:
            self.log("Only 2 windows, can't rotate")
            return

        # Swap top of stack with master, then move old master to bottom
        newMasterId = self.stackIds.pop()
        prevMasterId = self.masterId
        bottomId = self.stackIds[0]
        self.con.command("[con_id=%d] swap container with con_id %d" % (newMasterId, prevMasterId))
        self.log("swapped top of stack with master")
        self.moveWindow(prevMasterId, bottomId)
        self.log("Moved previous master to bottom of stack")
        self.con.command("[con_id=%d] focus" % newMasterId)

        # Update record
        self.masterId = newMasterId
        self.stackIds.appendleft(prevMasterId)


    def rotateCW(self):
        # Exit if less than three windows
        if len(self.stackIds) < 2:
            self.log("Only 2 windows, can't rotate")
            return

        # Swap bottom of stack with master, then move old master to top
        newMasterId = self.stackIds.popleft()
        prevMasterId = self.masterId
        topId = self.stackIds[-1]
        self.con.command("[con_id=%d] swap container with con_id %d" % (newMasterId, prevMasterId))
        self.log("swapped bottom of stack with master")
        self.moveWindow(prevMasterId, topId)
        self.con.command("[con_id=%d] focus" % prevMasterId)
        if self.stackLayout != "tabbed":
            self.con.command("move up")
        else:
            self.con.command("move left")
        self.con.command("[con_id=%d] focus" % newMasterId)
        self.log("Moved previous master to top of stack")

        # Update record
        self.masterId = newMasterId
        self.stackIds.append(prevMasterId)


    def swapMaster(self):
        # Exit if less than two windows
        if len(self.stackIds) == 0:
            self.log("Stack emtpy, can't swap")
            return

        focusedWindow = utils.findFocusedWindow(self.con)

        if focusedWindow is None:
            self.log("No window focused, can't swap")
            return

        # If focus is master, swap with top of stack
        if focusedWindow.id == self.masterId:
            targetId = self.stackIds.pop()
            self.con.command("[con_id=%d] swap container with con_id %d" % (targetId, self.masterId))
            self.stackIds.append(self.masterId)
            self.masterId = targetId
            self.log("Swapped master with top of stack")
            return

        # Find focused window in record
        for i in range(len(self.stackIds)):
            if self.stackIds[i] == focusedWindow.id:
                # Swap window with master
                self.con.command("[con_id=%d] swap container with con_id %d" % (focusedWindow.id, self.masterId))

                # Update record
                self.stackIds[i] = self.masterId
                self.masterId = focusedWindow.id
                self.log("Swapped master with window %d" % focusedWindow.id)

                # Refocus master
                self.con.command("[con_id=%d] focus" % self.masterId)
                return
