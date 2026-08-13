"""What the auth and version guards send back, and for how long a client keeps it.

Two defects, found while a status card refused to draw for a whole session and survived restarts.

`ReadFile` stamps `HeaderCache` (a year) on every release build. The version-mismatch guard page
went out under that header, so a client that asked for a card image during a mismatch cached an
HTML page under the card's URL and drew nothing there for a year. Restarting the server does not
help, because nothing is wrong on the server.

Worse, the guard answered *image* routes with that page at status 200. A 200 is a successful
answer, so there was nothing for the browser, or for `save_local`, to treat as a failure.

`game/` cannot be imported on its own because of a circular import, so `import engine` comes first.
"""
import asyncio
import unittest

import engine  # noqa: F401  must precede any game import
from aiohttp import web
from engine.lib import Ver
from engine.network.web_server import WebServer, PASSWORD

Ver.Initialize()  # the server does this at startup; `IsVersionMatch` reads what it sets


class _FakeGetRequest:
    """Only what the guard touches before it decides to refuse."""

    def __init__(self, cookies=None):
        self.cookies = cookies or {}
        self.remote = "127.0.0.1"


def _guarded_image_route(password: str = ""):
    """A resource route registered the way the image and `save_local` routes are."""
    previous = PASSWORD.value
    PASSWORD.value = password
    try:
        server = WebServer()
        server.AddNonAwaitGetSecurity(
            '/card', lambda request: web.Response(body=b'\xff\xd8 real art',
                                                  content_type='image/jpeg'))
        for route in server.web_app.router.routes():
            if route.resource and route.resource.canonical == '/card':
                return route.handler
        raise AssertionError("no route registered at /card")
    finally:
        PASSWORD.value = previous


class TestGuardPagesAreNotCached(unittest.TestCase):

    def test_the_version_guard_page_is_not_cacheable(self):
        """This is the one that outlived the mismatch it was reporting."""
        response = WebServer().LoadHtmlCleanCache()

        self.assertEqual(response.headers['Cache-Control'], 'no-store',
                         "the version-mismatch page was cached under the URL it was refusing")

    def test_the_authenticate_page_is_not_cacheable(self):
        """Same header, same file-reading path, so it had the same problem."""
        response = WebServer().LoadHtmlAuthenticate()

        self.assertEqual(response.headers['Cache-Control'], 'no-store',
                         "a cached login page would outlive the session it belongs to")


class TestResourceRoutesRefuseInsteadOfAnsweringWithAPage(unittest.TestCase):
    """Image routes and `save_local` sit behind this guard. Neither can render HTML."""

    def test_a_version_mismatch_is_not_a_successful_image(self):
        handler = _guarded_image_route()

        response = asyncio.run(handler(_FakeGetRequest({'app_version': 'stale'})))

        self.assertNotEqual(response.status, 200,
                            "a refused image answered 200, so nothing downstream saw a failure")
        self.assertEqual(response.status, 409)
        self.assertNotIn('html', response.content_type,
                         "an HTML body was served under a card's image URL")

    def test_a_refusal_is_never_cached(self):
        """The year-long header is what made one bad moment permanent."""
        handler = _guarded_image_route()

        response = asyncio.run(handler(_FakeGetRequest({'app_version': 'stale'})))

        self.assertEqual(response.headers['Cache-Control'], 'no-store')

    def test_an_unauthenticated_request_is_refused_the_same_way(self):
        handler = _guarded_image_route(password="hunter2")

        response = asyncio.run(handler(_FakeGetRequest()))

        self.assertEqual(response.status, 401)
        self.assertNotIn('html', response.content_type)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')


if __name__ == "__main__":
    unittest.main()
