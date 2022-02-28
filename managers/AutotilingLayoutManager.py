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

# AutolingLayoutManager, adapted from nwg-piotr's autiling script
class AutotilingLayoutManager(WorkspaceLayoutManager):
    def __init__(self, con, workspace, options):
        self.con = con
        self.workspaceId = workspace.ipc_data["id"]
        self.workspaceNum = workspace.num
        self.debug = options.debug

    def isExcluded(self, window):
        if window is None:
            return True

        if window.type != "con":
            return True

        if window.workspace() is None:
            return True

        if window.floating is not None and "on" in window.floating:
            return True

        if window.type == "floating_con":
            return True

        if window.fullscreen_mode == 1:
            return True

        if window.parent.layout == "stacked":
            return True

        if window.parent.layout == "tabbed":
            return True

        return False

    def switchSplit(self):
        focusedWindow = utils.findFocused(self.con)
        if not self.isExcluded(focusedWindow) and focusedWindow.workspace().id == self.workspaceId:
            newLayout = "splitv" if focusedWindow.rect.height > focusedWindow.rect.width else "splith"
            if newLayout != focusedWindow.parent.layout:
                result = self.con.command(newLayout)
                if result[0].success:
                    self.log("switchSplit: Switched to %s" % newLayout)
                elif debug:
                    self.log("switchSplit: Error: Switch failed with err {}".format(result[0].error))
        else:
            self.log("switchSplit: No focused container found or autotiling on the workspace turned off")


    def windowCreated(self, event):
        self.switchSplit()


    def windowFocused(self, event):
        self.switchSplit()


    def windowClosed(self, event):
        self.switchSplit()


    def windowMoved(self, event):
        self.switchSplit()


    def binding(self, command):
        pass
