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
import tomli
from logging import exception


CONFIG_PATH = ".config/layman/config.toml"

TABLE_LAYMAN = "layman"
TABLE_WORKSPACE = "workspace"
TABLE_OUTPUT = "output"
KEY_DEBUG = "debug"
KEY_EXCLUDED_WORKSPACES = "excludeWorkspaces"
KEY_EXCLUDED_OUTPUTS = "excludeOutputs"
KEY_LAYOUT = "defaultLayout"


class LaymanConfig():
    def __init__(self, con, configPath):
        self.reloadConfig(con, configPath)


    def parse(self):
        with open(self.configPath, "rb") as f:
            try:
                return tomli.load(f)
            except Exception as e:
                exception(e)
                return {}


    def reloadConfig(self, con, configPath):
        self.configPath = configPath or CONFIG_PATH
        self.con = con
        self.configDict = self.parse()


    def getDefault(self, key):
        try:
            return self.configDict[TABLE_LAYMAN][key]
        except KeyError:
            return None


    def getForWorkspace(self, workspaceNum, key):
        # Try to get value for the workspace
        try:
            value = self.configDict[TABLE_WORKSPACE][str(workspaceNum)][key]
        except KeyError:
            # If workspace config doesn't have the key, try output
            output = None
            for workspace in self.con.get_workspaces():
                if workspace.num == workspace.num:
                    output = workspace.output
            if output:
                try:
                    self.configDict[TABLE_OUTPUT][output][key]
                except KeyError:
                    pass

            # If output config doesn't have the key, falback to default
            try:
                value = self.configDict[TABLE_LAYMAN][key]
            except KeyError:
                value = None

        return value
