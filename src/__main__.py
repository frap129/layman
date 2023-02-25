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
import sys

from . import layman
from .server import PIPE

def main():
    """Application entry point."""

    # Write command if args were passed
    if len(sys.argv) > 1:
        command = ' '.join(sys.argv).replace("%s " % sys.argv[0], '')
        pipe = open(PIPE, "w")
        pipe.write(command)
        pipe.close()
        exit()

    # Start layman
    daemon = layman.Layman()
    daemon.init()

if __name__ == '__main__':
    main()
