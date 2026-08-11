"""Tests for what `Cache.LoadImage` remembers about a failed art download (J15).

The defect these pin: a failed fetch produced a placeholder, cached it in `Cache.cache` under the
card's own name, and on any failure that was not a timeout also wrote it to disk as `{card_id}.jpg`.
The memory half meant one bad moment on the network blanked a card for the life of the process, with
no retry, because the next call returned the placeholder from the cache. The disk half was worse: a
generated image under the card's own name cannot be told from real art by `LoadImage`,
`FindImageFile` or `CanLoadImage`, so the card stayed blank in every later run too.

`import engine` precedes any game import to establish the circular-import order.
"""
import tempfile
import unittest
from unittest import mock

import engine  # noqa: F401  must precede any game import
import requests

from engine.file import cache as cache_module
from engine.file.cache import Cache

# A real core card. Nothing under assets/pics or assets/textures is named this, and the test points
# CACHE_FOLDER at a temporary directory, so every lookup has to reach the download path.
CARD_ID = "01153"


def _response(status: int, body: bytes = b"", content_type: str = "image/jpeg") -> requests.Response:
    """A real Response, so `raise_for_status` produces the library's own HTTPError."""
    response = requests.Response()
    response.status_code = status
    response.url = f"https://example.invalid/{CARD_ID}.jpg"
    response._content = body
    response.headers["Content-Type"] = content_type
    return response


class ImageCacheFailureTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from unit_test.harness import EnsureEngine
        EnsureEngine()

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)

        # A cache folder of our own, so nothing here reads or writes the real assets.
        patch_folder = mock.patch.object(cache_module.CACHE_FOLDER, "value", self._temp.name)
        patch_servers = mock.patch.object(cache_module.IMAGE_SERVERS, "value",
                                         ["https://example.invalid/{card_id}.jpg"])
        patch_folder.start()
        patch_servers.start()
        self.addCleanup(patch_folder.stop)
        self.addCleanup(patch_servers.stop)

        # Class-level state, so it has to be put back or it leaks into every later test. The
        # failure counter matters most: left to accumulate it trips the give-up limit partway
        # through the suite and the results become order-dependent.
        original_cache = dict(Cache.cache)
        original_attempts = dict(Cache.fetch_attempts)
        original_failures = Cache.consecutive_fetch_failures
        original_given_up = Cache.downloads_given_up

        def restore() -> None:
            Cache.cache.clear()
            Cache.cache.update(original_cache)
            Cache.fetch_attempts.clear()
            Cache.fetch_attempts.update(original_attempts)
            Cache.consecutive_fetch_failures = original_failures
            Cache.downloads_given_up = original_given_up

        self.addCleanup(restore)
        Cache.cache.pop(CARD_ID, None)
        Cache.fetch_attempts.pop(CARD_ID, None)
        Cache.consecutive_fetch_failures = 0
        Cache.downloads_given_up = False

    def _cache_dir_files(self) -> list[str]:
        import os
        return sorted(os.listdir(self._temp.name))

    def test_timeout_is_not_remembered_and_the_next_call_retries(self):
        """One timeout must not cost the card for the rest of the run. This was J15."""
        with mock.patch.object(cache_module.requests, "get",
                               side_effect=requests.exceptions.Timeout()) as get:
            first = Cache.LoadImage(CARD_ID)
            second = Cache.LoadImage(CARD_ID)

        self.assertTrue(first and second, "a placeholder should still be served for this request")
        self.assertEqual(get.call_count, 2,
                         "the second call served a cached placeholder instead of retrying")
        self.assertNotIn(CARD_ID, Cache.cache,
                         "the placeholder was cached under the card's name, so nothing can retry")
        self.assertEqual(self._cache_dir_files(), [],
                         "a transient failure must leave nothing on disk")

    def test_a_404_records_a_marker_and_never_a_fake_jpeg(self):
        """A definitive miss is worth persisting, but not as something that looks like art."""
        with mock.patch.object(cache_module.requests, "get", return_value=_response(404)):
            Cache.LoadImage(CARD_ID)

        self.assertEqual(self._cache_dir_files(), [f"{CARD_ID}.no_art"],
                         "the placeholder was written as art, which is unrecoverable in practice")
        self.assertIsNone(Cache.FindImageFile(CARD_ID),
                          "the marker must be invisible to the image lookup")

    def test_a_recorded_miss_is_not_asked_about_again(self):
        """That is the point of persisting it: no repeat request every run."""
        with mock.patch.object(cache_module.requests, "get", return_value=_response(404)) as get:
            Cache.LoadImage(CARD_ID)
            self.assertEqual(get.call_count, 1, "precondition: the first call asks")

        Cache.cache.pop(CARD_ID, None)  # a fresh run, same cache folder
        with mock.patch.object(cache_module.requests, "get", return_value=_response(404)) as get:
            Cache.LoadImage(CARD_ID)

        self.assertEqual(get.call_count, 0, "the recorded miss did not suppress the request")
        # Asserted explicitly, because the old code also suppressed the second request: it had
        # written the placeholder as `{card_id}.jpg` and then found that. Suppression alone does not
        # distinguish a marker from poisoned art, so the reason has to be checked too.
        self.assertEqual(self._cache_dir_files(), [f"{CARD_ID}.no_art"],
                         "the request was suppressed by something other than the marker")

    def test_a_500_is_transient_and_is_not_recorded(self):
        """The server having a bad day is not the server telling us the card does not exist."""
        with mock.patch.object(cache_module.requests, "get", return_value=_response(500)):
            Cache.LoadImage(CARD_ID)

        self.assertEqual(self._cache_dir_files(), [],
                         "a 5xx was treated as a definitive miss and recorded")
        self.assertNotIn(CARD_ID, Cache.cache)

    def test_retries_stop_after_the_configured_number_of_attempts(self):
        """Retrying forever would mean a request per render while a network is down."""
        with mock.patch.object(cache_module.IMAGE_DOWNLOAD_ATTEMPTS, "value", 2):
            with mock.patch.object(cache_module.requests, "get",
                                   side_effect=requests.exceptions.ConnectionError()) as get:
                for _ in range(5):
                    Cache.LoadImage(CARD_ID)

        self.assertEqual(get.call_count, 2, "the attempt cap was not honoured")
        self.assertIn(CARD_ID, Cache.cache, "after giving up the placeholder should be cached")
        self.assertEqual(self._cache_dir_files(), [],
                         "giving up within a run must not be recorded on disk")

    def test_enough_failures_in_a_row_stops_asking_for_the_rest_of_the_run(self):
        """Retrying is right for one slow card and wrong for a network that is not there.

        Without this, a disconnected machine pays every attempt times every timeout for every card
        on the New Game screen.
        """
        # Real core ids, none of which exist under assets/pics or assets/textures, so each one has
        # to reach the download path. `9000x` would not: that art ships with the game.
        card_ids = ["01096", "01099", "01100", "01152", "01153", "01154"]
        for card_id in card_ids:
            Cache.cache.pop(card_id, None)
            self.addCleanup(Cache.cache.pop, card_id, None)

        with mock.patch.object(cache_module.IMAGE_DOWNLOAD_FAILURE_LIMIT, "value", 3):
            with mock.patch.object(cache_module.requests, "get",
                                   side_effect=requests.exceptions.ConnectionError()) as get:
                for card_id in card_ids:
                    Cache.LoadImage(card_id)

        self.assertTrue(Cache.downloads_given_up, "the give-up limit never tripped")
        self.assertEqual(get.call_count, 3, "asking continued past the limit")

    def test_a_success_clears_the_failure_count(self):
        """A single blip in the middle of a working session must not count towards giving up."""
        import io

        from PIL import Image

        buffer = io.BytesIO()
        Image.new("RGB", (8, 8), (10, 10, 200)).save(buffer, format="JPEG")

        with mock.patch.object(cache_module.requests, "get",
                               side_effect=[requests.exceptions.ConnectionError(),
                                            _response(200, buffer.getvalue())]):
            Cache.LoadImage(CARD_ID)
            self.assertEqual(Cache.consecutive_fetch_failures, 1, "precondition: one failure")
            Cache.LoadImage(CARD_ID)

        self.assertEqual(Cache.consecutive_fetch_failures, 0,
                         "a success left the failure count standing")

    def test_a_retry_that_succeeds_serves_the_real_art(self):
        """End to end: the point of retrying is that the card recovers without a restart."""
        import io

        from PIL import Image

        buffer = io.BytesIO()
        Image.new("RGB", (16, 16), (200, 30, 30)).save(buffer, format="JPEG")
        art = buffer.getvalue()

        with mock.patch.object(cache_module.requests, "get",
                               side_effect=[requests.exceptions.Timeout(),
                                            _response(200, art)]) as get:
            placeholder = Cache.LoadImage(CARD_ID)
            recovered = Cache.LoadImage(CARD_ID)

        self.assertEqual(get.call_count, 2)
        self.assertNotEqual(placeholder, recovered, "the retry did not replace the placeholder")
        self.assertEqual(Image.open(io.BytesIO(recovered)).size, (16, 16))
        self.assertEqual(self._cache_dir_files(), [f"{CARD_ID}.jpg"],
                         "the recovered art should be the only thing written")
