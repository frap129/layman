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

class CommandBuilder():
    commands = []

    def __init__(self, conn):
        self.conn = conn


    def clear(self):
        self.commands = []


    def raw(self, command):
        command = {
            "command" : command
        }
        self.commands.append(command)
        return self


    def byId(self, conId, command):
        command = {
            "id" : conId,
            "command" : command
        }
        self.commands.append(command)
        return self


    def addCommandByIdToBuffer(self, buffer, i, commandDict):
        if i != 0:
            prevCommand = self.commands[i - 1]
            if "id" in prevCommand.keys() and prevCommand["id"] == commandDict["id"]:
                return "%s, %s" % (buffer, commandDict["command"])
            else:
                return "%s; [con_id=%d] %s" % (buffer, commandDict["id"], commandDict["command"])
        else:
            return "[con_id=%d] %s" % (commandDict["id"], commandDict["command"])


    def run(self):
        commandBuf = ""
        for i in range(len(self.commands)):
            commandDict = self.commands[i]
            if "id" in commandDict.keys():
                commandBuf = self.addCommandByIdToBuffer(commandBuf, i, commandDict)
            elif i != 0:
                commandBuf = "%s; %s" % (commandBuf, commandDict["command"])
            else:
                commandBuf = commandDict["command"]

        print(commandBuf)

        retVal = self.conn.command(commandBuf)
        self.clear()
        return retVal

