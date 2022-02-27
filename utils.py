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

from optparse import OptionParser


def getCommaSeparatedArgs(option, opt, value, parser):
    setattr(parser.values, option.dest, value.split(","))


def findFocused(con):
    tree = con.get_tree()
    focusedWindow = tree.find_focused()
    return focusedWindow


def getUserOptions():
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
                      callback=getCommaSeparatedArgs,
                      metavar="1,2,.. ",
                      help="List of workspaces numbers that should be ignored.")
    parser.add_option("-o",
                      "--outputs",
                      dest="outputs",
                      type="string",
                      action="callback",
                      callback=getCommaSeparatedArgs,
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
    
    return parser.parse_args()[0]
