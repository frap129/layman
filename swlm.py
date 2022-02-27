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


def windowCreated(con, event):
    focusedWindow = utils.findFocused(con)

    if isExcluded(focusedWindow):
        log("windowCreated: Window, workspace, or output excluded")
        return

    workspace = focusedWindow.workspace()
    if workspace is None:
        log("windowCreated: No workspace given")
        return

    if workspace.id not in managers:
        log("windowCreated: No manager for workpsace %d, ignoring" % workspace.id)
        return

    log("windowCreated: calling manager for workspace %d" % workspace.id)
    managers[workspace.id].windowCreated(event)


def windowFocused(con, event):
    focusedWindow = utils.findFocused(con)

    if isExcluded(focusedWindow):
        log("windowFocused: Window, workspace, or output excluded")
        return
        
    workspace = focusedWindow.workspace()
    if workspace is None:
        log("windowFocused: No workspace given")
        return

    if workspace.id not in managers:
        log("windowFocused: No manager for workpsace %d, ignoring" % workspace.id)
        return

    log("windowFocused: Calling manager for workspace %d" % workspace.id)
    managers[workspace.id].windowFocused(event)


def windowClosed(con, event):
    focusedWindow = utils.findFocused(con)

    if isExcluded(focusedWindow):
        log("windowClosed: Window, workspace, or output excluded")
        return

    workspace = focusedWindow.workspace()
    if workspace is None:
        log("windowClosed: No workspace given")
        return

    if workspace.id not in managers:
        log("windowClosed: No manager for workpsace %d, ignoring" % workspace.id)
        return

    log("windowClosed: calling manager for workspace %d" % workspace.id)
    managers[workspace.id].windowClosed(event)


def recvBinding(con, event):
    # TODO: Get focsed workspace without requiring workspace to have a window
    focusedWindow = utils.findFocused(con)
    
    if isExcluded(focusedWindow):
        log("recvCommand: Window, workspace, or output excluded")
        return

    workspace = focusedWindow.workspace()
    if workspace is None:
        log("recvCommand: No workspace given")
        return

    command = event.ipc_data["binding"]["command"].strip()
    if command == "nop layout MasterStack":
        managers[workspace.id] = MasterStackLayoutManager(con, workspace.id, options.masterWidth, options.stackLayout)

    if workspace.id not in managers:
        log("windowClosed: No manager for workpsace %d, ignoring" % workspace.id)
        return
        
    log("recvCommand: calling manager for workspace %d" % workspace.id)    
    managers[workspace.id].binding(event)


def main():
    setproctitle("swlm")
    con = Connection()
    con.on(Event.WINDOW_FOCUS, windowFocused)
    con.on(Event.WINDOW_NEW, windowCreated)
    con.on(Event.WINDOW_CLOSE, windowClosed)
    con.on(Event.BINDING, recvBinding)

    try:
        con.main()
    except BaseException as e:
        print("restarting after exception:")
        print(e)
        main()


main()
