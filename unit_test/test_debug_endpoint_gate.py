"""The /debug endpoint hands its query string to exec(), so who may reach it is a real boundary.

`GET /debug?<python>` goes to `handle_debug_command` (engine/device/web/server/server_sync.py:20),
which unquotes the raw query string and feeds it to the console, ending at `exec(cmd)` in
`game/world/cheat/cheat_cmd_helper.py:481`. `IsCommandSafe` in between is a blocklist of module
names and stops roughly one payload in eight, so it is not the boundary.

The route was registered with `AddAwaitGetSecurity`, whose `IsAuthenticate` returns True for
everyone when no password is configured, and the shipped launch.json has `"password": ""`. Binding
defaults to 127.0.0.1, so this only bites when someone exposes the port to play with friends, which
is exactly what the 4-player mode needs.

`game/` cannot be imported on its own because of a circular import, so `import engine` comes first.
"""
import unittest

import engine  # noqa: F401  must precede any game import
from engine.network.web_server import WebServer, PASSWORD


class _FakeRequest:
    """Only the two attributes the gate reads."""

    def __init__(self, remote, cookies=None):
        self.remote = remote
        self.cookies = cookies or {}


class _Password:
    """Configure a server password for the duration of a test."""

    def __init__(self, password: str):
        self.password = password

    def __enter__(self):
        self.previous = PASSWORD.value
        PASSWORD.value = self.password
        return WebServer()

    def __exit__(self, *exc):
        PASSWORD.value = self.previous


class TestDebugEndpointGate(unittest.TestCase):

    def test_remote_request_is_refused_when_no_password_is_set(self):
        """The configuration that matters: a host sharing a game with friends and no password.

        `IsAuthenticate` says yes to everyone here, which is why the gate cannot be built on it.
        """
        with _Password("") as server:
            request = _FakeRequest("192.168.1.50")

            self.assertTrue(server.IsAuthenticate(request),
                            "precondition: the existing check passes everyone without a password")
            self.assertFalse(server.MayRunArbitraryCommands(request),
                             "a LAN client reached an endpoint that ends in exec()")


    def test_loopback_is_allowed_without_a_password(self):
        """Playing solo on your own machine must not need a password to use the console."""
        with _Password("") as server:
            for remote in ("127.0.0.1", "127.0.0.5", "::1"):
                self.assertTrue(server.MayRunArbitraryCommands(_FakeRequest(remote)),
                                f"{remote} should count as this machine")

    def test_remote_request_is_allowed_with_the_right_password(self):
        """Hosting for friends still works, once a password is actually configured."""
        with _Password("hunter2") as server:
            cookie = {"session_token": server.hash_password}
            self.assertTrue(
                server.MayRunArbitraryCommands(_FakeRequest("192.168.1.50", cookie)))

    def test_remote_request_is_refused_with_the_wrong_password(self):
        with _Password("hunter2") as server:
            cookie = {"session_token": "not-the-password"}
            self.assertFalse(
                server.MayRunArbitraryCommands(_FakeRequest("192.168.1.50", cookie)))

    def test_unknown_peer_is_refused(self):
        """Fail closed. No address, or one that will not parse, is not this machine."""
        with _Password("") as server:
            self.assertFalse(server.MayRunArbitraryCommands(_FakeRequest(None)))
            self.assertFalse(server.MayRunArbitraryCommands(_FakeRequest("")))
            self.assertFalse(server.MayRunArbitraryCommands(_FakeRequest("not-an-address")))
            self.assertFalse(server.MayRunArbitraryCommands(_FakeRequest("127.0.0.1, 10.0.0.1")))


class TestRegisteredRoute(unittest.TestCase):
    """The predicate is only useful if the registered route actually consults it."""

    def _handler_for(self, server, path):
        for route in server.web_app.router.routes():
            if route.resource and route.resource.canonical == path:
                return route.handler
        self.fail(f"no route registered at {path}")

    def test_the_wrapper_refuses_a_remote_request_with_403(self):
        import asyncio

        reached = []

        async def handler(request):
            reached.append(request)
            from aiohttp import web
            return web.Response(text="ran")

        with _Password("") as server:
            server.AddAwaitGetDebugSecurity('/debug_test', handler)
            wrapped = self._handler_for(server, '/debug_test')

            response = asyncio.run(wrapped(_FakeRequest("192.168.1.50")))

            self.assertEqual(response.status, 403)
            self.assertEqual(reached, [], "the handler ran despite the gate refusing")


if __name__ == "__main__":
    unittest.main()
