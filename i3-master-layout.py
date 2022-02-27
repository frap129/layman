#!/usr/bin/env python3

from i3ipc import Event, Connection
from optparse import OptionParser
from setproctitle import setproctitle


def get_comma_separated_args(option, opt, value, parser):
    setattr(parser.values, option.dest, value.split(","))

parser = OptionParser()
parser.add_option("-w",
                  "--master-width",
                  dest="masterWidth",
                  type="int",
                  action="store",
                  metavar="WIDTH",
                  help="The percent screen width the master window should fill. Default is 50")
parser.add_option("-e",
                  "--exclude-workspaces",
                  dest="excludes",
                  type="string",
                  action="callback",
                  callback=get_comma_separated_args,
                  metavar="ws1,ws2,.. ",
                  help="List of workspaces that should be ignored.")
parser.add_option("-o",
                  "--outputs",
                  dest="outputs",
                  type="string",
                  action="callback",
                  callback=get_comma_separated_args,
                  metavar="HDMI-0,DP-0,.. ",
                  help="List of outputs that should be used instead of all.")
parser.add_option("-n",
                  "--nested",
                  dest="move_nested",
                  action="store_true",
                  help="Also move new windows which are created in nested containers.")
parser.add_option("-l",
                  "--stack-layout",
                  dest="stackLayout",
                  action="store",
                  metavar="LAYOUT",
                  help='The stack layout. ("tabbed", "stacked", "splitv") default: splitv',
                  choices=["tabbed", "stacked", "splitv"])  # splith not yet supported
parser.add_option("--disable-rearrange",
                  dest="disable_rearrange",
                  action="store_true",
                  help="Disable the rearrangement of windows when the master window disappears.")
parser.add_option("-d",
                  "--debug",
                  dest="debug",
                  action="store_true",
                  help="Enable debug messages")
(options, args) = parser.parse_args()


def log(msg, workspace):
    if True: # TODO: Disable logging by default
        if workspace is None:
            print(msg)
        else:
            print(("workspace %d: " % workspace) + msg)


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

        
def findFocused(c):
    tree = c.get_tree()
    focusedWindow = tree.find_focused()

    if isExcluded(focusedWindow):
        return None

    return focusedWindow


class WorkspaceLayoutManager:
    def __init__(self, con, workspaceId, masterWidth, stackLayout):
        self.con = con
        self.workspaceId = workspaceId
        self.masterId = 0
        self.stackIds = []
        self.masterWidth = masterWidth
        self.stackLayout = stackLayout


    def setMasterWidth(self):
        self.con.command('[con_id=%s] resize set %s 0 ppt' % (self.masterId, self.masterWidth))


    def moveWindow(self, subject, target):
        self.con.command("[con_id=%d] mark --add move_target" % target)
        self.con.command("[con_id=%d] move container to mark move_target" % subject)
        self.con.command("[con_id=%d] unmark move_target" % target)


    def pushWindow(self, subject):
        # Only record window if stack is empty
        if self.stackIds == []:
            # Check if master is empty too
            if self.masterId == 0:
                self.masterId = subject
            else:
                self.stackIds.append(subject)
                self.setMasterWidth()
            return

        # Check if we're missing master but have a stack, for some reason
        if self.masterId == 0:
            self.masterId = subject
            return

        # Put new window at top of stack
        target = self.stackIds[-1]
        self.moveWindow(subject, target)
        self.con.command("[con_id=%s] focus" % subject)
        self.con.command("move up")

        # Swap with master
        oldMaster = self.masterId
        self.con.command("[con_id=%d] swap container with con_id %d" % (subject, oldMaster))
        self.setMasterWidth()

        # Update record
        self.stackIds.append(self.masterId)
        self.masterId = subject


    def popWindow():
        # Check if last window is being popped
        if self.stackIds == []:
            self.masterId = 0
            return

        # Move top of stack to master position
        self.masterId = self.stackIds.pop()
        self.con.command("[con_id=%s] focus" % self.masterId)
        self.con.command("move left")
        self.setMasterWidth()


    def rotateUp():
        # Exit if less than three windows
        if len(self.stackIds) < 2:
            return

        newMaster = self.stackIds.pop()
        oldMaster = self.masterId
        bottom = self.stackIds[0]

        # Swap top of stack with master, then move old master to bottom
        log("New window id: %d" % newWindow.id, self.workspaceId)
        self.con.command("[con_id=%d] swap container with con_id %d" % (newMaster, oldMaster))
        self.moveWindow(oldMaster, bottom)

        # Update record
        self.masterId = newMaster
        self.stackIds.insert(0, oldMaster)


    def swapMaster():
        # Exit if less than two windows
        if self.stackIds == []:
            return

        # Swap focused window with master
        oldMaster = self.masterId
        newMaster = self.stackIds.pop()
        self.con.command("[con_id=%d] swap container with con_id %d" % (newMaster, oldMaster))

        # Update record
        self.masterId = newMaster
        self.stackIds.append(oldMaster)


    def windowCreated(self, event):
        newWindow = findFocused(self.con)
        
        # New window replcases master, master gets pushed to stack
        log("New window id: %d" % newWindow.id, self.workspaceId)
        self.pushWindow(newWindow.id)


    def windowFocused(self, event):
        # splith is not supported yet. idk how to differentiate between splith and nested splith.
        if self.stackIds != []:
            layout = self.stackLayout or "splitv"
            bottom = self.stackIds[0]
            self.con.command("[con_id=%d] split vertical" % bottom)
            self.con.command("[con_id=%d] layout %s" % (bottom, layout))
        else:
            self.con.command("[con_id=%d] split horizontal" % self.masterId)


    def windowClosed(self, event):
        log("Closed window id: %d" % event.container.id, self.workspaceId)
        # Try to remove window from stack, catch if its on a different workspace
        try:
            self.stackIds.remove(e.container.id)
            return
        except BaseException as e:
            return


    def binding(self, event):
        command = event.ipc_data["binding"]["command"].strip()
        if command == "nop rotate up":
            self.rotateUp()
        elif command == "nop swap master":
            self.swapMaster()

class WorkspaceLayoutManagerDict(dict):
    def __missing__(self, key):
        return None


managers = WorkspaceLayoutManagerDict()


def on_window_new(con, event):
    focusedWindow = findFocused(con)
    if focusedWindow == None:
        log("on_window_new: No window focused", None)
        return

    workspace = focusedWindow.workspace()
    if workspace is None:
        log("on_window_new: No workspace given", None)
        return


    if workspace.id not in managers:
        managers[workspace.id] = WorkspaceLayoutManager(con, workspace.id, options.masterWidth, options.stackLayout)
        log("on_window_new: Creating new manager for workpsace %d" % workspace.id, None)

    log("on_window_new: calling manager for workspace %d" % workspace.id, None)
    managers[workspace.id].windowCreated(event)
    
def on_window_focus(con, event):
    focusedWindow = findFocused(con)
    if focusedWindow == None:
        log("on_window_focus: No window focused", None)
        return

    workspace = focusedWindow.workspace()
    if workspace is None:
        log("on_window_focus: No workspace given", None)
        return

    if workspace.id not in managers:
        managers[workspace.id] = WorkspaceLayoutManager(con, workspace.id, options.masterWidth, options.stackLayout)
        log("on_window_focus: Creating new manager for workpsace %d" % workspace.id, None)


    log("on_window_focus: Calling manager for workspace %d" % workspace.id, None)
    managers[workspace.id].windowFocused(event)


def on_window_close(con, event):
    focusedWindow = findFocused(con)
    if focusedWindow == None:
        log("on_window_focus: No window focused", None)
        return

    workspace = focusedWindow.workspace()
    if workspace is None:
        log("on_window_focus: No workspace given", None)
        return

    log("on_window_close: calling manager for workspace %d" % workspace.id, None)
    managers[workspace.id].windowClosed(event)


def on_binding(con, event):
    focusedWindow = findFocused(con)
    if focusedWindow == None:
        log("on_window_focus: No window focused", None)
        return

    workspace = focusedWindow.workspace()
    if workspace is None:
        log("on_window_focus: No workspace given", None)
        return

    if workspace.id not in managers:
        managers[workspace.id] = WorkspaceLayoutManager(con, workspace.id, options.masterWidth, options.stackLayout)

    log("on_binding: calling manager for workspace %d" % workspace.id, None)    
    managers[workspace.id].binding(event)


def main():
    setproctitle("i3-master-layout")
    con = Connection()
    con.on(Event.WINDOW_FOCUS, on_window_focus)
    con.on(Event.WINDOW_NEW, on_window_new)
    con.on(Event.WINDOW_CLOSE, on_window_close)
    con.on(Event.BINDING, on_binding)

    try:
        con.main()
    except BaseException as e:
        print("restarting after exception:")
        print(e)
        main()


main()
