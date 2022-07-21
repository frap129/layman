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
from i3ipc import Event, Connection
import inspect
from setproctitle import setproctitle
import logging

import utils
from managers.WorkspaceLayoutManager import WorkspaceLayoutManager
from managers.MasterStackLayoutManager import MasterStackLayoutManager
from managers.AutotilingLayoutManager import AutotilingLayoutManager


class WorkspaceLayoutManagerDict(dict):
    def __missing__(self, key):
        return None


class SWLM:
    def __init__(self):
        self.options = utils.getUserOptions()
        self.managers = WorkspaceLayoutManagerDict()
        self.workspaceWindows = WorkspaceLayoutManagerDict()
        self.focusedWindow = None
        self.focusedWorkspace = None


    def windowCreated(self, con, event):
        self.focusedWorkspace = self.findFocusedWorkspace(con)

        # Check if we should pass this call to a manager
        if self.isExcluded(self.focusedWorkspace):
            self.log("Workspace or output excluded")
            return

        # Check if we have a layoutmanager
        if self.focusedWorkspace.num not in self.managers:
            self.log("No manager for workpsace %d, ignoring" % self.focusedWorkspace.num)
            self.setWorkspaceLayoutManager(con, self.focusedWorkspace)

        # Store window
        self.focusedWindow = utils.findFocused(con)
        if self.focusedWindow is not None:
            self.workspaceWindows[self.focusedWorkspace.num].append(self.focusedWindow.id)

        # Pass event to the layout manager
        self.log("Calling windowAdded for workspace %d" % self.focusedWorkspace.num)
        self.managers[self.focusedWorkspace.num].windowAdded(event, self.focusedWindow)


    def windowFocused(self, con, event):
        #self.focusedWorkspace = self.findFocusedWorkspace(con)
        #self.focusedWindow = utils.findFocused(con)

        # Check if we should pass this call to a manager
        if self.isExcluded(self.focusedWorkspace):
            self.log("Workspace or output excluded")
            return

        # Pass command to the appropriate manager
        # log("windowFocused: Calling manager for workspace %d" % workspace.num)
        self.managers[self.focusedWorkspace.num].windowFocused(event, self.focusedWindow)


    def windowClosed(self, con, event):
        # Try to find workspace num by locating where the window is recorded
        workspaceNum = None
        for num in self.workspaceWindows:
            if event.container.id in self.workspaceWindows[num]:
                workspaceNum = num
                break

        # Fallback to focused workspace if the window wasn't tracked
        if workspaceNum is None:
            workspaceNum = self.findFocusedWorkspace(con).num

        # Remove window
        try:
            self.workspaceWindows[workspaceNum].remove(event.container.id)
        except BaseException as e:
            self.log("Untracked window %d closed on %d" % (event.container.id, workspaceNum))

        # Pass command to the appropriate manager
        self.log("Calling windowRemoved for workspace %d" % workspaceNum)
        self.managers[workspaceNum].windowRemoved(event, self.focusedWindow)


    def windowMoved(self,con, event):
        window = utils.findFocused(con)
        workspace = window.workspace()

        # Check if window has moved workspaces
        if window.id == self.focusedWindow.id:
            if workspace.num == self.focusedWorkspace.num:
                # Window has moved within a workspace, call windowMoved
                if not self.isExcluded(workspace):
                    self.log("Calling windowMoved for workspace %d" % workspace.num)
                    self.managers[workspace.num].windowMoved(event, self.focusedWindow)
            else:
                # Call windowRemoved on old workspace
                if not self.isExcluded(self.focusedWorkspace):
                    self.log("Calling windowRemoved for workspace %d" % self.focusedWorkspace.num)
                    self.workspaceWindows[self.focusedWorkspace.num].remove(window.id)
                    self.managers[self.focusedWorkspace.num].windowRemoved(event, self.focusedWindow)

                if not self.isExcluded(workspace):
                    # Call windowAdded on new workspace
                    self.log("Calling windowAdded for workspace %d" % workspace.num)
                    self.workspaceWindows[workspace.num].append(window.id)
                    self.managers[workspace.num].windowAdded(event, self.focusedWindow)


    def onBinding(self, con, event):
        # Exit early if binding isnt for slwm
        command = event.ipc_data["binding"]["command"].strip()
        if "nop swlm" not in command:
            return
            
        # Check if we should pass this call to a manager
        workspace = self.findFocusedWorkspace(con)
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
            con.command(moveCmd)
            self.log("Handling bind \"%s\" for workspace %d" % (moveCmd, workspace.num))
            return

        # Handle wlm creation commands
        if command == "nop swlm layout none":
            # Create no-op WLM to prevent onWorkspace from overwriting
            self.managers[workspace.num] = WorkspaceLayoutManager(con, workspace, self.options)
            self.log("Destroyed manager on workspace %d" % workspace.num)
            return
        elif command == "nop swlm layout MasterStack":
            self.managers[workspace.num] = MasterStackLayoutManager(con, workspace, self.options)
            self.log("Created %s on workspace %d" % (self.managers[workspace.num].shortName, workspace.num))
            return
        elif command == "nop swlm layout Autotiling":
            self.managers[workspace.num] = AutotilingLayoutManager(con, workspace, self.options)
            self.log("Created %s on workspace %d" % (self.managers[workspace.num].shortName, workspace.num))
            return

        # Pass unknown command to the appropriate wlm
        if workspace.num not in self.managers:
            self.log("No manager for workpsace %d, ignoring" % workspace.num)
            return
            
        self.log("Calling manager for workspace %d" % workspace.num)
        self.managers[workspace.num].onBinding(command)


    def workspaceInit(self, con, event):
        self.focusedWorkspace = self.findFocusedWorkspace(con)
        self.setWorkspaceLayoutManager(con, self.focusedWorkspace)
        
    def setWorkspaceLayoutManager(self, con, workspace):
        if workspace.num not in self.managers:
            if self.options.default == AutotilingLayoutManager.shortName:
                self.managers[workspace.num] = AutotilingLayoutManager(con, workspace, self.options)
                self.logCaller("Initialized workspace %d with %s" % (workspace.num, self.managers[workspace.num].shortName))
            elif self.options.default == MasterStackLayoutManager.shortName:
                self.managers[workspace.num] = MasterStackLayoutManager(con, workspace, self.options)
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
        setproctitle("swlm")

        # Get connection to swayipc
        con = Connection()

        # Set event callbacks
        con.on(Event.BINDING, self.onBinding)
        con.on(Event.WINDOW_FOCUS, self.windowFocused)
        con.on(Event.WINDOW_NEW, self.windowCreated)
        con.on(Event.WINDOW_CLOSE, self.windowClosed)
        con.on(Event.WINDOW_MOVE, self.windowMoved)
        con.on(Event.WORKSPACE_INIT, self.workspaceInit)
        self.log("swlm started")

        # Set default layout maangers
        if self.options.default and self.options.default != "none":
            for workspace in con.get_workspaces():
                self.setWorkspaceLayoutManager(con, workspace)
                self.workspaceWindows[workspace.num] = []

        try:
            con.main()
        except BaseException as e:
            print("restarting after exception:")
            logging.exception(e)
            self.init()


# Start swlm
swlm = SWLM()
swlm.init()
