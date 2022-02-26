#!/usr/bin/env python3

from i3ipc import Event, Connection
from optparse import OptionParser
from setproctitle import setproctitle


def get_comma_separated_args(option, opt, value, parser):
    setattr(parser.values, option.dest, value.split(","))


class WorkspaceList(dict):
    def __missing__(self, key):
        return None


class WorkspaceNode:
    def __init__(self, master_id, stack_ids):
        self.master_id = master_id
        self.stack_ids = stack_ids


workspaces = WorkspaceList()

parser = OptionParser()
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
(options, args) = parser.parse_args()


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


def move_window(c, subject, target):
    c.command("[con_id=%d] mark --add move_target" % target)
    c.command("[con_id=%d] move container to mark move_target" % subject)
    c.command("[con_id=%d] unmark move_target" % target)


def push_window(c, subject, workspace):
    # Record workspace if it's new
    workspace_state = workspaces[workspace] 
    if workspace_state is None:
        workspaces[workspace] = WorkspaceNode(subject, [])
        return

    # Only record window if stack is empty
    if workspace_state.stack_ids == []:
        # Check if master is empty
        if workspace_state.master_id == 0:
            workspace_state.master_id = subject
        else:
            workspace_state.stack_ids.append(subject)
        return
        
    # Put new window at top of stack
    target = workspace_state.stack_ids[0]
    move_window(c, subject, target)
    for window in workspace_state.stack_ids:
        c.command("move up")

    # Swap with master
    old_master = workspace_state.master_id
    c.command("[con_id=%d] swap container with con_id %d" % (subject, old_master))  

    # Update record
    workspace_state.stack_ids.append(workspace_state.master_id)
    workspace_state.master_id = subject


def pop_window(c, workspace):
    # Check if last window is being popped
    if workspaces[workspace].stack_ids == []:
        workspaces[workspace].master_id = 0
        return

    subject = workspaces[workspace].stack_ids.pop()
    workspaces[workspace].master_id = subject

    c.command("[con_id=%s] focus" % subject)
    c.command("move left")


def on_window_new(c, e):
    new_window = grab_focused(c)

    if new_window is None:
        return

    # only windows created on workspace level get moved if nested option isn't enabled
    workspace = new_window.workspace()
    if options.move_nested is not True and new_window.parent != workspace:
        return

    # new window gets moved behind last window found
    push_window(c, new_window.id, workspace.id)


def on_window_focus(c, e):
    focused_window = grab_focused(c)

    if focused_window is None:
        return

    workspace = focused_window.workspace()

    if len(workspace.nodes) < 2:
        return

    # Ignore untracked workspaces
    # TODO Autoarrange untracked workspaces
    if workspaces[workspace.id] is None:
        return

    # splith is not supported yet. idk how to differentiate between splith and nested splith.
    if workspaces[workspace.id].stack_ids != []:
        layout = options.stack_layout or "splitv"
        bottom = workspaces[workspace.id].stack_ids[0]

        c.command("[con_id=%d] split vertical" % bottom)
        c.command("[con_id=%d] layout %s" % (bottom, layout))


def on_window_close(c, e):
    if options.disable_rearrange is not True:
        # check if master window was closed 
        for workspace in workspaces:
            # master window disappears and only stack container left
            if workspaces[workspace].master_id == e.container.id:
                pop_window(c, workspace)


def main():
    setproctitle("i3-master-layout")
    c = Connection()
    c.on(Event.WINDOW_FOCUS, on_window_focus)
    c.on(Event.WINDOW_NEW, on_window_new)
    c.on(Event.WINDOW_CLOSE, on_window_close)

    try:
        c.main()
    except BaseException as e:
        print("restarting after exception:")
        print(e)
        main()


main()
