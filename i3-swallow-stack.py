#!/usr/bin/env python3

from i3ipc import Connection
import subprocess
import argparse

parser = argparse.ArgumentParser(description="i3-swallow-stack")
parser.add_argument("-d",
                    action="store_true",
                    help="Don't move window back to original parent on exit.")
parser.add_argument("-t",
                    action="store_true",
                    help="Use i3's tabbed layout instead of stack.")
parser.add_argument("cmd", nargs="+", help="Command to be executed")
args, cmdargs = parser.parse_known_args()

c = Connection()

tree = c.get_tree()
focused = tree.find_focused()

if (len(focused.parent.nodes) > 1):
    c.command("[con_id=%d] split vertical" % focused.id)

layout = "tabbed" if args.t is True else "stacked"

c.command("[con_id=%d] layout %s" % (focused.id, layout))

parent = focused.parent

subprocess.call(args.cmd + cmdargs, shell=False)

if args.d is True:
    exit

old_parent = c.get_tree().find_by_id(parent.id)

if (old_parent is not None):
    c.command("[con_id=%d] mark --add parent" % focused.parent.id)
    c.command("[con_id=%d] move container to mark parent" % focused.id)
    c.command("[con_id=%d] unmark parent" % focused.parent.id)