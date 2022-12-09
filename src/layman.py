#!/usr/bin/env python3
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
from i3ipc import Event, Connection
from importlib.machinery import SourceFileLoader
import inspect
import logging
import os
from setproctitle import setproctitle
import shutil

from . import utils
from . import config
from .managers import WorkspaceLayoutManager
from .managers import MasterStackLayoutManager
from .managers import AutotilingLayoutManager
from .managers import GridLayoutManager


class Layman:
    def __init__(self):
        self.managers = utils.SimpleDict()
        self.userLayouts = utils.SimpleDict()
        self.workspaceWindows = utils.SimpleDict()
        setproctitle("layman")


    """
    Window Events

    The following functions that are called in response to window events, specifically
    window::new, window::focus, window::close, window::move, and window::floating.
    """

    def windowCreated(self, _, event):
        window = utils.findFocusedWindow(self.cmdConn)
        workspace = utils.findFocusedWorkspace(self.cmdConn)

        # Check if we should pass this call to a manager
        if self.isExcluded(workspace):
            self.log("Workspace or output excluded")
            return

        # Pass event to the appropriate manager
        self.dispatchToManager(event, window, workspace)


    def windowFocused(self, _, event):
        window = utils.findFocusedWindow(self.cmdConn)
        workspace = utils.findFocusedWorkspace(self.cmdConn)

        # Check if we should pass this call to a manager
        if self.isExcluded(workspace):
            self.log("Workspace or output excluded")
            return

        # Pass command to the appropriate manager
        self.dispatchToManager(event, window, workspace)

    def windowClosed(self, _, event):
        # Try to find workspace by locating where the window is recorded
        workspaces = []
        for num in self.workspaceWindows:
            if event.container.id in self.workspaceWindows[num]:
                workspaces = self.cmdConn.get_tree().workspaces()
                workspaces = [x for x in workspaces if x.num == num]
                break

        # Fallback to focused workspace if the window wasn't tracked
        if workspaces == []:
            workspace = utils.findFocusedWorkspace(self.cmdConn)
        else:
            workspace = workspaces[0]

        if self.isExcluded(workspace):
            return

        # Pass command to the appropriate manager
        window = utils.findFocusedWindow(self.cmdConn)
        self.dispatchToManager(event, window, workspace)


    def windowMoved(self, _, event):
        window = utils.findFocusedWindow(self.cmdConn)
        workspace = utils.findFocusedWorkspace(self.cmdConn)

        if self.isExcluded(workspace):
            return

        if window.id in self.workspaceWindows[workspace.num]:
            # Window moved within the same workspace, call windowMoved
            self.dispatchToManager(event, window, workspace)
        else:
            # Call windowAdded on new workspace
            event.change = "new"
            self.dispatchToManager(event, window, workspace)

            # Find old workspace
            for workspaceNum in self.workspaceWindows.keys():
                if window.id in self.workspaceWindows[workspaceNum]:
                    # Call windowRemoved on old workspace
                    event.change = "close"
                    self.dispatchToManager(event, window, workspace)


    def windowFloating(self, _, event):
        window = self.cmdConn.get_tree().find_by_id(event.container.id)
        workspace = utils.findFocusedWorkspace(self.cmdConn)

        # Check if we should pass this call to a manager
        if self.isExcluded(workspace):
            self.log("Workspace or output excluded")
            return

        # Only send windowFloating event if wlm supports it
        if self.managers[workspace.num].supportsFloating:
             self.dispatchToManager(event, window, workspace) 
             return

        # Determine if window is floating
        i3Floating = window.floating is not None and "on" in window.floating
        swayFloating = any(window.id == node.id for node in workspace.floating_nodes)

        if swayFloating or i3Floating:
            # Window floating, treat like its closed
           event.change = "close"
           self.dispatchToManager(event, window, workspace)
        else:
            # Window is not floating, treat like a new window
            event.change = "new"
            self.dispatchToManager(event, window, workspace)

    """
    Workspace Events

    The following functions are called in response to workspace events, specifically
    workspace::init and workspace::focus.
    """

    def workspaceInit(self, _, event):
        if not self.isExcluded(event.current):
            self.setWorkspaceLayoutManager(event.current)

    """
    Binding Events

    The following function is called in response to any binding event and handles interpreting
    the binding command or passing it to the intended workspace layout manager.
    """

    def onBinding(self, _, event):
        # Handle chanined commands one at a time
        command = event.ipc_data["binding"]["command"].strip()
        if "nop layman" in command:
            for command in command.split(";"):
                command = command.strip()
                workspace = utils.findFocusedWorkspace(self.cmdConn)
                if "nop layman"in command and not self.isExcluded(workspace):
                    self.handleCommand(workspace, command)
                else:
                    self.cmdConn.command(command)


    def handleCommand(self, workspace, command):
        # Handle movement commands
        if "nop layman move" in command and not self.managers[workspace.num].overridesMoveBinds:
            moveCmd = command.replace("nop layman ", '')
            self.cmdConn.command(moveCmd)
            self.log("Handling bind \"%s\" for workspace %d" % (moveCmd, workspace.num))
            return

        # Handle reload command
        if command == "nop layman reload":
            # Get user config options
            self.options = config.LaymanConfig(self.cmdConn, utils.getConfigPath())
            self.fetchLayouts()
            self.log("Reloaded layman config")
            return

        # Handle wlm creation commands
        if "nop layman layout " in command:
            shortName = command.split(' ')[-1]
            name = self.getLayoutNameByShortName(shortName)
            layout = getattr(self.userLayouts[name], name)
            self.managers[workspace.num] = layout(self.cmdConn, workspace, self.options)
            self.log("Created %s on workspace %d" % (shortName, workspace.num))
            return

        # Pass unknown command to the appropriate wlm
        if workspace.num not in self.managers:
            self.log("No manager for workpsace %d, ignoring" % workspace.num)
            return
            
        self.log("Calling manager for workspace %d" % workspace.num)
        self.managers[workspace.num].onBinding(command)


    """
    Misc functions

    The following section of code handles miscellaneous tasks needed by the event
    handlers above.
    """

    def dispatchToManager(self, event, window, workspace):
        manager = self.managers[workspace.num]
        try:
            if event.change == "new":
                self.logCaller("Calling windowAdded for workspace %d" % workspace.num)
                self.workspaceWindows[workspace.num].append(window.id)
                manager.windowAdded(event, window)
            elif event.change == "focus":
                self.logCaller("Calling windowFocused for workspace %d" % workspace.num)
                manager.windowFocused(event, window)
            elif event.change == "move":
                self.logCaller("Calling windowMoved for workspace %d" % workspace.num)
                manager.windowMoved(event, window)
            elif event.change == "floating":
                self.logCaller("Calling windowFloating for workspace %d" % workspace.num)
                manager.windowFloating(event, window)
            elif event.change == "close":
                try:
                    self.logCaller("Calling windowRemoved for workspace %d" % workspace.num)
                    self.workspaceWindows[workspace.num].remove(window.id)
                except:
                    self.log("Window not tracked in workspace")
                manager.windowRemoved(event, window)
        except BaseException as e:
            logging.exception(e)
            self.setWorkspaceLayoutManager(workspace)


    def fetchLayouts(self):
        # Get builtin layouts
        self.userLayouts["WorkspaceLayoutManager"] = WorkspaceLayoutManager
        self.userLayouts["AutotilingLayoutManager"] = AutotilingLayoutManager
        self.userLayouts["MasterStackLayoutManager"] = MasterStackLayoutManager
        self.userLayouts["GridLayoutManager"] = GridLayoutManager

        # Get user provided layouts
        layoutPath = os.path.dirname(utils.getConfigPath())
        for file in os.listdir(layoutPath):
            if file.endswith(".py"):
                # Assume all python files in the config path are layouts, load them
                className = os.path.splitext(file)[0]
                try:
                    module = SourceFileLoader(className, layoutPath + "/" + file).load_module()
                    self.userLayouts[className] = module
                    self.log("Loaded user layout %s" % self.userLayouts[className].shortName)
                except ImportError:
                    self.log("Layout not found: " + className)


    def getLayoutNameByShortName(self, shortName):
        for name in self.userLayouts:
            if getattr(self.userLayouts[name], name).shortName == shortName:
                return name


    def setWorkspaceLayoutManager(self, workspace):

        layoutName = self.options.getForWorkspace(workspace.num, config.KEY_LAYOUT)
        name = self.getLayoutNameByShortName(layoutName)
        self.managers[workspace.num] = getattr(self.userLayouts[name], name)(self.cmdConn, workspace, self.options)
        self.logCaller("Initialized workspace %d wth %s" % (workspace.num, self.managers[workspace.num].shortName))

        if workspace.num not in self.workspaceWindows:
            self.workspaceWindows[workspace.num] = []

    
    def createConfig(self):
        configPath = utils.getConfigPath()
        if not os.path.exists(configPath):
            if os.path.exists(os.path.dirname(configPath)):
                shutil.copyfile(os.path.join(os.path.dirname(__file__), 'config.toml'), configPath)            
            else:
                self.logCaller("Path to user config does not exts: %s" % configPath)
                exit()


    def log(self, msg):
        if self.options.getDefault(config.KEY_DEBUG):
            print("%s: %s" % (inspect.stack()[1][3], msg))


    def logCaller(self, msg):
        if self.options.getDefault(config.KEY_DEBUG):
            print("%s: %s" % (inspect.stack()[2][3], msg))


    def isExcluded(self, workspace):
        if workspace is None:
            return True

        if self.options.getDefault(config.KEY_EXCLUDED_WORKSPACES) and workspace.num in self.options.getDefault(config.KEY_EXCLUDED_WORKSPACES):
            return True

        if self.options.getDefault(config.KEY_EXCLUDED_OUTPUTS) and workspace.ipc_data["output"] in self.options.getDefault(config.KEY_EXCLUDED_OUTPUTS):
            return True

        return False


    def init(self):
        # Get user config options
        self.cmdConn = Connection()
        self.options = config.LaymanConfig(self.cmdConn, utils.getConfigPath())
        self.fetchLayouts()

        # Set event callbacks
        self.eventConn = Connection()
        self.eventConn.on(Event.BINDING, self.onBinding)
        self.eventConn.on(Event.WINDOW_FOCUS, self.windowFocused)
        self.eventConn.on(Event.WINDOW_NEW, self.windowCreated)
        self.eventConn.on(Event.WINDOW_CLOSE, self.windowClosed)
        self.eventConn.on(Event.WINDOW_MOVE, self.windowMoved)
        self.eventConn.on(Event.WINDOW_FLOATING, self.windowFloating)
        self.eventConn.on(Event.WORKSPACE_INIT, self.workspaceInit)

      # Set default layout maangers for existing workspaces
        if self.options.getDefault(config.KEY_LAYOUT):
            for workspace in self.cmdConn.get_workspaces():
                if not self.isExcluded(workspace):
                    self.setWorkspaceLayoutManager(workspace)
                    self.workspaceWindows[workspace.num] = []

        # Start handling events
        self.log("layman started")
        try:
            self.eventConn.main()
        except BaseException as e:
            print("restarting after exception:")
            logging.exception(e)
            self.eventConn.main_quit()
            self.init()
