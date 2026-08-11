import gzip
import json
from core import *
from engine.lib import Ver
from build import Build

CATEGORY_NAME = "JSON"

class ChecksumError(Exception):
    """A file's contents do not match the checksum recorded inside it.

    Raised only for `check_sum="Restrict"`, and only for a real mismatch. A file with no checksum
    at all, or one written before checksums existed, has nothing to contradict and is not an error.
    """

class Json:

    CHECKSUM_RESULT = Literal["Ok", "Mismatch", "Version Error", "Not Found"]
    CHECKSUM_TYPE = Literal["Ignore", "Warn", "Restrict"]

    CHECK_SUM_KEY = 'checksum'
    VERSION_KEY = 'version'

    ################################################################################
    #
    @staticmethod
    def Dumps(items: Any, *, indent:int|None=None, sort_keys:bool=False) -> str:
        return json.dumps(items, default=lambda o:o.__dict__, indent=indent, sort_keys=sort_keys)

    @staticmethod
    def DumpGZip(items: Any) -> bytes:
        return gzip.compress(Json.Dumps(items).encode('utf-8'))

    @staticmethod
    def DumpsSize(items: Any) -> int:
        return len(Json.Dumps(items).encode('utf-8'))

    T = TypeVar("T")
    @staticmethod
    def ConvertDictToDataclass(data: Dict[Any, Any], cls: Type[T]) -> T:
        try:
            if not is_dataclass(cls):
                return data  # type: ignore
            
            filtered_data = {}
            for f in fields(cls):
                if f.name in data:
                    field_value = data[f.name]
                    field_type = f.type
                    
                    # Check if the field type is a Union (e.g., str | int)
                    if hasattr(field_type, '__origin__') and field_type.__origin__ is Union:
                        # Extract the types from the Union
                        types = field_type.__args__
                        if any(is_dataclass(t) for t in types): # type: ignore
                            # Handle dataclass types within Union
                            filtered_data[f.name] = Json.ConvertDictToDataclass(field_value, next(t for t in types if is_dataclass(t)))
                        else:
                            # Handle primitive types (e.g., str, int)
                            filtered_data[f.name] = field_value
                    elif is_dataclass(field_type):
                        filtered_data[f.name] = Json.ConvertDictToDataclass(field_value, field_type)
                    elif isinstance(field_value, list):
                        filtered_data[f.name] = [Json.ConvertDictToDataclass(item, field_type.__args__[0]) for item in field_value]  # type: ignore
                    elif isinstance(field_value, dict):
                        # Directly assign the dictionary values since they are str or int
                        filtered_data[f.name] = {
                            k: v for k, v in field_value.items() # type: ignore
                        }
                    else:
                        filtered_data[f.name] = field_value
            
            return cls(**filtered_data)
        except Exception as e:
            # from engine.lib import Log
            # Log.Assert(CATEGORY_NAME, f"{cls=}")
            raise e

    @staticmethod
    def LoadsAs(string: str, class_name: Type[T]) -> T:
        data = json.loads(string)
        return Json.ConvertDictToDataclass(data, class_name)

    @staticmethod
    def Loads(string: str) -> Dict[Any, Any]:
        import re

        def remove_comments(code: str) -> str:
            # Pattern to match // comments not inside strings
            pattern = re.compile(r'(".*?"|//.*?$)', re.MULTILINE)

            def replacer(match: re.Match[str]) -> str:
                # If the match is a string (starts and ends with a double quote), return it as is
                if match.group(1).startswith('"') and match.group(1).endswith('"'):
                    return match.group(1)
                # If the match is a comment, return an empty string to remove it
                return ''
            return pattern.sub(replacer, code)

        def remove_commas(json_str: str) -> str:
            # Remove trailing commas before closing braces or brackets
            json_str = re.sub(r',\s*([\]}])', r'\1', json_str)  # Trailing comma before } or ]

            # Remove trailing commas after the last item in an array or object
            json_str = re.sub(r'([$${])\s*([^,$$}]+)\s*,\s*([\]}])', r'\1\2\3', json_str)
            return json_str

        string = remove_comments(string)
        string = remove_commas(string)
        return json.loads(string)

    @staticmethod
    def SaveString(obj: Any, *, ignore_check_sum: bool=True) -> str:
        if hasattr(obj, Json.VERSION_KEY):
            setattr(obj, Json.VERSION_KEY, str(Ver.version))

        class DictWrapper:
            def __init__(self, dictionary: Dict[str, str]):
                self.__dict__ = dictionary

        def is_dict(obj: Any) -> TypeGuard[Dict[Any, Any]]:
            return isinstance(obj, dict)

        if is_dict(obj):
            obj = DictWrapper(obj)

        if not ignore_check_sum:
            if hasattr(obj, Json.CHECK_SUM_KEY):
                delattr(obj, Json.CHECK_SUM_KEY)
            setattr(obj, Json.CHECK_SUM_KEY, Types.DictChecksum(obj)) # This must be at the last

        return Json.Dumps(obj, indent=4)

    @staticmethod
    def Save(obj: Any, filename: str, *, ignore_check_sum: bool=True) -> None:
        from engine.file import FileManager
        data = Json.SaveString(obj, ignore_check_sum=ignore_check_sum)
        # Save the object to a file
        with FileManager.OpenFile(filename, write=True) as file:
            file.Write(data)

    @staticmethod
    def LoadInternal(filename: str) -> Tuple[Dict[Any, Any], CHECKSUM_RESULT]:
        from engine.file import FileManager
        with FileManager.OpenFile(filename, read=True) as file:
            json_data = file.Read()

        obj = Json.Loads(json_data)

        # Extract the checksum
        if isinstance(obj, list):
            return obj, "Not Found"
        else:
            original_checksum = obj.get(Json.CHECK_SUM_KEY)
            version = obj.get(Json.VERSION_KEY, str(Ver.version))
        if original_checksum is not None:
            del obj[Json.CHECK_SUM_KEY]

        if Ver(version).IsChecksum():
            from engine.log import Log
            recalculated_checksum = Types.DictChecksum(obj)

            if original_checksum is None:
                checksum = "Not Found"
                # if not Build.release:
                #     text = f"{Json.CHECK_SUM_KEY} key not found in file {filename}\n{recalculated_checksum}"
                #     Log.Warn(CATEGORY_NAME, text)
            elif original_checksum != recalculated_checksum:
                checksum = "Mismatch"
                if not Build.release:
                    text = f"Checksum mismatch in file {filename}\n{recalculated_checksum}"
                    Log.Warn(CATEGORY_NAME, text)
                else:
                    text = f"Checksum mismatch in file {filename}"
                    Log.Warn(CATEGORY_NAME, text)
            else:
                checksum = "Ok"
                # if not Build.release:
                #     Log.Info(CATEGORY_NAME, f"Checksum matches in file {filename}")
        else:
            checksum = "Version Error"

        return obj, checksum

    @staticmethod
    def CheckLoadedChecksum(filename: str, checksum: 'Json.CHECKSUM_RESULT',
                            check_sum: 'Json.CHECKSUM_TYPE') -> None:
        """Act on a checksum result, according to what the caller asked for.

        "Restrict" used to behave exactly like "Warn": both notified and then handed the object
        back, so nothing ever refused to load a file. It now refuses a genuine mismatch.

        Only a mismatch. "Not Found" and "Version Error" mean the file carries no checksum to
        contradict, which is true of anything written before checksums existed, and refusing those
        would reject files that are merely old rather than damaged.
        """
        if check_sum == "Ignore" or checksum == "Ok":
            return

        if checksum == "Mismatch" and check_sum == "Restrict":
            raise ChecksumError(
                f"Checksum mismatch in file {filename}. Its contents do not match the checksum "
                f"stored inside it, so it is corrupted or was edited after saving."
            )

        from engine.log import Notify
        Notify.Error(f"Checksum error in file {filename}")

    @staticmethod
    def Load(filename: str, *, check_sum: CHECKSUM_TYPE="Ignore") -> Dict[str, Any]:
        obj, checksum = Json.LoadInternal(filename)
        Json.CheckLoadedChecksum(filename, checksum, check_sum)
        return obj

    @staticmethod
    def LoadAsList(data_string: str) -> List[Any]:
        obj = Json.Loads(data_string)
        assert isinstance(obj, list)
        return obj

    @staticmethod
    def LoadAs(filename: str, class_name: Type[T], *, check_sum: CHECKSUM_TYPE="Ignore") -> T:
        obj, checksum = Json.LoadAsInternal(filename, class_name, check_sum=check_sum)
        Json.CheckLoadedChecksum(filename, checksum, check_sum)
        return obj

    @staticmethod
    def LoadAsInternal(filename: str, class_name: Type[T], *, check_sum: CHECKSUM_TYPE="Ignore") -> Tuple[T, CHECKSUM_RESULT]:
        obj, checksum = Json.LoadInternal(filename)
        return Json.ConvertDictToDataclass(obj, class_name), checksum

