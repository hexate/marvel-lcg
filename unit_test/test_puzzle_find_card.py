"""Whether a puzzle command that names a card finds the one in play, or silently builds another.

`RunPuzzle.FindOrCreateFace` resolves a name against the current player's deck and discard pile,
then the encounter deck and its discard pile, and then falls through to `CreateCard`. The step for
cards already in play was a commented-out line:

    # found_card = self.world.FindCardOnField(name=card)

That could not have been restored as written. `World` has no `FindCardOnField`; the search lives on
`Worlds`, is a staticmethod, and takes an effect as its first argument. Both facts are pinned below,
because "just uncomment it" is the obvious next move for anyone reading that line.

The consequence was not a crash. `CreateCard` generates a *new* card into the aside deck, so a name
that matched something in play produced a duplicate and left the real card alone. `Damage('Rhino')`
damaged a Rhino nobody could see, and `ChangeForm` crashed instead, because a `ClassCard` generated
outside a player has no owner and `Identity.GetInfoDict` asserts on that while rendering.

`game/` cannot be imported on its own because of a circular import, so `import engine` comes first.
"""
import unittest

import engine  # noqa: F401  must precede any game import
from game.operate.worlds import Worlds
from game.puzzle.puzzle import RunPuzzle
from game.world import World


class _Face:
    """A card face that knows its visible name and the name on its other side."""

    def __init__(self, visible, hidden=None):
        self.visible = visible
        self.hidden = hidden

    def IsName(self, name, check_cosider_as=True, check_all_face=False):
        if self.visible == name:
            return True
        return bool(check_all_face and self.hidden == name)


class _EmptyPile:
    def FindCard(self, **kwargs):
        return None


class _Player:
    player_deck = _EmptyPile()
    discard_pile = _EmptyPile()


class _World:
    def GetCurrentPlayer(self):
        return _Player()


class _OnField:
    """Puts `faces` on the field and makes `CreateCard` a failure rather than a silent duplicate."""

    def __init__(self, testcase, faces):
        self.testcase = testcase
        self.faces = faces

    def __enter__(self):
        self.originals = (Worlds.GetEncounterDeckCards,
                          Worlds.GetEncounterDiscardPileCards,
                          Worlds.GetOnFieldCards)
        Worlds.GetEncounterDeckCards = staticmethod(lambda *a, **k: [])
        Worlds.GetEncounterDiscardPileCards = staticmethod(lambda *a, **k: [])
        Worlds.GetOnFieldCards = staticmethod(lambda *a, **k: list(self.faces))

        puzzle = RunPuzzle.__new__(RunPuzzle)  # __init__ needs a real world to build a DebugRule
        puzzle.world = _World()
        puzzle.debug_rule = object()
        puzzle.CreateCard = self._refuse
        return puzzle

    def _refuse(self, card_name):
        self.testcase.fail(
            f"fell through to CreateCard for {card_name!r}, which duplicates it into the aside "
            f"deck and leaves the card in play untouched")

    def __exit__(self, *exc):
        (Worlds.GetEncounterDeckCards,
         Worlds.GetEncounterDiscardPileCards,
         Worlds.GetOnFieldCards) = self.originals


class TestTheCommentedOutLineCouldNotHaveWorked(unittest.TestCase):
    """Pins the premise, so nobody restores the original line and expects it to resolve."""

    def test_world_has_no_find_card_on_field(self):
        self.assertFalse(hasattr(World, "FindCardOnField"),
                         "if this ever exists, the commented-out line becomes the simpler fix")

    def test_the_real_search_is_on_worlds_and_needs_an_effect(self):
        import inspect

        self.assertTrue(hasattr(Worlds, "FindCardOnField"))
        first = list(inspect.signature(Worlds.FindCardOnField).parameters)[0]
        self.assertEqual(first, "by_effect",
                         "the search needs an effect, which is why GetOnFieldCards is used instead")


class TestACardInPlayIsFoundNotDuplicated(unittest.TestCase):

    def test_a_named_card_in_play_is_returned(self):
        """`Damage('Rhino')` was hitting a freshly generated Rhino, so it did nothing visible."""
        rhino = _Face("Rhino")

        with _OnField(self, [rhino]) as puzzle:
            self.assertIs(puzzle.FindOrCreateFace("Rhino"), rhino)

    def test_the_hidden_side_matches_too(self):
        """`ChangeForm('Spider-Man')` is given while the card is still showing Peter Parker."""
        identity = _Face("Peter Parker", hidden="Spider-Man")

        with _OnField(self, [identity]) as puzzle:
            self.assertIs(puzzle.FindOrCreateFace("Spider-Man"), identity)

    def test_a_name_that_is_nowhere_still_falls_through_to_creation(self):
        """The fallback is the point of the method, so it must survive the fix."""
        created = []

        with _OnField(self, []) as puzzle:
            puzzle.CreateCard = lambda name: created.append(name) or "made"

            self.assertEqual(puzzle.FindOrCreateFace("Nothing In This Game"), "made")

        self.assertEqual(created, ["Nothing In This Game"])


if __name__ == "__main__":
    unittest.main()
