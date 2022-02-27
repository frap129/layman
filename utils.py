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
                      metavar="ws1,ws2,.. ",
                      help="List of workspaces that should be ignored.")
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
