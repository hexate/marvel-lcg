from core import *
import requests
from engine.lib import ImageCreator, ImageLib
from engine.log import Log
from engine.file import FileManager
from engine.config import ConfigVariables

CATEGORY_NAME = "CACHE"

IMAGE_FOLDERS   = ConfigVariables.Folders('image_folders', ["./assets/pics/"])
TEXTURE_FOLDER  = ConfigVariables.Folder('texture_folder', "./assets/textures/")
CACHE_FOLDER    = ConfigVariables.Folder('cache_folder', "./assets/cache/")
IMAGE_SERVERS   = ConfigVariables.ListStr('image_servers', [])
SAVE_EMPTY_IMAGE = ConfigVariables.Bool('save_empty_image', True)
BREAK_WHEN_LOAD_ONLINE_IMAGE = ConfigVariables.Bool('break_when_load_online_image', False)
# 3 seconds was the original, against card art that measures around 370 KB a file: a slow moment
# was enough to lose one permanently, which is the J15 failure.
IMAGE_DOWNLOAD_TIMEOUT = ConfigVariables.Int('image_download_timeout', 10)
# How many times a transient fetch failure may be retried within one run before the card settles
# for a placeholder. Per name, not global.
IMAGE_DOWNLOAD_ATTEMPTS = ConfigVariables.Int('image_download_attempts', 3)
# Consecutive transient failures across all names before this run stops asking at all. Retrying is
# right for one card losing a race with a slow network and wrong for a network that is not there:
# without a limit, a disconnected machine pays every attempt times every timeout times every card
# before the New Game screen finishes drawing. Any success resets the count.
IMAGE_DOWNLOAD_FAILURE_LIMIT = ConfigVariables.Int('image_download_failure_limit', 10)

NO_ART_MARKER_EXT = "no_art"

class Cache:

    cache: Dict[str, bytes] = {}
    link_pic: Dict[str, str] = {}
    known_names: Set[str] = set()
    # The image route runs each request on a worker thread, so these are touched from several at
    # once. A lost increment costs at most one extra retry, never a wrong image, which is why they
    # are left unlocked like `cache` itself already is.
    fetch_attempts: Dict[str, int] = {}
    consecutive_fetch_failures: int = 0
    downloads_given_up: bool = False

    @staticmethod
    def SetLinkPic(card_id: str, link_to_pic_id: str):
        Cache.link_pic[card_id] = link_to_pic_id

    @staticmethod
    def RegisterImageName(card_id: str):
        """Declare a name the game may ask for, whether or not we hold art for it.

        `LoadImage` answers every name with a placeholder, so on its own it cannot tell a card we
        have no art for from a path that means nothing. The game layer registers the names it knows
        about, the same way it already hands over `SetLinkPic`, and `CanLoadImage` uses that to keep
        the first case working while the second becomes a 404.
        """
        Cache.known_names.add(card_id)

    @staticmethod
    def FindImageFile(name: str) -> str|None:
        """The path this name would load from, or None if nothing on disk matches.

        Mirrors the folders and extensions `LoadImage` searches, in the same order. Kept separate
        rather than shared because `LoadImage` also decodes, and this only needs to know whether a
        candidate exists. Change one and change the other.
        """
        for cache_folder in IMAGE_FOLDERS.value + [TEXTURE_FOLDER.value] + [CACHE_FOLDER.value]:
            for ext_name in [".webp", ".jpg", ".png"]:
                check_path = f"{cache_folder}/{name}{ext_name}"
                if FileManager.Exists(check_path):
                    return check_path
        return None

    @staticmethod
    def NoArtMarkerPath(name: str) -> str:
        return FileManager.JoinPath(CACHE_FOLDER.value, f"{name}.{NO_ART_MARKER_EXT}")

    @staticmethod
    def HasNoArtMarker(name: str) -> bool:
        return FileManager.Exists(Cache.NoArtMarkerPath(name))

    @staticmethod
    def WriteNoArtMarker(name: str, reason: str) -> None:
        """Record that every configured image server was asked for this name and none had the art.

        This replaces writing the generated placeholder to `{name}.jpg`, which is what the older
        code did and what poisoned `assets/cache/90001.jpg`. A fake JPEG under the card's own name
        cannot be told from real art by anything downstream, not `LoadImage`, not `FindImageFile`,
        not `CanLoadImage`, so the card stayed grey in every later run and the only cure was
        knowing to go and delete the file. A marker is skipped by all three, because they only look
        for `.webp`, `.jpg` and `.png`, and it says why it exists when someone finds it.
        """
        file_path = Cache.NoArtMarkerPath(name)
        FileManager.MakeDir(FileManager.GetDirName(file_path))
        with FileManager.OpenFile(file_path, write=True, bin=True) as file:
            file.Write(f"No art for {name}: {reason}\n"
                       f"Delete this file to make the game ask for it again.\n".encode())

    @staticmethod
    def IsCardId(s: str) -> bool:
        # Pattern to match: five digits followed by an optional lowercase letter
        import re
        return re.match(r'^\d{5}[a-z]?$', s) is not None

    @staticmethod
    def CanLoadImage(card_id: str) -> bool:
        """Is this a name we could serve an image for, or is it just an unknown path?

        Callers that route by path need this because `LoadImage` never fails: it returns a
        placeholder for anything, which turns a missing route into a 200 and a grey card.
        """
        card_id = card_id.lstrip("/")
        if not card_id:
            return False
        return (card_id in Cache.cache
                or card_id in Cache.known_names
                or card_id in Cache.link_pic
                or Cache.IsCardId(card_id)
                or Cache.FindImageFile(card_id) is not None)

    @staticmethod
    def SetCache(card_id: str, data: bytes):
        Cache.cache[card_id] = data

    @staticmethod
    def LoadImage(card_id: str) -> bytes:
        # if url in ['enthralled_minion', 'minion', 'ultron_facedown_drone']:
        #     url = 'player'
        card_id = card_id.lstrip("/")

        if card_id in Cache.cache:
            return Cache.cache[card_id]

        assert card_id != "", f"{card_id=}"
        file_name = card_id

        check_folders = IMAGE_FOLDERS.value + [TEXTURE_FOLDER.value] + [CACHE_FOLDER.value]

        def try_load_image_data(image_data: bytes):
            return ImageLib.TryRotateImage(image_data)

        # Load the image from the cache and images
        def try_load_image_path(file_path: str) -> bytes|None:
            for ext_name in [".webp", ".jpg", ".png"]:
                check_path = file_path + ext_name
                if FileManager.Exists(check_path):
                    with FileManager.OpenFile(check_path, read=True, bin=True) as file:
                        return try_load_image_data(file.Read())
            return None

        def try_load_image_name(name: str) -> bytes|None:
            for cache_folder in check_folders:
                file_paths: List[str] = []
                file_paths.append(f"{cache_folder}/{name}")
                for file_path in file_paths:
                    image_data = try_load_image_path(file_path)
                    if image_data:
                        return image_data
            return None

        image_data = try_load_image_name(file_name)
        if image_data:
            Cache.SetCache(file_name, image_data)
            return image_data

        if file_name in Cache.link_pic:
            image_data = Cache.LoadImage(Cache.link_pic[file_name])
            if image_data:
                return image_data

        def check_is_card_id(s: str):
            import re
            # Pattern to match: four digits followed by a lowercase letter
            pattern = r'^\d{5}[a-z]?$'
            return re.match(pattern, s)

        def save_to_file(file_name: str, ext_name: str, data: bytes):
            file_path = FileManager.JoinPath(CACHE_FOLDER.value, f"{file_name}.{ext_name}")
            FileManager.MakeDir(FileManager.GetDirName(file_path))
            with FileManager.OpenFile(file_path, write=True, bin=True) as file:
                file.Write(data)

        # What may be remembered about a failure depends on which kind it was. A definitive answer,
        # every configured server asked and none holding the art, is worth keeping so the next run
        # does not ask again. A timeout or a dropped connection is not: J15 was one 3-second timeout
        # blanking a card for the eleven remaining hours of a session, because the placeholder went
        # into `Cache.cache` under the card's own name and nothing ever looked again.
        attempted = False
        transient = False

        if IMAGE_SERVERS.value and check_is_card_id(card_id) \
        and not Cache.downloads_given_up and not Cache.HasNoArtMarker(file_name):
            attempted = True
            # Load the image from the internet
            skip_break = not BREAK_WHEN_LOAD_ONLINE_IMAGE.value
            if not skip_break:
                Debug.DebugBreak()

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
            }

            # "https://cerebrodatastorage.blob.core.windows.net/cerebro-cards/official/${card_id}.jpg",
            # "https://marvelcdb.com/bundles/cards/${card_id}.jpg",
            # "https://marvelcdb.com/bundles/cards/${card_id}.png",

            for site in IMAGE_SERVERS.value:
                full_url = site
                full_url = full_url.replace('{card_id}', card_id)
                full_url = full_url.replace('{card_id:U}', card_id.upper())

                try:
                    Log.DebugInfo(CATEGORY_NAME, f"Downloading from {full_url}")

                    response = requests.get(full_url, headers=headers,
                                            timeout=IMAGE_DOWNLOAD_TIMEOUT.value)
                    response.raise_for_status()

                    content_type = response.headers.get('Content-Type')

                    ext_name = "bmp"
                    if content_type:
                        # Determine the image format based on the Content-Type
                        if 'image/jpeg' in content_type:
                            ext_name = "jpg"
                        elif 'image/png' in content_type:
                            ext_name = "png"
                        elif 'image/webp' in content_type:
                            ext_name = "webp"

                    # Check if the response is successful
                    Log.DebugInfo(CATEGORY_NAME, f"Downloaded: {file_name}")
                    data = response.content
                    # Save the image to the cache
                    save_to_file(file_name, ext_name, data)
                    # Get the image data from the response
                    image_data = try_load_image_data(data)
                    Cache.SetCache(file_name, image_data)
                    Cache.consecutive_fetch_failures = 0
                    return image_data
                except requests.exceptions.Timeout:
                    Log.Warn(CATEGORY_NAME, f"Timeout occurred while downloading {file_name}")
                    transient = True
                except requests.exceptions.HTTPError as e:
                    # A status is an answer. 5xx, 408 and 429 mean ask again later; anything else is
                    # the server saying it does not have this card, which is worth remembering.
                    status = e.response.status_code if e.response is not None else None
                    if status is None or status >= 500 or status in (408, 429):
                        transient = True
                    Log.Warn(CATEGORY_NAME, f"{file_name}: HTTP {status} from {full_url}")
                except requests.exceptions.RequestException as e:
                    # No status, so no answer: DNS, refused, reset, TLS. Retryable.
                    Log.Warn(CATEGORY_NAME, f"Request failed with error: {e}")
                    transient = True

        # raise Exception(f"Failed to load {file_name} from the internet")
        image_data = ImageCreator.CreateNoImage(card_id)

        if transient:
            Cache.consecutive_fetch_failures += 1
            if Cache.consecutive_fetch_failures >= IMAGE_DOWNLOAD_FAILURE_LIMIT.value:
                Cache.downloads_given_up = True
                Log.Warn(CATEGORY_NAME,
                         f"{Cache.consecutive_fetch_failures} image downloads failed in a row, "
                         f"not asking again this run. Cards with no local art will show a "
                         f"placeholder. Restart once the network is back")

            attempts = Cache.fetch_attempts.get(file_name, 0) + 1
            Cache.fetch_attempts[file_name] = attempts
            if attempts < IMAGE_DOWNLOAD_ATTEMPTS.value and not Cache.downloads_given_up:
                # Deliberately not cached and not persisted, so the next request tries again. This
                # is the whole of J15: a card must not be lost to one bad moment on the network.
                Log.Warn(CATEGORY_NAME,
                         f"No art for {file_name} yet, attempt {attempts} failed, will retry")
                return image_data
            Log.Warn(CATEGORY_NAME,
                     f"Giving up on {file_name} after {attempts} failed attempts, showing a "
                     f"placeholder for the rest of this run")
        elif attempted and SAVE_EMPTY_IMAGE.value:
            Cache.WriteNoArtMarker(file_name, "every configured image server was asked and none "
                                              "had it")
        else:
            # Nothing was asked, either because there is no image server configured or because the
            # name is not card-id-shaped, so a placeholder is the correct and final answer. Cards we
            # ship no art for live here, `2425_boss_rush` among them, and warning about each one
            # would bury the cases above.
            Log.DebugInfo(CATEGORY_NAME, f"No art for {file_name}, showing a placeholder")

        Cache.SetCache(file_name, image_data)
        return image_data

