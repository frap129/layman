#!/usr/bin/env python3

from i3ipc import Event, Connection
from optparse import OptionParser
from setproctitle import setproctitle


def get_comma_separated_args(option, opt, value, parser):
    setattr(parser.values, option.dest, value.split(","))

parser = OptionParser()
parser.add_option("-w",
                  "--master-width",
                  dest="master_width",
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
                  dest="stack_layout",
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
                  action="store_false",
                  help="Enable logging")
(options, args) = parser.parse_args()


def log(msg):
    if options.debug is True:
        print(msg)


def is_excluded(window):
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

        
def grab_focused(c):
    tree = c.get_tree()
    focused_window = tree.find_focused()

    if is_excluded(focused_window):
        return None

    return focused_window


class WorkspaceLayoutManager:
    def __init__(self, con, workspace, master_id, master_width, stack_layout):
        self.con = con
        self.workspace = workspace
        self.master_id = master_id
        self.stack_ids = []
        self.master_width = master_width
        self.stack_layout = stack_layout


    def set_master_width():
        con.command('[con_id=%s] resize set %s 0 ppt' % (master_id, master_width))


    def move_window(subject, target):
        con.command("[con_id=%d] mark --add move_target" % target)
        con.command("[con_id=%d] move container to mark move_target" % subject)
        con.command("[con_id=%d] unmark move_target" % target)


    def push_window(subject):
        # Only record window if stack is empty
        if stack_ids == []:
            # Check if master is empty too
            if master_id == 0:
                master_id = subject
            else:
                stack_ids.append(subject)
                set_master_width()
            return

        # Check if we're missing master but have a stack, for some reason
        if master_id == 0:
            master_id = subject
            return

        # Put new window at top of stack
        target = stack_ids[-1]
        move_window(subject, target)
        con.command("[con_id=%s] focus" % subject)
        con.command("move up")

        # Swap with master
        old_master = master_id
        con.command("[con_id=%d] swap container with con_id %d" % (subject, old_master))
        set_master_width()

        # Update record
        workspace_state.stack_ids.append(master_id)
        workspace_state.master_id = subject


    def pop_window():
        # Check if last window is being popped
        if stack_ids == []:
            master_id = 0
            return

        # Move top of stack to master position
        master_id = stack_ids.pop()
        con.command("[con_id=%s] focus" % master_id)
        con.command("move left")
        set_master_width()


    def rotate_up():
        # Exit if less than three windows
        if len(stack_ids) < 2:
            return

        new_master = stack_ids.pop()
        old_master = master_id
        stack_bottom = stack_ids[0]

        # Swap top of stack with master, then move old master to bottom
        con.command("[con_id=%d] swap container with con_id %d" % (new_master, old_master))
        move_window(old_master, stack_bottom)

        # Update record
        master_id = new_master
        stack_ids.insert(0, old_master)


    def swap_master():
        # Exit if less than two windows
        if stack_ids == []:
            return

        # Swap focused window with master
        old_master = master_id
        new_master = stack_ids.pop()
        c.command("[con_id=%d] swap container with con_id %d" % (new_master, old_master))

        # Update record
        workspace_state.master_id = new_master
        workspace_state.stack_ids.append(old_master)


    def new_window(con, event):
        new_window = grab_focused(con)
        
        # New window replcases master, master gets pushed to stack
        print("New window id: %d" % new_window.id)
        push_window(new_window.id, workspace)


    def window_focused(event):
        focused_window = grab_focused(con)

        if focused_window is None:
            return

        # splith is not supported yet. idk how to differentiate between splith and nested splith.
        if stack_ids != []:
            layout = stack_layout or "splitv"
            bottom = stack_ids[0]

            con.command("[con_id=%d] split vertical" % bottom)
            c.command("[con_id=%d] layout %s" % (bottom, layout))


    def window_closed(event):
        print("Closed window id: %d" % event.container.id)
        # Try to remove window from stack, catch if its on a different workspace
        try:
            workspaces[workspace].stack_ids.remove(e.container.id)
            return
        except BaseException as e:
            return


    def binding(event):
        command = event.ipc_data["binding"]["command"].strip()
        if command == "nop rotate up":
            rotate_up()
        elif command == "nop swap master":
            swap_master()

class WorkspaceLayoutManagerDict(dict):
    def __missing__(self, key):
        return None


managers = WorkspaceLayoutManagerDict()


def on_window_new(con, event):
    workspace = event.container.workspace()
    if workspace is None:
        return

    if managers[workspace.id] is None:
        managers[workspace.id] = WorkspaceLayoutManager(con, workspace.id, event.container.id, options.master_width, options.stack_layout)
    
    managers[workspace.id].new_window(event)
    
def on_window_focus(con, event):
    workspace = event.container.workspace()
    if workspace is None:
        return

    if managers[workspace.id] is None:
        managers[workspace.id] = WorkspaceLayoutManager(con, workspace.id, event.container.id, options.master_width, options.stack_layout)
    
    managers[workspace.id].window_focused(event)


def on_window_close(con, event):
    workspace = None
    for wlm in managers:
        if event.container.id in managers[wlm].stack_ids:
            workspace = wlm.workspace

    if workspace is None:
        return

    managers[workspace].window_closed(event)

def on_binding(con, event):
    window = grab_focused(con)
    if window is None:
        return

    workspace = window.workspace()

    if managers[workspace.id] is None:
        managers[workspace.id] = WorkspaceLayoutManager(con, workspace.id, window.id, options.master_width, options.stack_layout)

    
    managers[workspace.id].binding(event)

def main():
    setproctitle("i3-master-layout")
    con = Connection()
    con.on(Event.WINDOW_FOCUS, on_window_focus)
    con.on(Event.WINDOW_NEW, on_window_new)
    con.on(Event.WINDOW_CLOSE, on_window_close)
    #con.on(Event.BINDING, on_binding)

    try:
        con.main()
    except BaseException as e:
        print("restarting after exception:")
        print(e)
        main()


main()
