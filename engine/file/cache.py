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

class Cache:

    cache: Dict[str, bytes] = {}
    link_pic: Dict[str, str] = {}
    known_names: Set[str] = set()

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

        is_time_out = True
        if IMAGE_SERVERS.value and check_is_card_id(card_id):
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

            is_time_out = False

            for site in IMAGE_SERVERS.value:
                full_url = site
                full_url = full_url.replace('{card_id}', card_id)
                full_url = full_url.replace('{card_id:U}', card_id.upper())

                try:
                    Log.DebugInfo(CATEGORY_NAME, f"Downloading from {full_url}")

                    response = requests.get(full_url, headers=headers, timeout=3)
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
                    return image_data
                except requests.exceptions.Timeout:
                    Log.Warn(CATEGORY_NAME, f"Timeout occurred while downloading {file_name}")
                    is_time_out = True
                except requests.exceptions.RequestException as e:
                    Log.Warn(CATEGORY_NAME, f"Request failed with error: {e}")

        # raise Exception(f"Failed to load {file_name} from the internet")
        image_data = ImageCreator.CreateNoImage(card_id)
        if SAVE_EMPTY_IMAGE.value and not is_time_out:
            save_to_file(file_name, "jpg", image_data)
        Cache.SetCache(file_name, image_data)
        return image_data

