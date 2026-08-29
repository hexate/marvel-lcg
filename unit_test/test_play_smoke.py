"""Play whole games and assert they finish properly.

`test_all` replays recorded games, and those replays are player data that is gitignored,
so on a fresh clone it has nothing to replay. This covers the same ground from the other
direction: it builds games from a scenario name and a deck name, plays them with a
policy, and checks each one reaches a real ending. It needs no replays, no assets and no
corpus, so it runs anywhere the repository does.

It is not testing whether the policy plays well. It is testing that a game can be played
at all: that every prompt the engine raises can be answered, that answering them makes
progress, and that the game ends for one of the reasons the rules define.

This finds a class of defect that reading cannot. Everything below was found by playing
games rather than by inspection, and every one of them looked like "the bot is bad"
rather than like a crash:

* An Attack or Thwart can list legal targets while asking for none of them
  (`target_num_range` of [0, 0]). Supplying one is rejected and the same prompt comes
  back forever.
* A forced prompt accepts id 0 only when a single option needs no targets. On a
  two-option forced choice, declining loops.
* A cost is not always a number: a typed cost arrives as its resource letters, 'RRR'.
* A card with two abilities numbers them, `Hero_Action` and `Hero_Action_1`.
* `GameOverReason.players_won` is only a type annotation until a game ends in a win or a
  loss, so a game that ended some other way raises on the attribute rather than
  reporting it.

The stall assertion is the important one. A prompt that repeats with no state change is
the engine telling you it cannot use the answer, and that is what all of the above look
like from the outside. It is not theoretical: three of these six matchups stalled on
`Hero_Action` the first time this ran, and the "reaches a real ending" assertion caught
those same games ending without a rules outcome.

What it does not do, checked rather than assumed. It cannot detect a single refused
answer. The engine does not re-prompt on input it cannot use: answering with an invented
effect id was measured as producing no repeat at all, the game simply moves on. So a
defect is only visible here once it is bad enough to stop progress, and the specific
historical bugs above were found by playing much longer games with a real policy in
`tools/sim`, not by this. This is a floor, not a net.

It also only covers what the six matchups touch. They use starter decks, because
`deck/custom` is gitignored and a test that needs player data is the problem this exists
to avoid.
"""
import json
import unittest

import engine  # noqa: F401  must precede any game import


# scenario, deck. Chosen for coverage rather than for difficulty: a single-stage main
# scheme, a two-stage one, a minion-heavy deck, and a multi-form hero, whose option names
# differ from every other hero's and so exercise a separate path.
MATCHUPS = [
    ("rhino", "spider_man"),
    ("rhino", "captain_america"),
    ("klaw", "doctor_strange"),
    ("taskmaster", "ant_man"),
    ("mysterio", "captain_marvel"),
    ("crossbones", "thor"),
]

MAX_STEPS = 4000
STALL_LIMIT = 40


class Exerciser:
    """Answers every prompt, takes real actions, and records anything that looks stuck.

    Deliberately not a good player. It needs to reach deep into a game so that card
    scripts actually run, which a decline-everything policy does not: that ends most
    games in two or three rounds having played nothing.
    """

    def __init__(self, world_getter=None):
        self.world_getter = world_getter
        self.steps = 0
        self.error = None
        self.stalled = None
        self._last = None
        self._repeat = 0
        self._tried = set()


    def _cmd(self, effect_id="0", targets=(), resources=()):
        return json.dumps({"id": str(effect_id),
                           "targets": [str(t) for t in targets],
                           "resources": [str(r) for r in resources]})

    @staticmethod
    def _cost(option):
        raw = ((option.get("target_payment") or {}).get("0") or {}).get("cost")
        if raw is None or raw == "":
            return 0
        text = str(raw).strip()
        if text.isdigit():
            return int(text)
        return len([c for c in text.upper() if c in "RBYGCW"])

    def _pay(self, option):
        payment = (option.get("target_payment") or {}).get("0") or {}
        pool = [list(e.keys())[0] for e in (payment.get("payment") or [])]
        return pool[:self._cost(option)]

    def _answer(self, option):
        """Respect the option's own target count. Handing a target to an option that
        asked for none is rejected, and the prompt repeats."""
        rng = option.get("target_num_range") or [0, 0]
        want = rng[1] if len(rng) > 1 else 0
        legal = [str(t) for t in (option.get("all_legal_targets") or [])]
        return self._cmd(option["id"], legal[:want], self._pay(option))

    def _end_game(self):
        """Stop the loop so the test can report, rather than hanging the suite."""
        try:
            world = self.world_getter() if self.world_getter else None
            if world is not None and not world.is_game_over:
                world.game_over.SetExit()
        except Exception:
            pass

    def __call__(self, payload, options):
        try:
            return self._decide(payload, options)
        except Exception as exc:          # never let the engine's crash handler exit()
            if self.error is None:
                import traceback
                self.error = traceback.format_exc()[-400:]
            return self._cmd("0")

    def _decide(self, payload, options):
        self.steps += 1
        signature = (payload.event_name, payload.prompt_text, len(options))
        if signature == self._last:
            self._repeat += 1
        else:
            self._last, self._repeat = signature, 0
            self._tried = set()

        if self._repeat > STALL_LIMIT:
            # Record it once, then stop repeating the answer the engine is refusing, or
            # the game never ends and the assertion never gets to fire.
            if self.stalled is None:
                self.stalled = "%s :: %s" % (
                    payload.event_name,
                    ",".join(sorted({str(o.get("name")) for o in options})))
            self._end_game()
            return self._cmd("0")
        if self.steps > MAX_STEPS:
            self._end_game()
            return self._cmd("0")
        if not options:
            return self._cmd("0")

        if payload.event_name == "WhenPlayerInTurn":
            # Try each option at most once per prompt. An ability that cannot actually be
            # used comes back as the same prompt, and re-offering it is an infinite loop
            # rather than a finding: an exerciser that cannot move on would report the
            # engine as stuck when it is the exerciser that is.
            fresh = [o for o in options if str(o.get("id")) not in self._tried]
            if not fresh:
                return self._cmd("0")          # nothing left to try: end the turn

            def rank(option):
                name = str(option.get("name"))
                for i, wanted in enumerate(("Play", "Attack", "Thwart")):
                    if name == wanted:
                        return i
                if name.startswith(("Change_", "Hero_Action", "Action")):
                    return 3
                return 4

            option = sorted(fresh, key=rank)[0]
            self._tried.add(str(option.get("id")))
            return self._answer(option)

        # A forced prompt takes id 0 only when one option needs no targets; with two,
        # declining is rejected and loops.
        forced = not payload.show_cancel
        if forced and len(options) > 1 and all(
                not (o.get("target_num_range") or [0, 0])[0] for o in options):
            return self._cmd(options[0]["id"])
        if payload.show_cancel:
            return self._cmd("0")
        option = options[0]
        need = (option.get("target_num_range") or [0, 0])[0]
        if not need:
            return self._cmd("0")
        return self._answer(option)


class TestGamesCanBePlayed(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from engine import Engine
        # `SaveCrash` hard-codes './crash.json' and then exit(-1) while in a unit test.
        # A policy bug would take the whole runner down with it and overwrite a real
        # crash repro on the way out.
        cls._saved_crash = Engine.SaveCrash
        Engine.SaveCrash = staticmethod(lambda: None)

    @classmethod
    def tearDownClass(cls):
        from engine import Engine
        Engine.SaveCrash = cls._saved_crash

    def _play(self, scenario, deck):
        from unit_test.harness import GameFixture
        holder = {}
        policy = Exerciser(lambda: holder.get("world"))
        fixture = GameFixture(scenario, [deck], seed=11, policy=policy)
        holder["fixture"] = fixture
        with fixture as fx:
            holder["world"] = fx.world
            fx.game.GameLoop()
            return fx.world, policy

    def test_every_matchup_reaches_a_real_ending(self):
        for scenario, deck in MATCHUPS:
            with self.subTest(scenario=scenario, deck=deck):
                world, policy = self._play(scenario, deck)

                self.assertIsNone(policy.error,
                                  "the policy raised while answering a prompt:\n%s"
                                  % policy.error)
                self.assertIsNone(policy.stalled,
                                  "a prompt repeated %d times with no progress, which "
                                  "means the engine could not use the answer: %s"
                                  % (STALL_LIMIT, policy.stalled))
                self.assertLess(policy.steps, MAX_STEPS,
                                "game did not finish within %d decisions" % MAX_STEPS)
                self.assertTrue(world.is_game_over, "game loop returned but no game over")

                # `players_won` is only a type annotation until the game ends in a win or
                # a loss, so its absence means the game ended some other way.
                won = getattr(world.game_over, "players_won", None)
                self.assertIsNotNone(
                    won, "game ended without a rules outcome (reason %r)"
                         % getattr(world.game_over, "reason", None))
                self.assertGreaterEqual(world.round_id, 2,
                                        "game ended before a second round, so almost "
                                        "nothing was exercised")

    def test_the_policy_actually_plays(self):
        """Guards the test itself. If the exerciser stops taking actions this suite goes
        on passing while covering nothing, which is the failure mode of a smoke test."""
        world, policy = self._play("rhino", "captain_america")
        self.assertGreater(policy.steps, 15,
                           "only %d decisions taken; the exerciser is not playing"
                           % policy.steps)


if __name__ == "__main__":
    unittest.main()
