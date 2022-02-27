#!/usr/bin/env python3

from i3ipc import Event, Connection
from setproctitle import setproctitle

import utils
from managers.MasterStackLayoutManager import MasterStackLayoutManager


class WorkspaceLayoutManagerDict(dict):
    def __missing__(self, key):
        return None


options = utils.getUserOptions()
managers = WorkspaceLayoutManagerDict()


def log(msg):
    if options.debug:
        print(msg)


def isExcluded(window):
    if window is None:
        return True

    if window.type != "con":
        return True

    if window.workspace() is None:
        return True

    if window.floating is not None and "on" in window.floating:
        return True

    if options.excludes and window.workspace().name in options.excludes:
        return True

    if options.outputs and window.ipc_data["output"] not in options.outputs:
        return True

    return False

# This doesn't work for some reason, guess a window needs top be action
def findFocusedWorkspace(con):
    # Get id of focused workspace
    workspaceId = None
    for workspace in con.get_tree().workspaces():
        log(workspace.focused)
        if workspace.focused:
            workspaceId = workspace.id
            break

    return workspaceId

def windowCreated(con, event):
    # Check if we should ignore this call
    focusedWindow = utils.findFocused(con)
    if isExcluded(focusedWindow):
        log("windowCreated: Window, workspace, or output excluded")
        return

    # Get focused workspace
    workspaceId = focusedWindow.workspace().id
    if workspaceId is None:
        log("windowCreated: No workspace given")
        return

    # Pass command to the appropriate manager
    if workspaceId not in managers:
        log("windowCreated: No manager for workpsace %d, ignoring" % workspaceId)
        return

    log("windowCreated: calling manager for workspace %d" % workspaceId)
    managers[workspaceId].windowCreated(event)


def windowFocused(con, event):
    # Check if we should ignore this call
    focusedWindow = utils.findFocused(con)
    if isExcluded(focusedWindow):
        log("windowFocused: Window, workspace, or output excluded")
        return

    # Get focused workspace
    workspaceId = focusedWindow.workspace().id
    if workspaceId is None:
        log("windowFocused: No workspace given")
        return
    
    # Pass command to the appropriate manager
    if workspaceId not in managers:
        log("windowFocused: No manager for workpsace %d, ignoring" % workspaceId)
        return

    log("windowFocused: Calling manager for workspace %d" % workspaceId)
    managers[workspaceId].windowFocused(event)


def windowClosed(con, event):
    # Check if we should ignore this call
    focusedWindow = utils.findFocused(con)
    if isExcluded(focusedWindow):
        log("windowClosed: Window, workspace, or output excluded")
        return

    # Get focused workspace
    workspaceId = focusedWindow.workspace().id
    if workspaceId is None:
        log("windowClosed: No workspace given")
        return None

    # Pass command to the appropriate manager
    if workspaceId not in managers:
        log("windowClosed: No manager for workpsace %d, ignoring" % workspaceId)
        return

    log("windowClosed: calling manager for workspace %d" % workspaceId)
    managers[workspaceId].windowClosed(event)

def windowMoved(con, event):
    # Check if we should ignore this call
    focusedWindow = utils.findFocused(con)
    if isExcluded(focusedWindow):
        log("windowMoved: Window, workspace, or output excluded")
        return

    # Get focused workspace
    workspaceId = focusedWindow.workspace().id
    if workspaceId is None:
        log("windowMoved: No workspace given")
        return None

    # Pass command to the appropriate manager
    if workspaceId not in managers:
        log("windowMoved: No manager for workpsace %d, ignoring" % workspaceId)
        return

    log("windowMoved: calling manager for workspace %d" % workspaceId)
    managers[workspaceId].windowMoved(event)


def recvBinding(con, event):
    # Check if we should ignore this call
    focusedWindow = utils.findFocused(con)
    if isExcluded(focusedWindow):
        log("windowFocused: Window, workspace, or output excluded")
        return

    # Get focused workspace
    # TODO: Get focused workspace without having to create a window
    workspaceId = focusedWindow.workspace().id
    if workspaceId is None:
        log("recvBinding: No workspace given")
        return None

    # Check if command is to create a layout manager
    command = event.ipc_data["binding"]["command"].strip()
    if command == "nop layout MasterStack":
        managers[workspaceId] = MasterStackLayoutManager(con, workspaceId, options)
        log("recvBinding: Created MasterStackLayoutManager on workspace %d" % workspaceId)
        return

    # Pass command to the appropriate manager
    if workspaceId not in managers:
        log("windowClosed: No manager for workpsace %d, ignoring" % workspaceId)
        return
        
    log("recvCommand: calling manager for workspace %d" % workspaceId)    
    managers[workspaceId].binding(event)


def main():
    setproctitle("swlm")

    # Get connection to sway
    con = Connection()
    con.on(Event.WINDOW_FOCUS, windowFocused)
    con.on(Event.WINDOW_NEW, windowCreated)
    con.on(Event.WINDOW_CLOSE, windowClosed)
    con.on(Event.WINDOW_MOVE, windowClosed)
    con.on(Event.BINDING, recvBinding)
    
    try:
        log("swlm started")
        con.main()
    except BaseException as e:
        print("restarting after exception:")
        print(e)
        main()


main()
