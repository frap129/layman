#!/usr/bin/env python3
"""
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
from i3ipc import Event, Connection, BindingEvent, WorkspaceEvent, WindowEvent
import imp
import inspect
import logging
import os
from setproctitle import setproctitle
import shutil

import utils
import config
from managers.WorkspaceLayoutManager import WorkspaceLayoutManager
from managers.MasterStackLayoutManager import MasterStackLayoutManager
from managers.AutotilingLayoutManager import AutotilingLayoutManager


class SWLM:
    def __init__(self):
        self.managers = utils.SimpleDict()
        self.workspaceWindows = utils.SimpleDict()
        self.focusedWindow = None
        self.focusedWorkspace = None
        self.eventQueue = utils.EventQueue()
        self.userLayouts = utils.SimpleDict()
        setproctitle("swlm")


    """
    Window Events

    The following functions that are called in response to window events, specifically
    window::new, window::focus, window::close, window::move, and window::floating.
    """

    def windowCreated(self, event):
        self.focusedWorkspace = utils.findFocusedWorkspace(self.con)

        # Check if we should pass this call to a manager
        if self.isExcluded(self.focusedWorkspace):
            self.log("Workspace or output excluded")
            return

        # Check if we have a layoutmanager
        if self.focusedWorkspace.num not in self.managers:
            self.log("No manager for workpsace %d, ignoring" % self.focusedWorkspace.num)
            self.setWorkspaceLayoutManager(self.focusedWorkspace)

        # Store window
        self.focusedWindow = utils.findFocusedWindow(self.con)
        if self.focusedWindow is not None:
            self.workspaceWindows[self.focusedWorkspace.num].append(self.focusedWindow.id)

        # Pass event to the layout manager
        self.log("Calling windowAdded for workspace %d" % self.focusedWorkspace.num)
        self.managers[self.focusedWorkspace.num].windowAdded(event, self.focusedWindow)


    def windowFocused(self, event):
        self.focusedWorkspace = utils.findFocusedWorkspace(self.con)
        self.focusedWindow = utils.findFocusedWindow(self.con)

        # Check if we should pass this call to a manager
        if self.isExcluded(self.focusedWorkspace):
            self.log("Workspace or output excluded")
            return

        # Pass command to the appropriate manager
        # log("windowFocused: Calling manager for workspace %d" % workspace.num)
        self.managers[self.focusedWorkspace.num].windowFocused(event, self.focusedWindow)


    def windowClosed(self, event):
        # Try to find workspace num by locating where the window is recorded
        workspaceNum = None
        for num in self.workspaceWindows:
            if event.container.id in self.workspaceWindows[num]:
                workspaceNum = num
                break

        # Fallback to focused workspace if the window wasn't tracked
        if workspaceNum is None:
            workspaceNum = utils.findFocusedWorkspace(self.con).num

        # Remove window
        try:
            self.workspaceWindows[workspaceNum].remove(event.container.id)
        except BaseException as e:
            self.log("Untracked window %d closed on %d" % (event.container.id, workspaceNum))

        # Pass command to the appropriate manager
        self.log("Calling windowRemoved for workspace %d" % workspaceNum)
        self.managers[workspaceNum].windowRemoved(event, self.focusedWindow)


    def windowMoved(self, event):
        window = utils.findFocusedWindow(self.con)
        workspace = window.workspace()

        if window.id in self.workspaceWindows[self.focusedWorkspace.num]:
            # Check if window has changed workspaces
            if workspace.num == self.focusedWorkspace.num:
                # Window moved within the same workspace, call windowMoved
                if not self.isExcluded(workspace):
                   self.log("Calling windowMoved for workspace %d" % workspace.num)
                   self.managers[workspace.num].windowMoved(event, window)
            else:
                # Call windowRemoved on old workspace
                if not self.isExcluded(self.focusedWorkspace):
                    self.log("Calling windowRemoved for workspace %d" % self.focusedWorkspace.num)
                    self.workspaceWindows[self.focusedWorkspace.num].remove(window.id)
                    self.managers[self.focusedWorkspace.num].windowRemoved(event, window)

        if window.id not in self.workspaceWindows[workspace.num]:
            # Call windowAdded on new workspace
            if not self.isExcluded(workspace):
                self.log("Calling windowAdded for workspace %d" % workspace.num)
                self.workspaceWindows[workspace.num].append(window.id)
                self.managers[workspace.num].windowAdded(event, window)

        self.focusedWindow = window
        self.focusedWorkspace = workspace


    def windowFloating(self, event):
        self.focusedWorkspace = utils.findFocusedWorkspace(self.con)
        self.focusedWindow = utils.findFocusedWindow(self.con)

        # Check if we should pass this call to a manager
        if self.isExcluded(self.focusedWorkspace):
            self.log("Workspace or output excluded")
            return

        # Only send windowFloating event if wlm supports it
        if self.managers[self.focusedWorkspace.num].supportsFloating:
             self.log("Calling windowFloating for workspace %d" % self.focusedWorkspace.num)
             self.managers[self.focusedWorkspace.num].windowFloating(event, self.focusedWindow)
             return

        # Determine if window is floating
        i3Floating = self.focusedWindow.floating is not None and "on" in self.focusedWindow.floating
        swayFloating = any(self.focusedWindow.id == node.id for node in self.focusedWindow.workspace().floating_nodes)

        if swayFloating or i3Floating:
            # Window floating, treat like its closed
            self.log("Calling windowRemoved for workspace %d" % self.focusedWorkspace.num)
            try:
                self.workspaceWindows[self.focusedWorkspace.num].remove(self.focusedWindow.id)
            except ValueError as e:
                self.log("Wiondow not tracked in workspace")
            self.managers[self.focusedWorkspace.num].windowRemoved(event, self.focusedWindow)
        else:
            # Window is not floating, treat like a new window
            self.log("Calling windowAdded for workspace %d" % self.focusedWorkspace.num)
            self.workspaceWindows[self.focusedWorkspace.num].append(self.focusedWindow.id)
            self.managers[self.focusedWorkspace.num].windowAdded(event, self.focusedWindow)


    """
    Workspace Events

    The following functions are called in response to workspace events, specifically
    workspace::init and workspace::focus.
    """

    def workspaceInit(self, event):
        self.focusedWorkspace = event.current
        self.setWorkspaceLayoutManager(self.focusedWorkspace)


    def workspaceFocused(self, event):
        # Exit early if we're on the same workspace
        if event.old == None or event.current.num == event.old.num:
            return

        window = utils.findFocusedWindow(self.con)
        if self.focusedWindow != None and window.id != self.focusedWindow.id:
            #  Exit early if all we did was focus a new window
            self.focusedWindow = window
            self.focusedWorkspace = event.current
            return

        # Check if window has changed workspaces
        if window.id == self.focusedWindow.id and window.workspace().num == event.current.num and self.focusedWorkspace.num == event.old.num:
            # Window has changed workspaces, check if it needs to be reported
            if window.id in self.workspaceWindows[self.focusedWorkspace.num] and not self.isExcluded(self.focusedWorkspace):
                # Window is still tracked on old workspace, remove and call windowRemoved on its manager
                self.log("Calling windowRemoved for workspace %d" % self.focusedWorkspace.num)
                self.workspaceWindows[self.focusedWorkspace.num].remove(window.id)
                self.managers[self.focusedWorkspace.num].windowRemoved(event, window)
                    
            if window.id not in self.workspaceWindows[event.current.num] and not self.isExcluded(event.current):
                # Window is not tracked on new workspace, add and call windowAdded on its manager
                self.log("Calling windowAdded for workspace %d" % event.current.num)
                self.workspaceWindows[event.current.num].append(window.id)
                self.managers[event.current.num].windowAdded(event, window)

        self.focusedWindow = window
        self.focusedWorkspace = event.current


    """
    Binding Events

    The following function is called in response to any binding event and handles interpreting
    the binding command or passing it to the intended workspace layout manager.
    """

    def onBinding(self, event):
        # Exit early if binding isnt for slwm
        command = event.ipc_data["binding"]["command"].strip()
        if "nop swlm" not in command:
            return
            
        # Check if we should pass this call to a manager
        workspace = utils.findFocusedWorkspace(self.con)
        if self.isExcluded(workspace):
            self.log("Workspace or output excluded")
            return

        # Handle movement commands
        if "nop swlm move" in command and self.managers[workspace.num].overridesMoveBinds:
            self.managers[workspace.num].onBinding(command)
            self.log("Passed bind to manager on workspace %d" % workspace.num)
            return
        elif "nop swlm move " in  command:
            moveCmd = command.replace("nop swlm ", '')
            self.con.command(moveCmd)
            self.log("Handling bind \"%s\" for workspace %d" % (moveCmd, workspace.num))
            return

        # Handle reload command
        if command == "nop swlm reload":
            # Get user config options
            self.options = config.SWLMConfig(self.con, utils.getConfigPath())
            self.fetchLayouts()
            self.log("Reloaded swlm config")
            return

        # Handle wlm creation commands
        if "nop swlm layout " in command:
            if command == "nop swlm layout none":
                # Create no-op WLM to prevent onWorkspace from overwriting
                self.managers[workspace.num] = WorkspaceLayoutManager(self.con, workspace, self.options)
            elif command == "nop swlm layout MasterStack":
                self.managers[workspace.num] = MasterStackLayoutManager(self.con, workspace, self.options)
            elif command == "nop swlm layout Autotiling":
                self.managers[workspace.num] = AutotilingLayoutManager(self.con, workspace, self.options)
            else:
                shortName = command.split(' ')[-1]
                layoutName = self.getLayoutNameByShortName(shortName)
                self.managers[workspace.num] = getattr(self.userLayouts[name], name)(self.con, workspace, self.options)

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
        # Set item priority
        priority = 3
        if type(event) == WorkspaceEvent and event.change == "init":
            priority = 0
        elif type(event) == WorkspaceEvent and event.change == "focus":
            priority = 1
        elif type(event) == BindingEvent:
            priority = 2
        elif type(event) == WindowEvent and event.change == "move":
            priority = 4

        try:
            self.eventQueue.put(utils.EventItem(priority, event))
        except TypeError as e:
            logging.exception(e)


    def onEventAddedToQueue(self):
        event = self.eventQueue.get().event
        if type(event) == BindingEvent:
            self.onBinding(event)
        if type(event) == WorkspaceEvent:
            if event.change == "init":
                self.workspaceInit(event)
            elif event.change == "focus":
                self.workspaceFocused(event)
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
        layoutPath = os.path.dirname(utils.getConfigPath())
        for file in os.listdir(layoutPath):
            if file.endswith(".py"):
                # Assume all python files in the config path are layouts, load them
                className = os.path.splitext(file)[0]
                try:
                    fp, path, desc = imp.find_module(className, [layoutPath])
                    package = imp.load_module(className, fp, path, desc)
                    self.userLayouts[className] = package
                except ImportError:
                    self.log("Layout not found: " + name)

    def getLayoutNameByShortName(self, shortName):
        for name in self.userLayouts:
            if getattr(self.userLayouts[name], name).shortName == shortName:
                return name

    def setWorkspaceLayoutManager(self, workspace):
        # Check if we should manage workspace
        if self.isExcluded(workspace):
            return

        layoutName = self.options.getForWorkspace(workspace.num, config.KEY_LAYOUT)
        if workspace.num not in self.managers:
            if layoutName == AutotilingLayoutManager.shortName:
                self.managers[workspace.num] = AutotilingLayoutManager(self.con, workspace, self.options)
                self.logCaller("Initialized workspace %d with %s" % (workspace.num, self.managers[workspace.num].shortName))
            elif layoutName == MasterStackLayoutManager.shortName:
                self.managers[workspace.num] = MasterStackLayoutManager(self.con, workspace, self.options)
                self.logCaller("Initialized workspace %d wth %s" % (workspace.num, self.managers[workspace.num].shortName))
            elif layoutName == WorkspaceLayoutManager.shortName:
                self.managers[workspace.num] = WorkspaceLayoutManager(self.con, workspace, self.options)
                self.logCaller("Initialized workspace %d wth %s" % (workspace.num, self.managers[workspace.num].shortName))
            else:
                # If the layout isn't prebundled, search user layouts
                name = self.getLayoutNameByShortName(layoutName)
                self.managers[workspace.num] = getattr(self.userLayouts[name], name)(self.con, workspace, self.options)
                self.logCaller("Initialized workspace %d wth %s" % (workspace.num, self.managers[workspace.num].shortName))

        if workspace.num not in self.workspaceWindows:
            self.workspaceWindows[workspace.num] = []

    
    def createConfig():
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
        # Set event callbacks
        self.con = Connection()
        self.con.on(Event.BINDING, self.onEvent)
        self.con.on(Event.WINDOW_FOCUS, self.onEvent)
        self.con.on(Event.WINDOW_NEW, self.onEvent)
        self.con.on(Event.WINDOW_CLOSE, self.onEvent)
        self.con.on(Event.WINDOW_MOVE, self.onEvent)
        self.con.on(Event.WINDOW_FLOATING, self.onEvent)
        self.con.on(Event.WORKSPACE_INIT, self.onEvent)
        self.con.on(Event.WORKSPACE_FOCUS, self.onEvent)

        # Get user config options
        self.options = config.SWLMConfig(self.con, utils.getConfigPath())
        self.fetchLayouts()

        # Register event queue listener
        self.eventQueue.registerListener(self.onEventAddedToQueue)
        self.log("swlm started")

        # Set default layout maangers
        if self.options.getDefault(config.KEY_LAYOUT):
            for workspace in self.con.get_workspaces():
                self.setWorkspaceLayoutManager(workspace)
                self.workspaceWindows[workspace.num] = []

        # Start i3ipc connection
        try:
            self.con.main()
        except BaseException as e:
            print("restarting after exception:")
            logging.exception(e)
            self.init()


# Start swlm
swlm = SWLM()
swlm.init()
