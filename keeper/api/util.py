# This file is part of Maker Keeper Framework.
#
# Copyright (C) 2017 reverendus
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import asyncio
import threading


def synchronize(futures) -> list:
    if len(futures) > 0:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(asyncio.gather(*futures, loop=loop))
        finally:
            loop.close()
    else:
        return []


def int_to_bytes32(value: int) -> bytes:
    assert(isinstance(value, int))
    return value.to_bytes(32, byteorder='big')


def bytes_to_int(value) -> int:
    if isinstance(value, bytes) or isinstance(value, bytearray):
        return int.from_bytes(value, byteorder='big')
    elif isinstance(value, str):
        b = bytearray()
        b.extend(map(ord, value))
        return int.from_bytes(b, byteorder='big')
    else:
        raise AssertionError


def bytes_to_hexstring(value) -> str:
    assert(isinstance(value, bytes) or isinstance(value, bytearray))
    return "0x" + "".join(map(lambda b: format(b, "02x"), value))


def hexstring_to_bytes(value: str) -> bytes:
    assert(isinstance(value, str))
    assert(value.startswith("0x"))
    return bytes.fromhex(value.replace("0x", ""))


class AsyncCallback:
    """Decouples callback invocation from the web3.py filter.

    Decouples callback invocation from the web3.py filter by executing the callback
    in a dedicated thread. If we make web3.py trigger the callback directly, and the callback
    execution takes more than 60 seconds, the `eth_getFilterChanges` call also will not
    get called for 60 seconds and more which will make the filter expire in Parity side.
    It's 60 seconds for Parity, this could be a different value for other nodes,
    but the filter will eventually expire sooner or later anyway.

    Invoking the callback logic in a separate thread allows the web3.py Filter thread
    to keep calling `eth_getFilterChanges` regularly, so the filter stays active.

    Attributes:
        callback: The callback function to be invoked in a separate thread.
    """
    def __init__(self, callback):
        self.callback = callback
        self.thread = None

    def trigger(self, on_start=None, on_finish=None) -> bool:
        """Invokes the callback in a separate thread, unless one is already running.

        If callback isn't currently running, invokes it in a separate thread and returns `True`.
        If the previous callback invocation still hasn't finished, doesn't do anything
        and returns `False`.

        Arguments:
            on_start: Optional method to be called before the actual callback. Can be `None`.
            on_finish: Optional method to be called after the actual callback. Can be `None`.

        Returns:
            `True` if callback has been invoked. `False` otherwise.
        """
        if self.thread is None or not self.thread.is_alive():
            def thread_target():
                if on_start is not None:
                    on_start()
                self.callback()
                if on_finish is not None:
                    on_finish()

            self.thread = threading.Thread(target=thread_target)
            self.thread.start()
            return True
        else:
            return False

    def wait(self):
        """Waits for the currently running callback to finish.

        If the callback isn't running or hasn't even been invoked once, returns instantly."""
        if self.thread is not None:
            self.thread.join()
