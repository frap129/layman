"""
Copyright 2022 Joe Maples <joe@maples.dev>
Copyright: 2019-2021 Piotr Miller & Contributors

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


class GridLayoutManager(WorkspaceLayoutManager):
    shortName = "Grid"

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
        newLayout = "splitv" if window.rect.height > window.rect.width else "splith"
        result = self.con.command(("[con_id=%d]" % window.id) + newLayout)
        if result[0].success:
            self.log("Switched to %s" % newLayout)
        elif self.debug:
            self.log("Error: Switch failed with err {}".format(result[0].error))


    def moveWindow(self, moveId, targetId):
        self.con.command("[con_id=%d] mark --add move_target" % targetId)
        self.con.command("[con_id=%d] move window to mark move_target" % moveId)
        self.con.command("[con_id=%d] unmark move_target" % targetId)
        self.logCaller("Moved window %s to mark on window %s" % (moveId, targetId))


    def windowAdded(self, event, window):
        if self.isExcluded(window):
            return

        # Find largest container
        leaves = self.getWorkspaceCon().leaves()
        largestCon = window.parent
        conSize = window.parent.rect.height + window.parent.rect.width
        for leaf in leaves:
            if leaf.parent.id == window.parent.id:
                continue

            if (leaf.rect.height + leaf.rect.width) > conSize:
                # Split the largest container
                largestCon = leaf
                conSize = leaf.rect.height + leaf.rect.width
            elif largestCon is not None and (leaf.rect.height + leaf.rect.width) == conSize:
                # If multiple containers are the largest, select left most first and top most second
                moreLeft = leaf.rect.x < largestCon.rect.x
                sameLeftHigher = leaf.rect.x == largestCon.rect.x and leaf.rect.y < largestCon.rect.y
                if moreLeft or sameLeftHigher:
                    largestCon = leaf
                    conSize = leaf.rect.height + leaf.rect.width

        # Split largest container, move new window to it
        if largestCon is not None and largestCon.id != window.parent.id:
            self.switchSplit(largestCon)
            self.moveWindow(window.id, largestCon.id)

        self.switchSplit(window)


    def windowFocused(self, event, window):
        if self.isExcluded(window):
            return

        self.switchSplit(window)


