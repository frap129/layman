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
import inspect

from ..config import KEY_DEBUG

class WorkspaceLayoutManager:
    # These properties should be overriden to configure your WLM as
    # Needed
    shortName = "none"
    overridesMoveBinds = False # Should window movement commands be sent as binds
    supportsFloating = False # Should windowFloating be used, or treated as Added/Removed

    # These are the functions you should override for to implement a
    # WLM. 
    def __init__(self, con, workspace, options):
        self.con = con
        self.workspaceId = workspace.ipc_data["id"]
        self.workspaceNum = workspace.num
        self.debug = options.getForWorkspace(self.workspaceNum, KEY_DEBUG)


    # windowAdded is called when a new window is added to the workpsace,
    # either by being created on the workspace or moved to it from another.
    def windowAdded(self, event, window):
        pass


    # windowRemoved is called when a window is removed from the workspace,
    # either by being closed or moved to a different workspace.
    def windowRemoved(self, event, window):
        pass


    # windowFocused is called when a window on the workpsace is focused.
    def windowFocused(self, event, window):
        pass


    # windowMoved is called when a window is moved, but stays on the same
    # workspace.
    def windowMoved(self, event, window):
        pass

    # windowFloating is called when a windows floating state is toggled.
    def windowFloating(self, event, window):
        pass


    # onBinding is called when a key binding is pressed while the workspace
    # is focused.
    def onBinding(self, command):
        pass


    # This log function includes the class name, workspace number, and the 
    # name of the function it is called by. This makes it useful for functions
    # that are called in response to events.
    def log(self, msg):
        if self.debug:
            print(("%s %d: %s: %s" % (self.shortName, self.workspaceNum, inspect.stack()[1][3], msg)))


    # This log function includes the class name, workspace number, and the 
    # name of the function 2 calls up. This makes it useful for helper
    # functions that get called by event handlers
    def logCaller(self, msg):
        if self.debug:
            print(("%s %d: %s: %s" % (self.shortName, self.workspaceNum, inspect.stack()[2][3], msg)))

    # These are some helper functions for getting container ids
    def getWorkspaceCon(self):
        return self.con.get_tree().find_by_id(self.workspaceId)


    def getFocusedCon(self):
        return self.con.get_tree().find_focused()


    def getConById(self, conId):
        return self.con.get_tree().find_by_id(conId)
