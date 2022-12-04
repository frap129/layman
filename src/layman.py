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
from i3ipc import Event, Connection, BindingEvent, WorkspaceEvent, WindowEvent
from importlib.machinery import SourceFileLoader
import inspect
import logging
import os
from setproctitle import setproctitle
import shutil

import utils
import config
from managers import WorkspaceLayoutManager
from managers import MasterStackLayoutManager
from managers import AutotilingLayoutManager
from managers import GridLayoutManager


class Layman:
    def __init__(self):
        self.managers = utils.SimpleDict()
        self.eventQueue = utils.EventQueue()
        self.userLayouts = utils.SimpleDict()
        self.workspaceWindows = utils.SimpleDict()
        setproctitle("layman")


    """
    Window Events

    The following functions that are called in response to window events, specifically
    window::new, window::focus, window::close, window::move, and window::floating.
    """

    def windowCreated(self, event):
        window = utils.findFocusedWindow(self.cmdCon)
        workspace = utils.findFocusedWorkspace(self.cmdCon)

        # Check if we should pass this call to a manager
        if self.isExcluded(workspace):
            self.log("Workspace or output excluded")
            return

        # Check if we have a layoutmanager
        if workspace.num not in self.managers:
            self.log("No manager for workpsace %d, ignoring" % workspace.num)
            self.setWorkspaceLayoutManager(workspace)

        # Store window
        self.workspaceWindows[workspace.num].append(window.id)

        # Pass event to the layout manager
        self.log("Calling windowAdded for workspace %d" % workspace.num)
        self.managers[workspace.num].windowAdded(event, window)


    def windowFocused(self, event):
        window = utils.findFocusedWindow(self.cmdCon)
        workspace = utils.findFocusedWorkspace(self.cmdCon)

        # Check if we should pass this call to a manager
        if self.isExcluded(workspace):
            self.log("Workspace or output excluded")
            return

        # Pass command to the appropriate manager
        # log("windowFocused: Calling manager for workspace %d" % workspace.num)
        self.managers[workspace.num].windowFocused(event, window)


    def windowClosed(self, event):
        # Try to find workspace num by locating where the window is recorded
        workspaceNum = None
        for num in self.workspaceWindows:
            if event.container.id in self.workspaceWindows[num]:
                workspaceNum = num
                break

        # Fallback to focused workspace if the window wasn't tracked
        if workspaceNum is None:
            workspaceNum = utils.findFocusedWorkspace(self.cmdCon).num

        # Remove window
        try:
            self.workspaceWindows[workspaceNum].remove(event.container.id)
        except BaseException as e:
            self.log("Untracked window %d closed on %d" % (event.container.id, workspaceNum))

        # Pass command to the appropriate manager
        self.log("Calling windowRemoved for workspace %d" % workspaceNum)
        self.managers[workspaceNum].windowRemoved(event, utils.findFocusedWindow(self.cmdCon))


    def windowMoved(self, event):
        window = utils.findFocusedWindow(self.cmdCon)
        workspace = utils.findFocusedWorkspace(self.cmdCon)

        if window.id in self.workspaceWindows[workspace.num]:
            # Window moved within the same workspace, call windowMoved
            if not self.isExcluded(workspace):
                self.log("Calling windowMoved for workspace %d" % workspace.num)
                self.managers[workspace.num].windowMoved(event, window)
        else:
            # Call windowAdded on new workspace
            if not self.isExcluded(workspace):
                self.log("Calling windowAdded for workspace %d" % workspace.num)
                self.workspaceWindows[workspace.num].append(window.id)
                self.managers[workspace.num].windowAdded(event, window)

            # Find old workspace
            for workspaceNum in self.workspaceWindows.keys():
                if window.id in self.workspaceWindows[workspaceNum]:
                    # Call windowRemoved on old workspace
                    if not self.isExcluded(workspace):
                        self.log("Calling windowRemoved for workspace %d" % workspaceNum)
                        self.workspaceWindows[workspaceNum].remove(window.id)
                        self.managers[workspaceNum].windowRemoved(event, window)


    def windowFloating(self, event):
        window = self.cmdCon.get_tree().find_by_id(event.container.id)
        workspace = utils.findFocusedWorkspace(self.cmdCon)

        # Check if we should pass this call to a manager
        if self.isExcluded(workspace):
            self.log("Workspace or output excluded")
            return

        # Only send windowFloating event if wlm supports it
        if self.managers[workspace.num].supportsFloating:
             self.log("Calling windowFloating for workspace %d" % workspace.num)
             self.managers[workspace.num].windowFloating(event, window)
             return

        # Determine if window is floating
        i3Floating = window.floating is not None and "on" in window.floating
        swayFloating = any(window.id == node.id for node in workspace.floating_nodes)

        if swayFloating or i3Floating:
            # Window floating, treat like its closed
            self.log("Calling windowRemoved for workspace %d" % workspace.num)
            try:
                self.workspaceWindows[workspace.num].remove(window.id)
            except ValueError as e:
                self.log("Wiondow not tracked in workspace")
            self.managers[workspace.num].windowRemoved(event, window)
        else:
            # Window is not floating, treat like a new window
            self.log("Calling windowAdded for workspace %d" % workspace.num)
            self.workspaceWindows[workspace.num].append(window.id)
            self.managers[workspace.num].windowAdded(event, window)


    """
    Workspace Events

    The following functions are called in response to workspace events, specifically
    workspace::init and workspace::focus.
    """

    def workspaceInit(self, event):
        self.setWorkspaceLayoutManager(event.current)

    """
    Binding Events

    The following function is called in response to any binding event and handles interpreting
    the binding command or passing it to the intended workspace layout manager.
    """

    def onBinding(self, event):
        # Exit early if binding isnt for slwm
        command = event.ipc_data["binding"]["command"].strip()
        if "nop layman" not in command:
            return
            
        # Check if we should pass this call to a manager
        workspace = utils.findFocusedWorkspace(self.cmdCon)
        if self.isExcluded(workspace):
            self.log("Workspace or output excluded")
            return

        # Handle movement commands
        if "nop layman move" in command and self.managers[workspace.num].overridesMoveBinds:
            self.managers[workspace.num].onBinding(command)
            self.log("Passed bind to manager on workspace %d" % workspace.num)
            return
        elif "nop layman move " in  command:
            moveCmd = command.replace("nop layman ", '')
            self.cmdCon.command(moveCmd)
            self.log("Handling bind \"%s\" for workspace %d" % (moveCmd, workspace.num))
            return

        # Handle reload command
        if command == "nop layman reload":
            # Get user config options
            self.options = config.LaymanConfig(self.cmdCon, utils.getConfigPath())
            self.fetchLayouts()
            self.log("Reloaded layman config")
            return

        # Handle wlm creation commands
        if "nop layman layout " in command:
            shortName = command.split(' ')[-1]
            name = self.getLayoutNameByShortName(shortName)
            self.managers[workspace.num] = getattr(self.userLayouts[name], name)(self.cmdCon, workspace, self.options)

            self.log("Created %s on workspace %d" % (self.managers[workspace.num].shortName, workspace.num))
            return

        # Pass unknown command to the appropriate wlm
        if workspace.num not in self.managers:
            self.log("No manager for workpsace %d, ignoring" % workspace.num)
            return
            
        self.log("Calling manager for workspace %d" % workspace.num)
        self.managers[workspace.num].onBinding(command)


    """
    Event Queue Management

    The following functions manage how events are added, removed, and sorted in the
    event queue. When an event is received from the i3ipc connection, it is prioritized
    based on its type and added to the event queue. This triggers the
    onEventAddedToQueue listener, which dispatches the event to is handler.
    """

    def onEvent(self, con, event):
        try:
            self.eventQueue.put(utils.EventItem(event))
        except TypeError as e:
            logging.exception(e)


    def onEventAddedToQueue(self):
        event = self.eventQueue.get().event
        if type(event) == BindingEvent:
            self.onBinding(event)
        if type(event) == WorkspaceEvent:
            if event.change == "init":
                self.workspaceInit(event)
        elif type(event) == WindowEvent:
            if event.change == "new":
                self.windowCreated(event)
            elif event.change == "focus":
                self.windowFocused(event)
            elif event.change == "move":
                self.windowMoved(event)
            elif event.change == "floating":
                self.windowFloating(event)
            elif event.change == "close":
                self.windowClosed(event)


    """
    Misc functions

    The following section of code handles miscellaneous tasks needed by the event
    handlers above.
    """

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
                except ImportError:
                    self.log("Layout not found: " + className)


    def getLayoutNameByShortName(self, shortName):
        for name in self.userLayouts:
            if getattr(self.userLayouts[name], name).shortName == shortName:
                return name


    def setWorkspaceLayoutManager(self, workspace):
        # Check if we should manage workspace
        if self.isExcluded(workspace):
            return

        layoutName = self.options.getForWorkspace(workspace.num, config.KEY_LAYOUT)
        name = self.getLayoutNameByShortName(layoutName)
        self.managers[workspace.num] = getattr(self.userLayouts[name], name)(self.cmdCon, workspace, self.options)
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
        self.cmdCon = Connection()
        self.options = config.LaymanConfig(self.cmdCon, utils.getConfigPath())
        self.fetchLayouts()

        # Set default layout maangers for existing workspaces
        if self.options.getDefault(config.KEY_LAYOUT):
            for workspace in self.cmdCon.get_workspaces():
                self.setWorkspaceLayoutManager(workspace)
                self.workspaceWindows[workspace.num] = []

        # Set event callbacks
        self.eventCon = Connection()
        self.eventCon.on(Event.BINDING, self.onEvent)
        self.eventCon.on(Event.WINDOW_FOCUS, self.onEvent)
        self.eventCon.on(Event.WINDOW_NEW, self.onEvent)
        self.eventCon.on(Event.WINDOW_CLOSE, self.onEvent)
        self.eventCon.on(Event.WINDOW_MOVE, self.onEvent)
        self.eventCon.on(Event.WINDOW_FLOATING, self.onEvent)
        self.eventCon.on(Event.WORKSPACE_INIT, self.onEvent)

        # Register event queue listener
        self.eventQueue.registerListener(self.onEventAddedToQueue)
        self.log("layman started")

        # Start handling events
        try:
            self.eventCon.main()
        except BaseException as e:
            print("restarting after exception:")
            logging.exception(e)
            self.eventCon.main_quit()
            self.eventCon.off(self.onEvent)
            self.init()


# Start layman
layman = Layman()
layman.init()
