#!/usr/bin/env python3

from i3ipc import Connection

c = Connection()

tree = c.get_tree()
focused = tree.find_focused()
master = focused.workspace().nodes[0]

c.command("[con_id=%d] swap container with con_id %d" % (focused.id, master.id))
