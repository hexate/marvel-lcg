"""What the auth and version guards send back, and for how long a client keeps it.

Two defects, found while a status card refused to draw for a whole session and survived restarts.

`ReadFile` stamps `HeaderCache` (a year) on every release build. The version-mismatch guard page
went out under that header, so a client that asked for a card image during a mismatch cached an
HTML page under the card's URL and drew nothing there for a year. Restarting the server does not
help, because nothing is wrong on the server.

Worse, the guard answered *image* routes with that page at status 200. A 200 is a successful
answer, so there was nothing for the browser, or for `save_local`, to treat as a failure.

A third defect, J18, found later in a browser and belonging in the same file: the route that issues
the `app_version` cookie was itself cached for a year, deliberately, as `image/jpeg`. A cached copy
is replayed without `Set-Cookie`, so a client that lost the cookie could never obtain another and
every guarded route refused it from then on. Same shape as the two above, and the same header at
fault: J17 cached the refusal, J18 cached the thing that lifts it.

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


def _version_route():
    """The `/get_version` handler, reached the way it is actually registered."""
    server = WebServer()
    server.AddDefaultGet()
    for route in server.web_app.router.routes():
        if route.resource and route.resource.canonical == '/get_version':
            return route.handler
    raise AssertionError("no route registered at /get_version")


class TestTheVersionCookieRouteIsNeverCached(unittest.TestCase):
    """J18. This route's only job is issuing a cookie, and a cached response cannot do that."""

    def test_the_cookie_route_is_not_cacheable(self):
        response = asyncio.run(_version_route()(_FakeGetRequest()))

        self.assertEqual(response.headers['Cache-Control'], 'no-store',
                         "a stored copy is replayed without Set-Cookie, so the cookie it exists "
                         "to issue can never be obtained again")

    def test_the_cookie_is_still_issued(self):
        """The header change must not cost the thing the route is for."""
        response = asyncio.run(_version_route()(_FakeGetRequest()))

        cookie = response.cookies.get('app_version')
        self.assertIsNotNone(cookie, "the route stopped issuing the cookie it exists to issue")
        self.assertEqual(cookie.value, str(Ver.ui_version_str))
        self.assertEqual(cookie['path'], '/', "a narrower path would not be sent to guarded routes")

    def test_the_route_answers_a_client_that_has_no_cookie_yet(self):
        """The recovery cannot be behind the guard it recovers from.

        Registered `need_check_version=False` for this reason. Putting the version guard on this
        route would refuse exactly the clients that need it and leave no way back in at all.
        """
        response = asyncio.run(_version_route()(_FakeGetRequest()))

        self.assertEqual(response.status, 200,
                         "the only route that can hand out the cookie refused a client for not "
                         "having it")
        self.assertIn(str(Ver.ui_version_str), response.text)


class TestCodeIsNotCachedLikeAnAsset(unittest.TestCase):
    """Card art never changes for a given id; a stylesheet changes every time you edit it.

    Both used to go out under the same year-long header, so every UI change was invisible until
    someone hard reloaded, and the obvious reading of that is that the change did not work.
    """

    def test_markup_styles_and_scripts_revalidate(self):
        server = WebServer()

        for path in ('/public/scene.html', '/public/css/menu/style.css',
                     '/public/js/marvel/hover.js', '/public/js/marvel/hover.ts',
                     '/public/js/marvel/hover.js.map', '/data/cards.json'):
            with self.subTest(path=path):
                header = server.CacheHeaderFor(path)
                self.assertNotIn('max-age=31536000', header['Cache-Control'],
                                 f"{path} was cached for a year, so editing it changes nothing "
                                 f"the browser will show you")

    def test_card_art_and_fonts_still_cache_hard(self):
        """The cache is worth having for these: re-fetching art is the slow thing it prevents."""
        server = WebServer()

        for path in ('/01109.jpg', '/public/fonts/ChampionsIcons.ttf', '/assets/sounds/x.mp3'):
            with self.subTest(path=path):
                self.assertIn('max-age=31536000', server.CacheHeaderFor(path)['Cache-Control'])

    def test_the_split_is_by_extension_not_mime_type(self):
        """`.ts` is `video/mp2t` to `MimeType` and `.map` is not known at all.

        A MIME-based split would hand both the asset cache, which is backwards for source that
        changes constantly.
        """
        server = WebServer()

        self.assertEqual(server.CacheHeaderFor('/a/b/hover.ts'),
                         server.CacheHeaderFor('/a/b/hover.js'))
        self.assertEqual(server.CacheHeaderFor('/a/b/hover.js.map'),
                         server.CacheHeaderFor('/a/b/hover.js'))


if __name__ == "__main__":
    unittest.main()
