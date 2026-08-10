"""What `/authenticate` actually does, and what it should do (tracker item J2).

The handler hashes whatever password it is given and sets that as the `session_token` cookie,
without ever comparing it to the configured one. That reads like an authentication bypass and is
not one: `IsAuthenticate` compares the cookie against `md5(configured password)`, so a wrong guess
produces a wrong cookie and is refused on the next request. Verified before writing these tests.

What it does cause is a server that always answers "fine" to a login attempt, so a client cannot
tell a correct password from a wrong one, and a 500 when the request body is not what it expects.

`game/` cannot be imported on its own because of a circular import, so `import engine` comes first.
"""
import asyncio
import unittest

import engine  # noqa: F401  must precede any game import
from engine.network.web_server import WebServer, PASSWORD


class _FakeJsonRequest:
    """Only what the handler touches: an awaitable json() and a cookie jar."""

    def __init__(self, payload, *, raises=None):
        self.payload = payload
        self.raises = raises
        self.cookies = {}
        self.remote = "192.168.1.50"

    async def json(self):
        if self.raises:
            raise self.raises
        return self.payload


class _Password:
    def __init__(self, password: str):
        self.password = password

    def __enter__(self):
        self.previous = PASSWORD.value
        PASSWORD.value = self.password
        server = WebServer()
        server.AddDefaultGet()
        return server

    def __exit__(self, *exc):
        PASSWORD.value = self.previous


def _handler_for(server, path):
    for route in server.web_app.router.routes():
        if route.resource and route.resource.canonical == path:
            return route.handler
    raise AssertionError(f"no route registered at {path}")


class TestAuthenticateEndpoint(unittest.TestCase):

    def test_a_wrong_password_is_refused(self):
        """Answering 200 to every attempt means the client cannot tell it got in."""
        with _Password("hunter2") as server:
            handler = _handler_for(server, '/authenticate')

            response = asyncio.run(handler(_FakeJsonRequest({"password": "wrong"})))

            self.assertEqual(response.status, 401)
            self.assertNotIn("session_token", response.cookies,
                             "a refused attempt still handed out a session cookie")


    def test_the_right_password_still_gets_a_session(self):
        with _Password("hunter2") as server:
            handler = _handler_for(server, '/authenticate')

            response = asyncio.run(handler(_FakeJsonRequest({"password": "hunter2"})))

            self.assertEqual(response.status, 200)
            self.assertEqual(response.cookies["session_token"].value, server.hash_password)

    def test_a_malformed_body_is_a_client_error_not_a_crash(self):
        """`data.get('password')` returned None and then `None.encode()` raised, answering 500."""
        with _Password("hunter2") as server:
            handler = _handler_for(server, '/authenticate')

            for request in (_FakeJsonRequest({}),
                            _FakeJsonRequest({"passwrod": "typo"}),
                            _FakeJsonRequest(None, raises=ValueError("not json"))):
                response = asyncio.run(handler(request))
                self.assertEqual(response.status, 400)

    def test_no_configured_password_accepts_the_attempt(self):
        """Refusing here would be strange when every other route already admits everyone.

        That every route admits everyone is the actual problem, and it is not this endpoint's to
        fix. See the loopback gate on /debug, and J2 in the tracker.
        """
        with _Password("") as server:
            handler = _handler_for(server, '/authenticate')

            response = asyncio.run(handler(_FakeJsonRequest({"password": "anything"})))

            self.assertEqual(response.status, 200)


class TestPasswordComparison(unittest.TestCase):

    def test_only_the_configured_password_matches(self):
        with _Password("hunter2") as server:
            self.assertTrue(server.IsPasswordCorrect("hunter2"))
            self.assertFalse(server.IsPasswordCorrect("Hunter2"))
            self.assertFalse(server.IsPasswordCorrect(""))
            self.assertFalse(server.IsPasswordCorrect(None))
            self.assertFalse(server.IsPasswordCorrect(12345))


class TestBindAddressClassification(unittest.TestCase):
    """Whether a bind address is reachable from off this machine, which decides the startup warning.

    The warning itself is not exercised here: firing it means constructing WebDeviceManager, which
    binds real ports. This pins the part that is easy to get wrong.
    """

    def test_only_loopback_counts_as_local(self):
        from engine.device.manager.web.manager import WebDeviceManager

        for ip in ("127.0.0.1", "127.0.0.5", "::1"):
            self.assertTrue(WebDeviceManager.IsLoopbackAddress(ip), f"{ip} is this machine")

        for ip in ("0.0.0.0", "::", "192.168.1.50", "10.0.0.1", "not-an-address", ""):
            self.assertFalse(WebDeviceManager.IsLoopbackAddress(ip),
                             f"{ip} is reachable from elsewhere, or unknown, so warn")


if __name__ == "__main__":
    unittest.main()
