"""Tests for the generated card placeholder (J16).

`ImageCreatorHelper.DrawText` had its line-accumulation loop commented out when Pillow 10 removed
`draw.textsize`, so it returned without drawing for every caller. Nothing failed and nothing logged:
`show_image_text` stayed on by default in `launch.json` and quietly produced a blank colour swatch
instead of a card showing its name and text. That is the fallback the game relies on whenever art is
missing, so a card the player could not identify looked exactly like a card with no art.

`import engine` precedes any game import to establish the circular-import order, as in the other
modules here.
"""
import unittest

import engine  # noqa: F401  must precede any game import
from PIL import Image, ImageDraw

from engine.lib.image_creator import ImageCreatorHelper


WHITE = (255, 255, 255)


def _blank(width: int = 254, height: int = 352) -> Image.Image:
    return Image.new("RGB", (width, height), WHITE)


def _dark_pixels(image: Image.Image) -> int:
    """Pixels dark enough to be drawn glyphs rather than background."""
    return sum(count for count, color in (image.getcolors(maxcolors=200000) or [])
               if sum(color) < 200)


class TestDrawText(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        ImageCreatorHelper.Initialize()

    def test_draw_text_marks_the_image(self):
        """Drawing text has to change pixels. It silently changed none."""
        image = _blank()
        draw = ImageDraw.Draw(image)

        ImageCreatorHelper.DrawText(draw, "Concussion Blasters", (10, 4),
                                    ImageCreatorHelper.font, image.width)

        self.assertGreater(_dark_pixels(image), 0,
                           "DrawText left the image untouched, so the placeholder carries no text")

    def test_long_text_wraps_within_max_width(self):
        """Card text is a paragraph, so it has to wrap rather than run off the right edge."""
        image = _blank()
        draw = ImageDraw.Draw(image)
        max_width = 120
        text = ("Attach to the villain. The villain gains retaliate 1. Hero Action: Exhaust your "
                "hero and spend energy energy resources to discard this card.")

        ImageCreatorHelper.DrawText(draw, text, (0, 0), ImageCreatorHelper.font, max_width)

        columns = [x for x in range(image.width) for y in range(image.height)
                   if sum(image.getpixel((x, y))) < 200]
        self.assertTrue(columns, "nothing was drawn")
        # One word may overhang, since a word wider than max_width still gets its own line.
        self.assertLess(max(columns), max_width + ImageCreatorHelper.font_size * 4,
                        "text ran past max_width instead of wrapping")

    def test_newlines_in_source_text_are_kept(self):
        """Card text carries its own line breaks; splitting on all whitespace lost them."""
        image_one_line = _blank()
        image_two_lines = _blank()

        ImageCreatorHelper.DrawText(ImageDraw.Draw(image_one_line), "alpha beta", (0, 0),
                                    ImageCreatorHelper.font, 254)
        ImageCreatorHelper.DrawText(ImageDraw.Draw(image_two_lines), "alpha\nbeta", (0, 0),
                                    ImageCreatorHelper.font, 254)

        def lowest_drawn_row(image: Image.Image) -> int:
            # -1 for an untouched image, so a no-op DrawText fails the comparison below with a
            # readable message rather than raising ValueError out of max().
            rows = [y for y in range(image.height) for x in range(image.width)
                    if sum(image.getpixel((x, y))) < 200]
            return max(rows) if rows else -1

        self.assertGreater(lowest_drawn_row(image_two_lines), lowest_drawn_row(image_one_line),
                           "the newline did not start a second line")


class TestCreateNoImage(unittest.TestCase):
    """The placeholder a card falls back to when its art is missing."""

    @classmethod
    def setUpClass(cls) -> None:
        from unit_test.harness import EnsureEngine
        EnsureEngine()

    def test_placeholder_identifies_the_card(self):
        """Two different cards must not produce the same placeholder.

        This is the symptom that made J15 undiagnosable from the table: `01152` and `01153` both
        attach to the villain and only one of them grants retaliate, and both rendered as the same
        blank swatch, so the player could not tell which was in play.
        """
        import hashlib
        import io

        from engine.lib.image_creator import ImageCreator

        self.assertTrue(ImageCreator.show_image_text,
                        "launch.json ships show_image_text on; the rest of this test assumes it")

        blasters = ImageCreator.CreateNoImage("01153")
        armor = ImageCreator.CreateNoImage("01152")

        # Compared by digest so a failure prints two hashes rather than two JPEGs.
        self.assertNotEqual(hashlib.sha256(blasters).hexdigest(),
                            hashlib.sha256(armor).hexdigest(),
                            "different cards produced byte-identical placeholders")
        for card_id, data in (("01153", blasters), ("01152", armor)):
            image = Image.open(io.BytesIO(data)).convert("RGB")
            with self.subTest(card_id=card_id):
                self.assertGreater(_dark_pixels(image), 0,
                                   f"{card_id} rendered as a blank swatch with no text")
