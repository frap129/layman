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
class AutotilingLayoutManager(WorkspaceLayoutManager):
    shortName = "Autotiling"

    def __init__(self, con, workspace, options):
        super().__init__(con, workspace, options)
        self.depthLimit = options.getForWorkspace(self.workspaceNum, KEY_DEPTH_LIMIT) or 0

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

        if window.parent.layout != window.layout and len(window.parent.nodes) <= 1:
            return True

        return False

    def switchSplit(self, window):
        if self.isExcluded(window):
            return

        # Check if we've hit the depth limit before splitting
        if self.depthLimit:
            windowParent = window
            depth = 0
            while depth <= self.depthLimit:
                if windowParent.type != "workspace":
                    # Exit when depth limit is reached
                    if depth == self.depthLimit:
                        return

                    windowParent = windowParent.parent

                    # Only count depth of containers with more than 1 child
                    if len(windowParent.nodes) > 1:
                        depth += 1
                else:
                    # Top of workspace reached, continue to split
                    break

        newLayout = "splitv" if window.rect.height > window.rect.width else "splith"
        if newLayout != window.parent.layout:
            result = self.con.command(newLayout)
            if result[0].success:
                self.log("Switched to %s" % newLayout)
            elif self.debug:
                self.log("Error: Switch failed with err {}".format(result[0].error))


    def windowAdded(self, event, window):
        self.switchSplit(window)


    def windowRemoved(self, event, window):
        self.switchSplit(window)


    def windowFocused(self, event, window):
        self.switchSplit(window)


    def windowMoved(self, event, window):
        self.switchSplit(window)
