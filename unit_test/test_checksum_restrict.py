"""Loading a file with a bad checksum (tracker item J3).

`Json` offers three modes: "Ignore", "Warn" and "Restrict". Only two of them existed in practice.
A mismatch called `Notify.Error` and then returned the object anyway, so "Restrict" and "Warn" did
the same thing and nothing ever refused to load a file.

`game/statistics/game_statistics.py:66` asks for "Restrict" and wraps the call in `try/except` that
sets `file_broken`, and `Save` then refuses to overwrite a broken file. The handling was written
for a refusal that never came.

Scenes and puzzles deliberately keep asking for "Warn": refusing to open a save whose checksum has
drifted is a decision about players' existing files, not a bug fix. See J3 in the tracker.

`game/` cannot be imported on its own because of a circular import, so `import engine` comes first.
"""
import json
import pathlib
import unittest

import engine  # noqa: F401  must precede any game import
from engine.lib import Json
from engine.lib.json import ChecksumError

OUT_DIR = pathlib.Path("out/checksum_tests")


class TestChecksumModes(unittest.TestCase):

    def setUp(self):
        # Saving and loading both stamp and read the version, and `Engine.Initialize` is what
        # normally sets it. These tests do not start an engine.
        from engine.lib import Ver
        Ver.Initialize()

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        self.path = OUT_DIR / f"{self._testMethodName}.json"
        Json.Save({"hero": "spider_man", "seed": 42}, str(self.path), ignore_check_sum=False)

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def _tamper(self):
        """Edit the contents without touching the recorded checksum, as corruption would."""
        data = json.loads(self.path.read_text())
        data["seed"] = 9999
        self.path.write_text(json.dumps(data))

    def test_an_intact_file_loads_in_every_mode(self):
        for mode in ("Ignore", "Warn", "Restrict"):
            loaded = Json.Load(str(self.path), check_sum=mode)
            self.assertEqual(loaded["seed"], 42, f"mode {mode} did not load an intact file")

    def test_ignore_loads_a_tampered_file(self):
        self._tamper()
        self.assertEqual(Json.Load(str(self.path), check_sum="Ignore")["seed"], 9999)

    def test_warn_still_loads_a_tampered_file(self):
        """Unchanged on purpose. Scene loading uses this and players have existing files."""
        self._tamper()
        self.assertEqual(Json.Load(str(self.path), check_sum="Warn")["seed"], 9999)

    def test_restrict_refuses_a_tampered_file(self):
        self._tamper()
        with self.assertRaises(ChecksumError) as caught:
            Json.Load(str(self.path), check_sum="Restrict")
        self.assertIn(str(self.path), str(caught.exception))

    def test_restrict_still_loads_a_file_that_has_no_checksum(self):
        """A file with nothing recorded is old, not damaged, and must keep opening.

        Refusing these would reject anything written before checksums existed, or written with the
        default `ignore_check_sum=True`, which is most of what is on disk.
        """
        no_checksum = OUT_DIR / "no_checksum.json"
        Json.Save({"hero": "spider_man", "seed": 42}, str(no_checksum))
        try:
            self.assertEqual(Json.Load(str(no_checksum), check_sum="Restrict")["seed"], 42)
        finally:
            no_checksum.unlink(missing_ok=True)

    def test_restrict_refuses_a_tampered_file_through_load_as(self):
        """The statistics loader goes through LoadAs, so both doors have to be shut."""
        from dataclasses import dataclass

        @dataclass
        class _Shape:
            hero: str = ""
            seed: int = 0

        self._tamper()
        with self.assertRaises(ChecksumError):
            Json.LoadAs(str(self.path), _Shape, check_sum="Restrict")


if __name__ == "__main__":
    unittest.main()
