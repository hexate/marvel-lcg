import functools
from core import *
from engine.config import ConfigVariables
from engine.lib.sorted_set import SortedSet
from engine.log import Log
from build import Build

COVERAGE_WHITE_LIST = ConfigVariables.ListStr('coverage_white_list', [])

class Coverage:
    is_enable = Build.release == False

    all_register_functions: SortedSet[str] = SortedSet()
    executed_func: Dict[str, int] = {}

    @staticmethod
    def GetKeyName(fn: Callable[..., Any]):
        name = GetFuncLines(fn, True)
        # The path comes from os.path.relpath, so it carries the platform's separator. Comparing
        # against a hardcoded backslash meant this matched nothing at all on macOS and Linux, and
        # card-script coverage silently counted zero rather than reporting an error.
        if name.replace("\\", "/").startswith("cards/pack/"):
            key = name
            return key
        else:
            return ""

    @staticmethod
    def Setup():
        Coverage.executed_func = {}
        Coverage.all_register_functions.clear()

    @staticmethod
    def RegisterFunction(fn: Callable[..., Any]):
        # if not Coverage.is_enable:
        #     return
        key = Coverage.GetKeyName(fn)
        if key:
            # Fix in test
            if key not in Coverage.executed_func:
                Coverage.executed_func[key] = 0
            if key not in COVERAGE_WHITE_LIST.value:
                Coverage.all_register_functions.add(key)

    @staticmethod
    def TrackCallable(fn: Callable[..., Any]):
        # if not Coverage.is_enable:
        #     return
        key = Coverage.GetKeyName(fn)
        if key:
            if key not in Coverage.all_register_functions:
                Coverage.RegisterFunction(fn)
            Coverage.executed_func[key] += 1

    ################################################################################
    #
    @staticmethod
    def track(func: Any):
        """Decorator to track the execution of a callable."""
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if Coverage.is_enable:
                Coverage.TrackCallable(func)
            return func(*args, **kwargs)
        return wrapper

    ################################################################################
    #
    @staticmethod
    def Report(print_rule: Literal["All", "Uncall", "Called"]="Called") -> str:
        if not Coverage.is_enable:
            return ''

        execution_count = 0
        for func_name in Coverage.all_register_functions:
            count = Coverage.executed_func.get(func_name, 0)
            if count:
                text = func_name.ljust(60, "-") + " " + str(count)
                execution_count += 1
            else:
                text = func_name

            if print_rule == "All" or \
                (print_rule == "Called" and count > 0) or \
                (print_rule == "Uncall" and count == 0):
                Log.Print(text)

        total = len(Coverage.all_register_functions)
        text = "Coverage: {}/{} ({:.2f}%)".format(
            execution_count, total,
            execution_count / total * 100)
        Log.Print(text)
        return text


# Example usage
if __name__ == "__main__":
    @Coverage.track
    def example_function() -> None:
        print("Hello, World!")
        for i in range(5):
            print(i)

    @Coverage.track
    def another_function() -> None:
        print("This is another function.")
        print("End of another function.")

    @Coverage.track
    def another_function2() -> int:
        return 1

    example_function()
    another_function()

    x = another_function2()

    # Using the new track_callable method
    def additional_function():
        print("This is an additional function being tracked.")
        for j in range(3):
            print(j)

    Coverage.TrackCallable(additional_function)

    print(Coverage.Report())

