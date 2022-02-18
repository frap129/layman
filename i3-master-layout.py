#!/usr/bin/env python3

from re import I
from i3ipc import Event, Connection
from optparse import OptionParser


def get_comma_separated_args(option, opt, value, parser):
    setattr(parser.values, option.dest, value.split(","))


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
parser.add_option("-n", "--nested", dest="move_nested", action="store_true", help="Also move new windows which are created in nested containers.")
parser.add_option("--disable-rearrange",
                  dest="disable_on_close",
                  action="store_true",
                  help="Disable the rearrangement of windows when the master window is closed.")
(options, args) = parser.parse_args()


def is_excluded(window):
    if window is None:
        return True

    if window.type != "con":
        return True

    if window.workspace() is None:
        return True

    if "on" in window.floating:
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


def find_last(con):
    if len(con.nodes) > 1:
        return find_last(con.nodes[-1])

    return con


def move_window(c, subject, target):
    c.command("[con_id=%d] mark --add move_target" % target.id)
    c.command("[con_id=%d] move container to mark move_target" % subject.id)
    c.command("[con_id=%d] unmark move_target" % target.id)


def on_window_new(c, e):
    new_window = grab_focused(c)

    if new_window is None:
        return

    # only windows created on workspace level get moved if nested option isn't enabled
    if options.move_nested is not True and new_window.parent != new_window.workspace():
        return

    # new window gets moved behind last window found
    move_window(c, new_window, find_last(new_window.workspace()))


def on_window_focus(c, e):
    focused_window = grab_focused(c)

    if focused_window is None:
        return

    workspace = focused_window.workspace()

    if len(workspace.nodes) < 2:
        return

    last = find_last(workspace)
    # last window is also 2nd window
    if last == workspace.nodes[1] and last.layout != "splitv":
        c.command("[con_id=%d] splitv" % last.id)


def on_window_close(c, e):
    focused_window = grab_focused(c)

    if focused_window is None:
        return

    workspace = focused_window.workspace()
    # master window closed and only stack container left
    if len(workspace.nodes) == 1:
        # move focused window (usually last focused window of stack) back to workspace level
        move_window(c, focused_window, workspace)
        # now the stack if it exists is first node and gets moved to the end of workspace
        move_window(c, workspace.nodes[0], workspace)


def main():
    c = Connection()
    c.on(Event.WINDOW_FOCUS, on_window_focus)
    c.on(Event.WINDOW_NEW, on_window_new)
    if options.disable_on_close is not True:
        c.on(Event.WINDOW_CLOSE, on_window_close)

    try:
        c.main()
    except BaseException as e:
        print("restarting after exception:")
        print(e)
        main()


main()
