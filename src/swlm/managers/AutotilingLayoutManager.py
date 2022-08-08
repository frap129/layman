"""
Copyright: 2019-2021 Piotr Miller & Contributors
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
from managers.WorkspaceLayoutManager import WorkspaceLayoutManager
import utils

# AutolingLayoutManager, adapted from nwg-piotr's autotiling script
class AutotilingLayoutManager(WorkspaceLayoutManager):
    shortName = "Autotiling"

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
            elif debug:
                self.log("Error: Switch failed with err {}".format(result[0].error))


    def windowAdded(self, event, window):
        self.switchSplit(window)


    def windowRemoved(self, event, window):
        self.switchSplit(window)


    def windowFocused(self, event, window):
        self.switchSplit(window)


    def windowMoved(self, event, window):
        self.switchSplit(window)
