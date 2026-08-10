from core import *
from engine.lib.mt19937 import Random as R
from engine.config import ConfigVariables

DISABLE_NUMPY_RANDOM = ConfigVariables.Bool('disable_numpy_random', False)

# Capturing generator state on every draw is what `Random.Undo` rewinds, and `Random.Undo` is
# reached from one debug cheat. numpy.random.get_state() copies the 624-word Mersenne buffer each
# time, measured at roughly 34x the cost of a shuffle, and the list was never trimmed. Opt in.
ENABLE_RANDOM_UNDO = ConfigVariables.Bool('enable_random_undo', False)

CATEGORY_NAME = "RANDOM"

class Random:
    seed = 0
    counter = 0
    rand = R()

    states: List[Any] = []

    @staticmethod
    def AddCounter():
        from engine.log import Log
        Random.counter += 1
        Log.DebugSilent(CATEGORY_NAME, f"{Random.counter=}")

    @staticmethod
    def PushState() -> None:
        """Record the generator position so `Undo` can rewind to it.

        Off unless `enable_random_undo` is set. Left on, this copies a 624-word Mersenne buffer on
        every draw and grows `Random.states` for the life of the process.

        Which generator produced the snapshot is stored with it. The two keep their position in
        different shapes, and restoring one into the other would corrupt the generator rather than
        fail, so the tag is what makes the mismatch loud.

        The tag is the `disable_numpy_random` flag itself, deliberately. Undo only has to tell the
        two code paths apart, and naming the generator here would tie a debug affordance to
        whatever the save format happens to call it.
        """
        if not ENABLE_RANDOM_UNDO.value:
            return
        numpy_disabled = DISABLE_NUMPY_RANDOM.value
        if numpy_disabled:
            Random.states.append((numpy_disabled, Random.rand.GetState()))
        else:
            import numpy.random
            Random.states.append((numpy_disabled, numpy.random.get_state()))

    @staticmethod
    def SetSeed(seed: int) -> None:
        from engine.log import Log
        Random.seed = seed
        Random.counter = 0
        # Positions recorded against the old seed cannot be rewound to once it changes, and
        # nothing else trimmed this list.
        Random.states = []
        Log.DebugSilent(CATEGORY_NAME, f"Seed: {seed}")
        if DISABLE_NUMPY_RANDOM.value:
            Random.rand.seed(seed)
        else:
            import numpy.random
            numpy.random.seed(Random.seed)

    @staticmethod
    def RandomSeed() -> int:
        import random
        seed = random.randrange(2**31-2)+1
        Random.SetSeed(seed)
        return seed

    T = TypeVar("T")
    @staticmethod
    def RandomChoice(input_list: Sequence[T]) -> T:
        assert input_list != []
        Random.AddCounter()
        Random.PushState()
        if DISABLE_NUMPY_RANDOM.value:
            return Random.rand.choice_one(input_list)
        else:
            import numpy.random
            return numpy.random.choice(input_list) # type: ignore

    @staticmethod
    def RandomChoice2(input_list: Sequence[T], x: int) -> List[T]:
        if x < 0:
            raise ValueError("x cannot be negative.")
        if x > len(input_list):
            raise ValueError("x cannot be greater than the length of the input list.")
        if x == 1:
            return [Random.RandomChoice(input_list)]
        if len(input_list) == x:
            return list(input_list)

        Random.AddCounter()
        Random.PushState()
        if DISABLE_NUMPY_RANDOM.value:
            return Random.rand.choice(list(input_list), size=x, replace=False)
        else:
            import numpy.random
            return list(numpy.random.choice(input_list, size=x, replace=False)) # type: ignore

    @staticmethod
    def Shuffle(list: List[Any]) -> None:
        Random.AddCounter()
        Random.PushState()
        if DISABLE_NUMPY_RANDOM.value:
            Random.rand.shuffle(list)
        else:
            import numpy.random
            numpy.random.shuffle(list) # type: ignore

    @staticmethod
    def Undo():
        """Rewind to the position recorded before the most recent draw.

        Both backends support this. The bundled one used to fall through a bare `pass`, so the
        `Unshuffle` cheat at `cheat_cmd_helper.py:390` quietly did nothing instead of rewinding.
        """
        assert ENABLE_RANDOM_UNDO.value, (
            "Random.Undo needs 'enable_random_undo' in the config. State capture is off by "
            "default because it copies the generator buffer on every draw."
        )
        assert Random.states, "No recorded generator position to undo."

        recorded_numpy_disabled, state = Random.states.pop()
        assert recorded_numpy_disabled == DISABLE_NUMPY_RANDOM.value, (
            f"Recorded generator position belongs to the "
            f"{'bundled' if recorded_numpy_disabled else 'numpy'} generator but this build is "
            f"running the {'bundled' if DISABLE_NUMPY_RANDOM.value else 'numpy'} one. Restoring "
            f"it would corrupt the generator rather than rewind it."
        )

        if DISABLE_NUMPY_RANDOM.value:
            Random.rand.SetState(state)
        else:
            import numpy.random
            numpy.random.set_state(state)

