"""
Copyright: 2019-2021 Piotr Miller & Contributors
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
from .WorkspaceLayoutManager import WorkspaceLayoutManager

KEY_DEPTH_LIMIT = "depthLimit"

# AutolingLayoutManager, adapted from nwg-piotr's autotiling script
class FibonacciLayoutManager(WorkspaceLayoutManager):
    shortName = "Fibonacci"

    def __init__(self, con, workspace, options):
        super().__init__(con, workspace, options)

    def isExcluded(self, window):
        if window is None:
            return True

        if window.type != "con":
            return True

        if window.workspace() is None:
            return True

        if window.floating is not None and "on" in window.floating:
            return True

        if window.fullscreen_mode == 1:
            return True

        if window.parent.layout == "stacked":
            return True

        if window.parent.layout == "tabbed":
            return True

        return False

    def switchSplit(self, window):
        if self.isExcluded(window):
            return

        newLayout = "splitv" if window.rect.height > window.rect.width else "splith"
        if newLayout != window.parent.layout:
            result = self.con.command(newLayout)
            if result[0].success:
                self.log("Switched to %s" % newLayout)
            elif self.debug:
                self.log("Error: Switch failed with err {}".format(result[0].error))

    def checkSplit(self, windowId, parentNumChildren):
        window = self.getConById(windowId)
        try:
            numChildren = len(window.nodes)
        except:
            numChildren = 0
        if numChildren == 0:
            return
        else:
            if numChildren == 1:
                return self.checkSplit(window.nodes[0], 1)
            if numChildren > 1:
                if numChildren > parentNumChildren:
                    parent = self.getConById(window.parent.id)
                    # Window removed in parent
                    self.moveWindow(window.nodes[0].id, parent.id)
                    self.reparentChildren(parent.id)
                    return self.checkSplit(window.nodes[1].id, 1)

                elif numChildren == 2:
                    return self.checkSplit(window.nodes[0], 2), self.checkSplit(window.nodes[1], 2)


    def reparentChildren(self, windowId):
        window = self.getConById(windowId)

        for node in window.nodes:
            if node.layout == window.layout:
                self.con.command("[con_id=%d] split toggle" % node.id)
            if len(node.nodes) > 0:
                self.reparentChildren(node.id)
        


    def windowAdded(self, event, window):
        self.switchSplit(window)


    def windowRemoved(self, event, window):
        self.checkSplit(self.workspaceId, 1)


    def windowFocused(self, event, window):
        self.switchSplit(window)


    def windowMoved(self, event, window):
        self.switchSplit(window)
