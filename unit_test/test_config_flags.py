"""Command-line flags have to reach variables that were already declared (tracker item J9).

`ParseArguments` handles `-flag` and `-no_flag`. For the negative form it strips the prefix before
storing the value but not before looking the variable up to re-read it, so `-no_x` is silently
ignored for anything declared earlier in the process. Silently is the problem: the flag is accepted,
nothing complains, and the old value stands.

Found while forcing an RNG backend for the F10 work, where it meant a run that reported one backend
and measured the other.
"""
import unittest

import engine  # noqa: F401  must precede any game import
from engine.config import ConfigVariables


class TestNegativeFlags(unittest.TestCase):

    def test_no_prefix_turns_an_already_declared_flag_off(self):
        """The variable exists before the argument is parsed, which is the normal case."""
        flag = ConfigVariables.Bool('j9_probe_on', True)
        self.assertTrue(flag.value, "precondition: starts on")

        ConfigVariables.ParseArguments(['-no_j9_probe_on'])

        self.assertFalse(flag.value, "-no_ was accepted and then ignored")

    def test_positive_form_still_works(self):
        """The half that already worked, pinned so a fix to the other half cannot break it."""
        flag = ConfigVariables.Bool('j9_probe_off', False)
        self.assertFalse(flag.value, "precondition: starts off")

        ConfigVariables.ParseArguments(['-j9_probe_off'])

        self.assertTrue(flag.value)


if __name__ == "__main__":
    unittest.main()
