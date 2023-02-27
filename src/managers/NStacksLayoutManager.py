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
from collections import deque

from .WorkspaceLayoutManager import WorkspaceLayoutManager


def moveWindow(conn, moveId, targetId):
    conn.command("[con_id=%d] mark --add move_target" % targetId)
    conn.command("[con_id=%d] move window to mark move_target" % moveId)
    conn.command("[con_id=%d] unmark move_target" % targetId)


class NStacksLayoutManager(WorkspaceLayoutManager):
    shortName = "NStacks"
    overridesMoveBinds = True

    class Stack(WorkspaceLayoutManager):
        order = 0
        newOnTop = True
        maxCount = 0
        layout = "splitv"
        conId = 0
        windowIds = deque([])

        def __init__(self, con, workspace, options):
            super().__init__(con, workspace, options)


        def windowAdded(self, event, window):
            if window.id in self.windowIds:
                # Don't duplicate window records
                return

            # Initialize stack if needed
            if self.conId == 0:
                self.conId = window.id
                self.con.command("[con_id=%d] layout %s" % (self.conId, self.layout))
                stackCon = self.getConById(self.conId)
                window = stackCon.nodes[0]

            stackCon = self.getConById(self.conId)
            if stackCon.layout != self.layout:
                self.con.command("[con_id=%d] layout %s" % (self.conId, self.layout))

            self.windowIds.append(window.id)
            moveWindow(self.con, window.id, self.conId)
            if self.newOnTop and len(self.windowIds) > 1:
                self.moveToTopOfStack(window.id)

        def windowRemoved(self, windowId):
            try:
                self.windowIds.remove(windowId)

                # Reset stack if empty
                if len(self.windowIds) == 0:
                    self.conId = 0
            except:
                # Not in stack
                self.log("idk")

        def moveToTopOfStack(self, windowId):
            # The top of a tabbed layout is the closest to master, handle that
            moveDirection = "up"
            topIndex = 0
            if self.layout == "tabbed":
                moveDirection = "left"

            # Get stack container
            try:
                stackCon = self.getConById(windowId).parent
            except AttributeError:
                # Window not in stack
                self.moveWindow(windowId, self.windowIds[0])
                stackCon = self.getConById(windowId).parent

            # Move the previous master to top of stack
            while stackCon is not None and stackCon.nodes[topIndex].id != windowId:
                self.con.command("[con_id=%d] move %s" % (windowId, moveDirection))
                stackCon = self.getConById(windowId).parent
                if stackCon.id != self.conId:
                    self.moveWindow(windowId, self.conId)
                    stackCon = self.getConById(self.conId)


    def __init__(self, con, workspace, options):
        super().__init__(con, workspace, options)
        self.stackCount = 2
        self.stacks = []

        for i in range(self.stackCount):
            newStack = self.Stack(con, workspace, options)
            newStack.order = i
            self.stacks.append(newStack)

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


    def windowFocused(self, event, window):
        topCon = self.getWorkspaceCon()

        if len(topCon.nodes) < self.stackCount:
            # New windows should be new stacks
            self.con.command("[con_id=%d] layout none" % window.id)
            self.con.command("[con_id=%d] layout splith" % topCon.id)


    def windowAdded(self, event, window):
        # Ignore excluded windows
        if self.isExcluded(window):
            return

        topCon = self.getWorkspaceCon()

        if len(topCon.nodes) < self.stackCount:
            self.stacks[0].windowAdded(event, window)


    def windowRemoved(self, event, window):
         # Ignore excluded windows
        if self.isExcluded(window):
            return

        topCon = self.getWorkspaceCon()
        self.popWindow(window, topCon)

        self.log("Removed window id: %d" % window.id)


    def popWindow(self, window, topCon):
        leaves = topCon.leaves()
        leafIds = []

        for leaf in leaves:
            leafIds.append(leaf.id)

        leafIds = set(leafIds)

        for stack in self.stacks:
            missingWindows = list(set(stack.windowIds) - leafIds)
            if len(missingWindows) > 0:
                for id in missingWindows:
                    stack.windowRemoved(id)
                break
