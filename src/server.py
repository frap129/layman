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
from os import unlink, mkfifo
from queue import Queue
from threading import Thread

PIPE = "/tmp/layman.pipe"

class MessageQueue(Queue):
    def __init__(self, maxsize=0):
        super().__init__(maxsize=0)
        self.on_change_listeners = []

    def _put(self, msg):
        # Add to queue
        super()._put(msg)

        # Run any listeners on a separate thread
        for listener in self.on_change_listeners:
            listener(msg)

    def registerListener(self, listener):
        self.on_change_listeners.append(listener)

class MessageServer():

    def __init__(self, callback):
        self.callback = callback
        self.queue = MessageQueue()
        self.queue.registerListener(callback)

        try:
            unlink(PIPE)
        except:
            "do nothing"

        mkfifo(PIPE, 0o660)
        thread = Thread(target=self.readPipe)
        thread.start()

    def readPipe(self):
        while True:
            with open(PIPE) as fifo:
                self.queue.put(fifo.read())

