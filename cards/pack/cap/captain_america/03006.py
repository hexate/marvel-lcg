from . import *

# Shield Toss

def GetAbilities() -> Sequence['Ability']:

    # How many cards the discard actually took, carried from the ability body to the target
    # selector below.
    #
    # It has to be carried, because the selector cannot look it up. `SetTarget2` is implemented by
    # `AskChooseSelect` (`game/player/model/player_ask.py:206-218`), which does not reuse this
    # effect: it builds a throwaway ability with `ForChoiceAbility(...).SetTargetInternal(selector)`
    # and asks the player to choose THAT. The selector is reused but is attached to a fresh effect,
    # one with an empty `cost_func` list, so a range callable reading
    # `effect.cost_func.Has(CostFunc.Discard)` gets `None` and the range collapses to (0, 0).
    # Verified by logging the effect identity from inside the callable: the body runs on effect
    # object 21 with cost funcs ['Discard', 'ReturnToHand'], while the range callable is handed
    # effect object 1 with none. That is why a range callable on a second target can only ever read
    # world state (as `ant/12032.py` does with the villain's stage), never anything about the effect
    # that owns it.
    #
    # A single cell is safe here despite being module-level state. It is written at the top of the
    # body and read during the `targets2` access three lines later, inside the same call, and
    # effects resolve one at a time.
    discarded = {"count": 0}

    def discarded_count(effect: 'Effect') -> int:
        return discarded["count"]

    def shield_toss(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Event)

        # The card is "discard any number of cards, then deal 4 damage to that many enemies", and
        # the two used to be chosen independently. `SetTarget` is resolved before `Play` pays the
        # costs (`card_player.py:126`), so the enemies were named first and the discard chosen
        # after, with nothing reconciling them: the body simply sliced,
        # `effect.targets[:discard_num]`. Select three enemies, discard nothing, and the card
        # resolved in silence with every enemy untouched (N10a, reported from play).
        #
        # Now the discard is known first and the enemy selection is bound to it, so the two cannot
        # disagree and the player is never offered a target they cannot pay for.
        discarded["count"] = len(effect.cost_func.Get(CostFunc.Discard).return_discarded_cards)
        this.DealDamage(effect.targets2, 4, effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            shield_toss,
        ).SetPlay().SetLabel('attack')
        # `(0, n)` and not `(n, n)`, which is a rules point as well as an engine one. The card
        # damages that many enemies, or all of them when there are fewer, and `GetTargetRange`
        # bails out entirely (`selector.py:83`, `len(faces) < target_range[0]` returns None) rather
        # than clamping when the minimum exceeds the enemies available. Discard two against a lone
        # villain and a `(2, 2)` range selects nothing at all, which is the original bug wearing a
        # different hat. Measured: `(2, 2)` with one enemy in play deals 0.
        .SetTarget2(Enemy, range=(0, discarded_count))
        .SetCostFunc(CostFunc.Discard("YourHandCards", range=(0, "All")))
        .SetCostFunc(CostFunc.ReturnToHand(
            card_type=Upgrade,
            name=CAPTAIN_AMERICAS_SHIELD,
            from_where=["YouControlCards"],
            to_who="Initiator"
        )),
    ]
