#!/usr/bin/env python3

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
parser.add_option("-n",
                  "--nested",
                  dest="move_nested",
                  action="store_true",
                  help="Also move new windows which are created in nested containers.")
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


def grab_focused(c, e):
    tree = c.get_tree()
    focused_window = tree.find_by_id(e.container.id)

    if is_excluded(focused_window):
        return None

    return focused_window


def find_last(con):
    if len(con.nodes) > 1:
        return find_last(con.nodes[-1])

    return con


def on_window_new(c, e):
    new_window = grab_focused(c, e)

    if new_window is None:
        return

    if options.move_nested is not True and new_window.parent != new_window.workspace():
        return

    last = find_last(new_window.workspace())
    c.command("[con_id=%d] mark --add last" % last.id)
    c.command("[con_id=%d] move container to mark last" % new_window.id)
    c.command("[con_id=%d] unmark last" % last.id)


def on_window_focus(c, e):
    focused_window = grab_focused(c, e)

    if focused_window is None:
        return

    workspace = focused_window.workspace()

    if len(workspace.nodes) < 2:
        return

    last = find_last(workspace)
    if last == workspace.nodes[1] and last.layout != "splitv":
        c.command("[con_id=%d] split vertical" % last.id)


def main():
    c = Connection()
    c.on(Event.WINDOW_FOCUS, on_window_focus)
    c.on(Event.WINDOW_NEW, on_window_new)

    try:
        c.main()
    except BaseException as e:
        print("restarting after exception:")
        print(e)
        main()


main()
