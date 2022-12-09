"""
Copyright 2022 Joe Maples <joe@maples.dev>

This file is part of layman.

layman is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

layman is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
layman. If not, see <https://www.gnu.org/licenses/>.
"""
from i3ipc import Connection
import threading
from time import sleep
from collections import deque

from .WorkspaceLayoutManager import WorkspaceLayoutManager

KEY_MASTER_WIDTH = "masterWidth"
KEY_STACK_LAYOUT = "stackLayout"
KEY_STACK_SIDE = "stackSide"


class MasterStackLayoutManager(WorkspaceLayoutManager):
    shortName = "MasterStack"
    overridesMoveBinds = True
    # Lock to prevent multiple instances from arranging at once
    arranging = threading.Lock()

    def __init__(self, con, workspace, options):
        super().__init__(con, workspace, options)
        self.masterId = 0
        self.stackId = 0
        self.stack = deque([])
        self.masterWidth = options.getForWorkspace(self.workspaceNum, KEY_MASTER_WIDTH) or 50
        self.stackLayout = options.getForWorkspace(self.workspaceNum, KEY_STACK_LAYOUT) or "splitv"
        self.stackSide = options.getForWorkspace(self.workspaceNum, KEY_STACK_SIDE) or "right"

        # If windows exist, fit them into MasterStack
        self.pushEvent = threading.Event()
        self.arrangeUntrackedWindows()


    def windowAdded(self, event, window):
        # Ignore excluded windows
        if self.isExcluded(window):
            return

        topCon = self.getWorkspaceCon()
        self.pushWindow(window, topCon)

        self.log("Added window id: %d" % window.id)
        self.con.command("[con_id=%d] focus" % self.masterId)
        self.pushEvent.set() # Unblock the arrange thread


    def windowRemoved(self, event, window):
         # Ignore excluded windows
        if self.isExcluded(window):
            return

        topCon = self.getWorkspaceCon()
        self.popWindow(window, topCon)

        self.log("Removed window id: %d" % window.id)


    def windowFocused(self, event, window):
        # Ignore excluded windows
        if self.isExcluded(window):
            return

        # Make sure the focused window is visible
        if self.stackLayout != "splitv" and window.id in self.stack:
            self.con.command("focus child")


    def onBinding(self, command):
        if command == "nop layman move up":
            self.moveUp()
        elif command == "nop layman move down":
            self.moveDown()
        elif command == "nop layman rotate ccw" or command == "nop layman move left":
            self.rotateCCW()
        elif command == "nop layman rotate cw" or command == "nop layman move right":
            self.rotateCW()
        elif command == "nop layman swap master":
            self.swapMaster()
        elif command == "nop layman stack toggle":
            self.toggleStackLayout()
        elif command == "nop layman stackside toggle":
            self.toggleStackSide()


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


    def setStackLayout(self):
        if len(self.stack) != 0 and self.stackId != 0:
            self.con.command("[con_id=%d] layout %s" % (self.stackId, self.stackLayout))


    def moveWindow(self, moveId, targetId):
        self.con.command("[con_id=%d] mark --add move_target" % targetId)
        self.con.command("[con_id=%d] move window to mark move_target" % moveId)
        self.con.command("[con_id=%d] unmark move_target" % targetId)
        self.logCaller("Moved window %s to mark on window %s" % (moveId, targetId))


    def floatToggleUntrackedWindows(self):
        with MasterStackLayoutManager.arranging:
            conn = Connection()
            leaves = conn.get_tree().find_by_id(self.workspaceId).leaves()
            # Float all untracked windows
            for window in leaves:
                if window.id not in self.stack and window.id != self.masterId:
                    self.con.command("[con_id=%s] focus" % window.id)
                    self.con.command("floating enable")

            # Unfloat to simulate adding a window
            sleep(0.05)
            floating = conn.get_tree().find_by_id(self.workspaceId).floating_nodes
            for window in floating:
                self.con.command("[con_id=%s] focus" % window.id)
                self.con.command("floating disable")
                # Wait until the window is added
                self.pushEvent.clear()
                self.pushEvent.wait()


    def arrangeUntrackedWindows(self):
        '''
        Floating the windows causes layman to send window added/removed events since
        this layout doesnt support floating windows. By floating windows on a separate
        thread, we can reinsert them and let the layout handle them correctly. Doing
        this on the same thread would block the layout from handling events.
        '''
        thread = threading.Thread(target=self.floatToggleUntrackedWindows)
        thread.start()


    def pushWindow(self, window, topCon):
        leaves = topCon.leaves()
        masterCon = topCon.find_by_id(self.masterId)
        stackCon = topCon.find_by_id(self.stackId)
        if stackCon is None:
            if masterCon is None:
                if len(leaves) > 1:
                    # Something's not right, I can feel it
                    self.arrangeUntrackedWindows()
                elif leaves != 0:
                    # Only one window exists, make it master
                    self.masterId = leaves[0].id
                    self.con.command("[con_id=%d] layout %s" % (self.masterId, "splith"))
            else:
                # Only two windows, initialize stack. Start by getting master on the correct side
                swapRight = window.rect.x > masterCon.rect.x and self.stackSide == "right"
                swapLeft = window.rect.x < masterCon.rect.x and self.stackSide == "left"
                if swapLeft or swapRight:
                    self.con.command("[con_id=%d] swap container with con_id %d" % (window.id, masterCon.id))

                # Create stack container
                self.con.command("[con_id=%d] split vertical" % (masterCon.id))
                self.con.command("[con_id=%d] layout %s" % (masterCon.id, self.stackLayout))

                # Refresh masterCon for updated parent
                masterCon = self.getConById(masterCon.id)
                self.masterId = window.id
                self.stackId = masterCon.parent.id
                self.log("New stackId: %d" % self.stackId)
                self.stack.append(masterCon.id)
                self.setMasterWidth()
        elif masterCon is None:
            # No master, even though we have a stack for some reason.
            self.arrangeUntrackedWindows()
        elif topCon.nodes == 1 and len(leaves) > 1:
            # Layout is wrapped in another container, recurse
            self.pushWindow(window, topCon.nodes[0])
        else:
            if len(topCon.nodes) > 2:
                # New window in top container, move old master to stack
                self.moveWindow(self.masterId, self.stack[-1])
            elif len(leaves) > (len(self.stack) + 1):
                # New window in stack, swap with master
                self.con.command("[con_id=%d] swap container with con_id %d" % (window.id, self.masterId))

            # The top of a tabbed layout is the closest to master, handle that
            moveDirection = "up"
            topIndex = 0
            if self.stackLayout == "tabbed" and self.stackSide == "right":
                moveDirection = "left"
            elif self.stackLayout == "tabbed" and self.stackSide == "left":
                moveDirection = "right"
                topIndex = -1

            # Move the previous master to top of stack
            stackCon = self.getConById(self.masterId).parent
            while stackCon is not None and stackCon.nodes[topIndex].id != self.masterId:
                self.con.command("[con_id=%d] move %s" % (self.masterId, moveDirection))
                stackCon = self.getConById(self.masterId).parent
                if stackCon.id != self.stackId:
                    self.moveWindow(self.masterId, self.stackId)
                    stackCon = self.getConById(self.stackId)

            self.stack.append(self.masterId)
            self.log("New window on stack: %d" % self.masterId)
            self.masterId = window.id
            self.setMasterWidth()


    def popWindow(self, window, topCon):
        leaves = topCon.leaves()
        masterCon = topCon.find_by_id(self.masterId)
        stackCon = topCon.find_by_id(self.stackId)
        if stackCon is None:
            if masterCon is None:
                if len(leaves) > 0:
                    # Something's not right, I can feel it
                    self.arrangeUntrackedWindows()
                else:
                    # No windows, clear everything
                    self.stack.clear()
                    self.stackId = 0
                    self.masterId = 0
            else:
                # Only one window remains
                self.log("Single window, making it master.")
                self.masterId = topCon.nodes[0].id
                self.stackId = 0
                self.stack.clear()
        elif masterCon is None:
            # Master destroyed, pop from stack
            self.masterId = self.stack.pop()
            self.log("Master removed, popping %d from stack." % self.masterId)
            if len(leaves) == 1:
                # Stack empty, make last window master
                self.con.command("[con_id=%d] layout splith" % self.masterId)
                self.moveWindow(self.masterId, self.workspaceId)
                self.stack.clear()
                self.stackId = 0
            else:
                moveDirection = "left" if self.stackSide == "right" else "right"
                self.con.command("[con_id=%id] focus")
                self.con.command("move %s" % moveDirection)
                self.setMasterWidth()
        elif topCon.nodes == 1 and len(leaves) > 1:
            # Layout is wrapped in another container, recurse
            self.popWindow(window, topCon.nodes[0])
        else:
            # A stack item was destroyed
            self.setMasterWidth()
            allWindowIds = {window.id for window in leaves}
            for id in self.stack:
                if id not in allWindowIds:
                    self.stack.remove(id)
                    break


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
        if len(self.stack) != 0:
            self.con.command("[con_id=%d] layout %s" % (self.stack[0], self.stackLayout))
            self.log("Changed stackLayout to %s" % self.stackLayout)


    def toggleStackSide(self):
        self.stackSide = "left" if self.stackSide == "right" else "right"
        stackCon = self.getConById(self.stackId)
        masterCon = self.getConById(self.masterId)
        moveToRight = stackCon.rect.x < masterCon.rect.x and self.stackSide == "right"
        moveToLeft = stackCon.rect.x > masterCon.rect.x and self.stackSide == "left"

        if stackCon is not None and masterCon is not None:
            if stackCon.rect.x == masterCon.rect.x:
                # Master has incorrect layout
                self.con.command("[con_id=%d] layout splith" % self.masterId)
            elif moveToLeft or moveToRight:
                self.con.command("[con_id=%d] swap container with con_id %d" % (self.stackId, self.masterId))
                self.setMasterWidth()


    def moveUp(self):
        focusedWindow = self.getFocusedCon()

        if focusedWindow is None:
            self.log("No window focused, can't move")
            return

        # Swap master and top of stack if only two windows, or focus is top of stack
        if len(self.stack) < 2 or focusedWindow.id == self.stack[-1]:
            targetId = self.stack.pop()
            self.con.command("[con_id=%d] swap container with con_id %d" % (targetId, self.masterId))
            self.stack.append(self.masterId)
            self.masterId = targetId
            self.log("Swapped window %d with master" % targetId)
            return

        # Swap window with window above
        try:
            index = self.stack.index(focusedWindow.id)
        except ValueError:
            self.log("Window %d not found in stack" % focusedWindow.id)
            return

        self.con.command("[con_id=%d] swap container with con_id %d" % (focusedWindow.id, self.stack[index+1]))
        self.stack[index] = self.stack[index+1]
        self.stack[index+1] = focusedWindow.id
        self.log("Swapped window %d with %d" % (focusedWindow.id, self.stack[index]))


    def moveDown(self):
        # Check if stack only has one window
        if len(self.stack) < 2:
            return

        focusedWindow = self.getFocusedCon()
        if focusedWindow is None:
            self.log("No window focused, can't move")
            return

        # Check if we hit bottom of stack
        if focusedWindow.id == self.stack[0]:
            self.log("Bottom of stack, nowhere to go")
            return

        # Swap with top of stack if master is focused
        if focusedWindow.id == self.masterId:
            self.con.command("[con_id=%d] swap container with con_id %d" % (focusedWindow.id, self.stack[-1]))
            self.masterId = self.stack.pop()
            self.stack.append(focusedWindow.id)
            self.log("Swapped master %d with top of stack %d" % (self.stack[-1], self.masterId))
            return

        # Swap window with window below
        try:
            index = self.stack.index(focusedWindow.id)
        except ValueError:
            self.log("Window %d not found in stack" % focusedWindow.id)
            return

        self.con.command("[con_id=%d] swap container with con_id %d" % (focusedWindow.id, self.stack[index-1]))
        self.stack[index] = self.stack[index-1]
        self.stack[index-1] = focusedWindow.id
        self.log("Swapped window %d with %d" % (focusedWindow.id, self.stack[index]))


    def rotateCCW(self):
        # Exit if less than three windows
        if len(self.stack) < 2:
            self.log("Only 2 windows, can't rotate")
            return

        # Swap top of stack with master, then move old master to bottom
        newMasterId = self.stack.pop()
        prevMasterId = self.masterId
        bottomId = self.stack[0]
        self.con.command("[con_id=%d] swap container with con_id %d" % (newMasterId, prevMasterId))
        self.log("swapped top of stack with master")
        self.moveWindow(prevMasterId, bottomId)
        self.log("Moved previous master to bottom of stack")
        self.con.command("[con_id=%d] focus" % newMasterId)

        # Update record
        self.masterId = newMasterId
        self.stack.appendleft(prevMasterId)


    def rotateCW(self):
        # Exit if less than three windows
        if len(self.stack) < 2:
            self.log("Only 2 windows, can't rotate")
            return

        # Swap bottom of stack with master, then move old master to top
        newMasterId = self.stack.popleft()
        prevMasterId = self.masterId
        topId = self.stack[-1]
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
        self.stack.append(prevMasterId)


    def swapMaster(self):
        # Exit if less than two windows
        if len(self.stack) == 0:
            self.log("Stack emtpy, can't swap")
            return

        focusedWindow = self.getFocusedCon()

        if focusedWindow is None:
            self.log("No window focused, can't swap")
            return

        # If focus is master, swap with top of stack
        if focusedWindow.id == self.masterId:
            targetId = self.stack.pop()
            self.con.command("[con_id=%d] swap container with con_id %d" % (targetId, self.masterId))
            self.stack.append(self.masterId)
            self.masterId = targetId
            self.log("Swapped master with top of stack")
            self.con.command("[con_id=%d] focus" % self.masterId)
            return

        # Find focused window in record
        for i in range(len(self.stack)):
            if self.stack[i] == focusedWindow.id:
                # Swap window with master
                self.con.command("[con_id=%d] swap container with con_id %d" % (focusedWindow.id, self.masterId))

                # Update record
                self.stack[i] = self.masterId
                self.masterId = focusedWindow.id
                self.log("Swapped master with window %d" % focusedWindow.id)

                # Refocus master
                self.con.command("[con_id=%d] focus" % self.masterId)
                return
