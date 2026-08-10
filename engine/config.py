from core import *
from typing import TypeAlias

class ConfigVariable:

    SET_FROM: TypeAlias = Literal["DefaultValue", "CommandLine", "LaunchJson", ""]

    class Base:
        def __init__(self, var_name: 'str') -> None:
            self.name = var_name
            self.value: Any
            self.set_from: ConfigVariable.SET_FROM = ""

        @property
        def is_initialized(self) -> bool:
            return self.set_from != ""

        @property
        def is_from_command_line(self) -> bool:
            return self.set_from == "CommandLine"

        def __repr__(self) -> str:
            return f"{self.name}: {self.value}"

        def SetDefault(self, default: Any|None):
            assert not self.set_from

            if default != None:
                self.value = default
                self.set_from = "DefaultValue"

        def SetValue(self, value: List[str]|str|int|bool, set_from: 'ConfigVariable.SET_FROM'):
            if self.set_from == set_from:
                return

            if self.is_initialized:
                assert self.set_from == "DefaultValue"

            self.SetValueInternal(value)
            self.set_from = set_from

        def SetValueInternal(self, value: List[str]|List[int]|str|int|bool):
            self.value = value

    class Str(Base):
        def __init__(self, var_name: 'str') -> None:
            self.value: str
            super().__init__(var_name)

        # def __str__(self) -> str:
        #     return self.value

        @override
        def SetValueInternal(self, value: List[str]|List[int]|str|int|bool):
            assert not isinstance(value, list), f"{self.name=}"
            if not isinstance(value, str):
                value = str(value)
            return super().SetValueInternal(value)

    class Int(Base):
        def __init__(self, var_name: 'str') -> None:
            self.value: int
            super().__init__(var_name)

        # def __int__(self) -> int:
        #     return self.value

        @override
        def SetValueInternal(self, value: List[str]|List[int]|str|int|bool):
            assert not isinstance(value, list)
            if not isinstance(value, int):
                value = int(value)
            return super().SetValueInternal(value)

    class Bool(Base):
        def __init__(self, var_name: 'str') -> None:
            self.value: bool
            super().__init__(var_name)

        # def __bool__(self) -> bool:
        #     return self.value

        @override
        def SetValueInternal(self, value: List[str]|List[int]|str|int|bool):
            if value != False:
                value = True
            return super().SetValueInternal(value)

    class ListStr(Base):
        def __init__(self, var_name: 'str') -> None:
            self.value: List[str]
            super().__init__(var_name)

        @override
        def SetValueInternal(self, value: List[str]|List[int]|str|int|bool):
            if not isinstance(value, list):
                value = [str(value)]
            return super().SetValueInternal(value)

    class ListInt(Base):
        def __init__(self, var_name: 'str') -> None:
            self.value: List[int]
            super().__init__(var_name)

        @override
        def SetValueInternal(self, value: List[str]|List[int]|str|int|bool):
            if not isinstance(value, list):
                value = [int(value)]
            else:
                value = [int(x) for x in value]
            return super().SetValueInternal(value)

class ConfigVariables:

    ALLOW_TYPE: TypeAlias = ConfigVariable.Str|ConfigVariable.Int|ConfigVariable.Bool|ConfigVariable.ListStr|ConfigVariable.ListInt
    variable_dict: Dict[str, ALLOW_TYPE] = {}
    instance_launch: Dict[str, List[str]|str|int|bool] = {}
    instance_command: Dict[str, List[str]|str|int|bool] = {}
    is_initialized = False

    group: Dict[str, str] = {}

    @staticmethod
    def ParseString(arg_string: str):
        import re
        # Split the string into arguments while handling quoted values
        args = re.findall(r'\"(.*?)\"|(\S+)', arg_string)
        flattened_args = [match[0] if match[0] else match[1] for match in args]
        ConfigVariables.ParseArguments(flattened_args)

    @staticmethod
    def ParseArguments(args: List[str]):
        current_key: str = ""
        result: Dict[str, List[str]] = {}

        for arg in args:
            # Normalize the argument prefix
            if arg.startswith(('/', '-')):
                # Remove the prefix and convert to lowercase
                key = arg[1:].lower()
                current_key = key
                if current_key in ConfigVariables.group:
                    ConfigVariables.ParseString(ConfigVariables.group[current_key])
                else:
                    result[key] = []
            else:
                if current_key:
                    result[current_key].append(arg)

        # Convert single values to their respective types
        for key, value in result.items():
            # `-no_x` addresses the variable `x`, so the prefix has to come off before the lookup
            # below as well as before the store. Leaving it on meant the value was written under
            # the right name and then nothing re-read it, so `-no_x` was accepted and silently
            # ignored for any variable that had already been declared.
            is_negated = len(value) == 0 and key.startswith("no_")
            var_name = key[3:] if is_negated else key

            if len(value) == 0:
                ConfigVariables.instance_command[var_name] = not is_negated
            elif len(value) == 1:
                ConfigVariables.instance_command[var_name] = value[0]
            else:
                ConfigVariables.instance_command[var_name] = value

            if var_name in ConfigVariables.variable_dict:
                ConfigVariables.InitVariable(var_name)

    @staticmethod
    def LoadConfig(file_name: str):
        from engine.lib import Json
        ConfigVariables.instance_launch = Json.Load(file_name)

    @staticmethod
    def InitVariable(var_name: str) -> bool:
        variable: 'ConfigVariable.Base' = ConfigVariables.variable_dict[var_name]
        if var_name in ConfigVariables.instance_command:
            value = ConfigVariables.instance_command[var_name]
            variable.SetValue(value, "CommandLine")
            return True
        if var_name in ConfigVariables.instance_launch:
            value = ConfigVariables.instance_launch[var_name]
            variable.SetValue(value, "LaunchJson")
            return True
        return False

        # if f"no_{var_name}" in ConfigVariables.instance and \
        #     isinstance(variable, ConfigVariables._Bool):
        #     variable.SetValue(False)

    @staticmethod
    def SetupVariables(var_names: List[str]):
        for var_name in var_names:
            ConfigVariables.InitVariable(var_name)

    @staticmethod
    def Initialize() -> None:
        # Example string input
        # example_string = '/a "a_value" /b "b_value still in b value" /c xxx -d -e -f f_value f_value2 -g 1'
        # CommandArguments.ParseString(example_string)
        CONFIG_FILES = ConfigVariables.Files('config_files', ['launch.json'])

        import sys
        # Get command line arguments, excluding the script name
        if len(sys.argv) > 1:
            ConfigVariables.ParseArguments(sys.argv[1:])

        from engine.file import FileManager
        config_file = FileManager.FindJsonPath('Config', *CONFIG_FILES.value)
        if config_file:
            ConfigVariables.LoadConfig(config_file)

        ConfigVariables.SetupVariables([x for x in ConfigVariables.variable_dict])
        ConfigVariables.is_initialized = True

    ################################################################################
    #
    @staticmethod
    def Find(var_name: str) -> 'ConfigVariables.ALLOW_TYPE|None':
        if var_name in ConfigVariables.variable_dict:
            return ConfigVariables.variable_dict[var_name]
        return None

    ################################################################################
    #
    T = TypeVar("T", bound=ConfigVariable.Base)
    @staticmethod
    def New(var_type: Type['T'], var_name: 'str', default: Any|None) -> T:
        var = ConfigVariables.Find(var_name)
        if var != None:
            assert isinstance(var, var_type)
            # assert var.is_initialized # some has no default value
        else:
            var = var_type(var_name)
            assert isinstance(var, ConfigVariable.Str|ConfigVariable.Bool|ConfigVariable.Int|ConfigVariable.ListStr|ConfigVariable.ListInt)
            ConfigVariables.variable_dict[var_name] = var

        if var.set_from == "" or var.set_from == "DefaultValue":
            if ConfigVariables.is_initialized:
                ConfigVariables.InitVariable(var_name)

        if not var.set_from:
            var.SetDefault(default)
        return var

    @staticmethod
    def Str(var_name: 'str', default: str|None=None) -> 'ConfigVariable.Str':
        return ConfigVariables.New(ConfigVariable.Str, var_name, default)

    @staticmethod
    def Folder(var_name: 'str', default: str|None=None) -> 'ConfigVariable.Str':
        assert var_name.endswith('_folder')
        return ConfigVariables.New(ConfigVariable.Str, var_name, default)

    @staticmethod
    def File(var_name: 'str', default: str|None=None) -> 'ConfigVariable.Str':
        assert var_name.endswith('_file')
        return ConfigVariables.New(ConfigVariable.Str, var_name, default)

    @staticmethod
    def Int(var_name: 'str', default: int|None=None) -> 'ConfigVariable.Int':
        return ConfigVariables.New(ConfigVariable.Int, var_name, default)

    @staticmethod
    def Bool(var_name: 'str', default: bool|None=None) -> 'ConfigVariable.Bool':
        return ConfigVariables.New(ConfigVariable.Bool, var_name, default)

    @staticmethod
    def ListStr(var_name: 'str', default: List[str]|None=None) -> 'ConfigVariable.ListStr':
        return ConfigVariables.New(ConfigVariable.ListStr, var_name, default)

    @staticmethod
    def ListInt(var_name: 'str', default: List[str]|None=None) -> 'ConfigVariable.ListInt':
        return ConfigVariables.New(ConfigVariable.ListInt, var_name, default)

    @staticmethod
    def Files(var_name: 'str', default: List[str]|None=None) -> 'ConfigVariable.ListStr':
        assert var_name.endswith('_files')
        return ConfigVariables.New(ConfigVariable.ListStr, var_name, default)

    @staticmethod
    def Folders(var_name: 'str', default: List[str]|None=None) -> 'ConfigVariable.ListStr':
        assert var_name.endswith('_folders')
        return ConfigVariables.New(ConfigVariable.ListStr, var_name, default)

    # Only work for `sys.argv`
    @staticmethod
    def SetGroupArgs(var_name: 'str', arg_string: "str") -> None:
        ConfigVariables.group[var_name] = arg_string

    @staticmethod
    def Test():
        A = ConfigVariables.Int     ("a", 1)
        B = ConfigVariables.Bool    ("b", True)
        C = ConfigVariables.Bool    ("c", True)
        D = ConfigVariables.ListStr ("d", ['a', 'b'])
        E = ConfigVariables.Bool    ("e", True)
        G = ConfigVariables.Int     ("g", 123)
        H = ConfigVariables.Str     ("h", "This is a string")

        I0 = ConfigVariables.Int     ("i")
        I1 = ConfigVariables.Int     ("i", 1)
        I2 = ConfigVariables.Int     ("i")
        # I3 = ConfigVariables.Int     ("i", 2)
        J0 = ConfigVariables.Int     ("j")

        assert I0.value == 1
        assert I1.value == 1
        assert I2.value == 1

        assert J0.is_initialized == False

        ConfigVariables.SetGroupArgs("hello", "-a 2 -b -no_c")

        import sys
        sys.argv.append('-hello')
        sys.argv.append('-d')
        sys.argv.append('good')
        sys.argv.append('nice')
        sys.argv.append('-no_e')
        sys.argv.append('-i')
        sys.argv.append('2')
        sys.argv.append('-j')
        sys.argv.append('3')

        ConfigVariables.Initialize()

        assert I0.value == 2
        assert I1.value == 2
        assert I2.value == 2

        assert A.value == 2
        assert B.value == True
        assert C.value == False
        assert D.value == ['good', 'nice']
        assert E.value == False
        assert G.value == 123
        assert H.value == "This is a string"

        assert J0.value == 3
        J1 = ConfigVariables.Int     ("j", 1)
        assert J0.value == 3
        assert J1.value == 3

