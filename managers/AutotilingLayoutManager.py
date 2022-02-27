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


    def switchSplit(self):
        focusedWindow = utils.findFocused(self.con)
        if focusedWindow is not None and focusedWindow.workspace().id == self.workspaceId:
            if focusedWindow.floating:
                # We're on i3: on sway it would be None
                # May be 'auto_on' or 'user_on'
                isFloating = "_on" in focusedWindow.floating
                isFullscreen = focusedWindow.fullscreen_mode == 1
            else:
                # We are on sway
                isFloating = focusedWindow.type == "floating_con"
                isFullscreen = focusedWindow.fullscreen_mode == 1

            isStacked = focusedWindow.parent.layout == "stacked"
            isTabbed = focusedWindow.parent.layout == "tabbed"

            # Exclude floating containers, stacked layouts, tabbed layouts and full screen mode
            if (not isFloating and not isStacked and not isTabbed and not isFullscreen):
                newLayout = "splitv" if focusedWindow.rect.height > focusedWindow.rect.width else "splith"

                if newLayout != focusedWindow.parent.layout:
                    result = self.con.command(newLayout)
                    if result[0].success:
                        self.log("switchSplit: Switched to %s" % newLayout)
                    elif debug:
                        self.log("switchSplit: Error: Switch failed with err {}".format(result[0].error))

        else :
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
