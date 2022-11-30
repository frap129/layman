"""
Copyright 2022 Joe Maples <joe@maples.dev>

This file is part of layman.

layman is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

layman is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
layman. If not, see <https://www.gnu.org/licenses/>. 
"""

from dataclasses import dataclass, field
from optparse import OptionParser
from dataclasses import dataclass, field
import os
import queue
import threading

import config


class SimpleDict(dict):
    def __missing__(self, key):
        return None


@dataclass
class EventItem:
    event:  any


class EventQueue(queue.Queue):
    def __init__(self, maxsize=0):
        super().__init__(maxsize=0)
        self.on_change_listeners = []


    def _put(self, event):
        # Add to queue
        super()._put(event)

        # Run any listeners on a separate thread
        for listener in self.on_change_listeners:
            thread = threading.Thread(target=listener)
            thread.start()


    def registerListener(self, listener):
        self.on_change_listeners.append(listener)


def getCommaSeparatedArgs(option, opt, value, parser):
    setattr(parser.values, option.dest, value.split(","))


def findFocusedWindow(con):
    return con.get_tree().find_focused()


def findFocusedWorkspace(con):
    return con.get_tree().find_focused().workspace()


def getConfigPath():
    parser = OptionParser()
    parser.add_option("-c",
                      "--config",
                      dest="configPath",
                      type="string",
                      action="callback",
                      callback=getCommaSeparatedArgs,
                      metavar=config.CONFIG_PATH,
                      help="Path to user config file.")

    try:
        path = parser.parse_args()[0].configPath[0]
    except:
        path = os.path.expanduser("~") + "/" + config.CONFIG_PATH

    return path
