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
from dataclasses import dataclass, field
from i3ipc import Event, Connection, BindingEvent, WorkspaceEvent, WindowEvent
import inspect
import logging
from setproctitle import setproctitle
import threading
import queue

import utils
from managers.WorkspaceLayoutManager import WorkspaceLayoutManager
from managers.MasterStackLayoutManager import MasterStackLayoutManager
from managers.AutotilingLayoutManager import AutotilingLayoutManager


class WorkspaceLayoutManagerDict(dict):
    def __missing__(self, key):
        return None


class NotifyingList(list):
    def __init__(self, maxsize=0):
        super().__init__()
        self.on_change_listeners = []

    def append(self, item):
        super().append(item)
        for listener in self.on_change_listeners:
            thread = threading.Thread(target=listener)
            thread.start()

    def registerListener(self, listener):
        self.on_change_listeners.append(listener)


class SWLM:
    def __init__(self):
        self.options = utils.getUserOptions()
        self.managers = WorkspaceLayoutManagerDict()
        self.workspaceWindows = WorkspaceLayoutManagerDict()
        self.focusedWindow = None
        self.focusedWorkspace = None
        self.eventQueue = NotifyingList()
        self.con = Connection()
        setproctitle("swlm")


    def windowCreated(self, event):
        self.focusedWorkspace = self.findFocusedWorkspace(self.con)

        # Check if we should pass this call to a manager
        if self.isExcluded(self.focusedWorkspace):
            self.log("Workspace or output excluded")
            return

        # Check if we have a layoutmanager
        if self.focusedWorkspace.num not in self.managers:
            self.log("No manager for workpsace %d, ignoring" % self.focusedWorkspace.num)
            self.setWorkspaceLayoutManager(self.focusedWorkspace)

        # Store window
        self.focusedWindow = utils.findFocused(self.con)
        if self.focusedWindow is not None:
            self.workspaceWindows[self.focusedWorkspace.num].append(self.focusedWindow.id)

        # Pass event to the layout manager
        self.log("Calling windowAdded for workspace %d" % self.focusedWorkspace.num)
        self.managers[self.focusedWorkspace.num].windowAdded(event, self.focusedWindow)


    def windowFocused(self, event):
        self.focusedWorkspace = self.findFocusedWorkspace(self.con)
        self.focusedWindow = utils.findFocused(self.con)

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
            workspaceNum = self.findFocusedWorkspace(self.con).num

        # Remove window
        try:
            self.workspaceWindows[workspaceNum].remove(event.container.id)
        except BaseException as e:
            self.log("Untracked window %d closed on %d" % (event.container.id, workspaceNum))

        # Pass command to the appropriate manager
        self.log("Calling windowRemoved for workspace %d" % workspaceNum)
        self.managers[workspaceNum].windowRemoved(event, self.focusedWindow)


    def windowMoved(self, event):
        window = utils.findFocused(self.con)
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


    def workspaceInit(self, event):
        self.focusedWorkspace = self.findFocusedWorkspace(self.con)
        self.setWorkspaceLayoutManager(self.focusedWorkspace)

    def onBinding(self, event):
        # Exit early if binding isnt for slwm
        command = event.ipc_data["binding"]["command"].strip()
        if "nop swlm" not in command:
            return
            
        # Check if we should pass this call to a manager
        workspace = self.findFocusedWorkspace(self.con)
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

        # Handle wlm creation commands
        if command == "nop swlm layout none":
            # Create no-op WLM to prevent onWorkspace from overwriting
            self.managers[workspace.num] = WorkspaceLayoutManager(self.con, workspace, self.options)
            self.log("Destroyed manager on workspace %d" % workspace.num)
            return
        elif command == "nop swlm layout MasterStack":
            self.managers[workspace.num] = MasterStackLayoutManager(self.con, workspace, self.options)
            self.log("Created %s on workspace %d" % (self.managers[workspace.num].shortName, workspace.num))
            return
        elif command == "nop swlm layout Autotiling":
            self.managers[workspace.num] = AutotilingLayoutManager(self.con, workspace, self.options)
            self.log("Created %s on workspace %d" % (self.managers[workspace.num].shortName, workspace.num))
            return

        # Pass unknown command to the appropriate wlm
        if workspace.num not in self.managers:
            self.log("No manager for workpsace %d, ignoring" % workspace.num)
            return
            
        self.log("Calling manager for workspace %d" % workspace.num)
        self.managers[workspace.num].onBinding(command)


    def onEventAddedToQueue(self):
        event = self.eventQueue.pop()

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
            elif event.change == "close":
                self.windowClosed(event)


    def onEvent(self, con, event):
        self.con = con
        self.eventQueue.append(event)


    def setWorkspaceLayoutManager(self, workspace):
        if workspace.num not in self.managers:
            if self.options.default == AutotilingLayoutManager.shortName:
                self.managers[workspace.num] = AutotilingLayoutManager(self.con, workspace, self.options)
                self.logCaller("Initialized workspace %d with %s" % (workspace.num, self.managers[workspace.num].shortName))
            elif self.options.default == MasterStackLayoutManager.shortName:
                self.managers[workspace.num] = MasterStackLayoutManager(self.con, workspace, self.options)
                self.logCaller("Initialized workspace %d wth %s" % (workspace.num, self.managers[workspace.num].shortName))
        if workspace.num not in self.workspaceWindows:
            self.workspaceWindows[workspace.num] = []


    def findFocusedWorkspace(self, con):
        workspace = None
        for workspace in con.get_workspaces():
            if workspace.focused:
                workspace = workspace
                break

        return workspace


    def log(self, msg):
        if self.options.debug:
            print("%s: %s" % (inspect.stack()[1][3], msg))


    def logCaller(self, msg):
        if self.options.debug:
            print("%s: %s" % (inspect.stack()[2][3], msg))


    def isExcluded(self, workspace):
        if workspace is None:
            return True

        if self.options.excludes and workspace.num in self.options.excludes:
            return True

        if self.options.outputs and workspace.ipc_data["output"] not in self.options.outputs:
            return True

        return False


    def init(self):
        # Set event callbacks
        self.con.on(Event.BINDING, self.onEvent)
        self.con.on(Event.WINDOW_FOCUS, self.onEvent)
        self.con.on(Event.WINDOW_NEW, self.onEvent)
        self.con.on(Event.WINDOW_CLOSE, self.onEvent)
        self.con.on(Event.WINDOW_MOVE, self.onEvent)
        self.con.on(Event.WORKSPACE_INIT, self.onEvent)

        # Register event queue listener
        self.eventQueue.registerListener(self.onEventAddedToQueue)
        self.log("swlm started")

        # Set default layout maangers
        if self.options.default and self.options.default != "none":
            for workspace in self.con.get_workspaces():
                self.setWorkspaceLayoutManager(workspace)
                self.workspaceWindows[workspace.num] = []

        try:
            self.con.main()
        except BaseException as e:
            print("restarting after exception:")
            logging.exception(e)
            self.init()


# Start swlm
swlm = SWLM()
swlm.init()
