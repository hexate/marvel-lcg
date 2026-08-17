"""Whether the port probe agrees with the bind it is standing in for. J14.

Quitting the game and starting it again within a few seconds died on
`AssertionError: ip='127.0.0.1', port=2345`, with nothing listening anywhere in `netstat`. The
cause was that `IsPortAvailable` opened a plain socket, while the real listener is opened by
`asyncio.create_server`, which sets `SO_REUSEADDR` on POSIX. The probe was therefore stricter than
the bind it predicted, and refused to start over a port the server would have taken.

A browser left open on the game is what put the port into that state: its keep-alive connections
leave the server side in `TIME_WAIT` after the process exits.

`game/` cannot be imported on its own because of a circular import, so `import engine` comes first.
"""
import socket
import unittest

import engine  # noqa: F401  must precede any game import
from engine.network.net_lib import NetLib


def _port_in_time_wait():
    """A real completed connection, closed server-side first, leaves that port in TIME_WAIT.

    Returns the port, and the listener is gone by the time this returns.
    """
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('127.0.0.1', 0))
    port = server.getsockname()[1]
    server.listen(1)

    client = socket.socket()
    client.connect(('127.0.0.1', port))
    accepted, _ = server.accept()

    # Closing the accepted end first is what parks this side in TIME_WAIT.
    accepted.close()
    server.close()
    client.close()
    return port


def _plain_bind_refused(port):
    """Whether a socket without SO_REUSEADDR is refused, i.e. whether TIME_WAIT really happened."""
    s = socket.socket()
    try:
        s.bind(('127.0.0.1', port))
        return False
    except OSError:
        return True
    finally:
        s.close()


class TestProbeMatchesTheRealBind(unittest.TestCase):

    def test_a_port_in_time_wait_is_reported_available(self):
        """The defect. The server can bind here, so the probe must not say otherwise."""
        port = _port_in_time_wait()

        if not _plain_bind_refused(port):
            self.skipTest("this platform did not leave the port in TIME_WAIT, nothing to prove")

        self.assertIsNone(
            NetLib.WhyPortUnavailable('127.0.0.1', port),
            "the probe refused a port that asyncio.create_server would have bound, which is what "
            "made restarting the game fail with nothing listening")

    def test_a_live_listener_is_still_reported_unavailable(self):
        """The probe still has to catch a real clash, or it is useless."""
        holder = socket.socket()
        holder.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        holder.bind(('127.0.0.1', 0))
        port = holder.getsockname()[1]
        holder.listen(1)
        try:
            reason = NetLib.WhyPortUnavailable('127.0.0.1', port)
            self.assertIsNotNone(reason, "a port with a live listener was reported as free")
            self.assertFalse(NetLib.IsPortAvailable('127.0.0.1', port))
        finally:
            holder.close()

    def test_the_reason_says_what_the_os_said(self):
        """The other half of J14: the failure used to name only the port you already typed."""
        holder = socket.socket()
        holder.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        holder.bind(('127.0.0.1', 0))
        port = holder.getsockname()[1]
        holder.listen(1)
        try:
            reason = NetLib.WhyPortUnavailable('127.0.0.1', port)
            self.assertIn('errno', reason,
                          "the reason has to carry the errno, since EADDRINUSE and EADDRNOTAVAIL "
                          "need different fixes")
        finally:
            holder.close()

    def test_a_free_port_is_available(self):
        probe = socket.socket()
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
        probe.close()

        self.assertIsNone(NetLib.WhyPortUnavailable('127.0.0.1', port))
        self.assertTrue(NetLib.IsPortAvailable('127.0.0.1', port))

    def test_an_address_that_is_not_ours_is_a_reason_not_a_crash(self):
        """The old bare `except` hid this by reporting every failure as a busy port."""
        reason = NetLib.WhyPortUnavailable('203.0.113.1', 2345)  # TEST-NET-3, cannot be local

        self.assertIsNotNone(reason)
        self.assertIn('errno', reason)


if __name__ == "__main__":
    unittest.main()
