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
        priority = 0
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

            self.windowIds.append(window.id)
            moveWindow(self.conn, window.id, self.conId)
            if self.newOnTop:
                self.moveToTopOfStack(window.id)

        def windowRemoved(self, event, window):
            try:
                self.windowIds.remove(window.id)
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
                self.moveWindow(windowId, self.stack[0])
                stackCon = self.getConById(windowId).parent

            # Move the previous master to top of stack
            while stackCon is not None and stackCon.nodes[topIndex].id != windowId:
                self.con.command("[con_id=%d] move %s" % (windowId, moveDirection))
                stackCon = self.getConById(windowId).parent
                if stackCon.id != self.stackId:
                    self.moveWindow(windowId, self.stackId)
                    stackCon = self.getConById(self.stackId)


    def __init__(self, con, workspace, options):
        super().__init__(con, workspace, options)
        self.stackCount = 2
        self.stacks = []

        for i in range(self.stackCount):
            newStack = self.Stack(con, workspace, options)
            newStack.priority = i
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


    def windowAdded(self, event, window):
        # Ignore excluded windows
        if self.isExcluded(window):
            return


    def windowRemoved(self, event, window):
         # Ignore excluded windows
        if self.isExcluded(window):
            return

        topCon = self.getWorkspaceCon()
        self.popWindow(window, topCon)

        self.log("Removed window id: %d" % window.id)
