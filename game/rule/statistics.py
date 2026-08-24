from core import *
from game.ability import *
from game.card.face import *
from game.message import *
from game.player import *

def GetStatisticsRule() -> List['Ability']:
    from game.card.face.base import Scheme2
    from game.card.face.base import Unit2
    from game.card.face.card_type import Environment
    from game.card.face.card_type import Event
    from game.card.face.card_type import Obligation
    from game.card.face.card_type import Resource
    from game.card.face.card_type import Support
    from game.card.face.card_type import Support
    from game.card.face.card_type import Treachery
    from game.card.face.card_type import Upgrade
    from game.operate.worlds import Worlds
    from engine import Engine

    def scenario_key(message: 'Message.WhenGameOver') -> str:
        """The scenario as it is named on screen, with what makes it a harder fight.

        Expert and challenge runs are counted apart from the standard ones. Both can be on at
        once, which the replay's own name does not allow for.
        """
        campaign = message.world.scene.campaign
        marks = list(campaign.challenges)
        if campaign.expert:
            marks.append("Expert")
        if not marks:
            return campaign.name
        return f"{campaign.name} ({', '.join(marks)})"

    def statistics_gameover(message: 'Message.WhenGameOver'):
        from game.world.game_over import GAME_OVER_OUTCOME_BY_REASON

        # Why the game ended, not just whether it was won. The reason arrives on the message and
        # was read no further than `players_won` before.
        if message.reason in GAME_OVER_OUTCOME_BY_REASON:
            Engine.statistics.RecordGameOver(scenario_key(message), GAME_OVER_OUTCOME_BY_REASON[message.reason])

        if message.players_won == True:
            for face in Worlds.GetAllMainSchemes(message.world):
                Engine.statistics.RecordCard(face, "GameOver")
            for face in message.world.area_rule.GetAll():
                Engine.statistics.RecordCard(face, "GameOver")
            for face in message.world.area_insert.GetAll():
                Engine.statistics.RecordCard(face, "GameOver")
            Engine.statistics.RecordValue("games_won", 1)
            # for face in message.world.GetAllVillains():
            #     if not face.IsDefeated():
            #         Engine.statistics.Record(face, "Defeated")
        elif message.players_won == False:
            for player in message.world.const_players:
                face = player.GetIdentity()
                Engine.statistics.RecordCard(face, "Defeated")
            Engine.statistics.RecordValue("games_lost", 1)

    def remove_threats(message: 'Message.AfterSchemeRemoveThreat'):
        Engine.game.session.statistics.Add(message.by_effect.this, message.value, 'thwarted_threat')
        Engine.statistics.RecordValue("total_threats_removed", message.value)

    def heal_damage(message: 'Message.AfterUnitHealHealth'):
        Engine.statistics.RecordValue("total_damage_healed", message.value)
        Engine.statistics.RecordMaximum("max_single_damage_healed", message.value)

    def player_drawn(message: 'Message.AfterPlayerDrewCards'):
        Engine.statistics.RecordValue("total_cards_drawn", message.size)
        Engine.statistics.RecordMaximum("max_single_cards_drawn", message.size)

    def deal_damage(message: 'Message.AfterFaceDealDamage'):
        Engine.game.session.statistics.Add(message.by_effect.this, message.dealt_damage, 'damage_dealt')
        Engine.statistics.RecordValue("total_damage_dealt", message.dealt_damage)
        Engine.statistics.RecordMaximum("max_single_damage_dealt", message.dealt_damage)

    def take_damage(message: 'Message.AfterFaceDealDamage'):
        Engine.game.session.statistics.Add(message.target, message.dealt_damage, 'damage_taken')
        Engine.statistics.RecordValue("total_damage_taken", message.dealt_damage)
        Engine.statistics.RecordMaximum("max_single_damage_taken", message.dealt_damage)

    def statistics_record(face: 'CardFace', method: Literal["Resolve", "Play", "Resource", "Reveal", "PutIntoPlay", "Hero", "Attached", "Defeated", "Discard", "Cancel"]):
        if method == "PutIntoPlay":
            Engine.game.session.statistics.Add(face, 1, 'entered_play')
        Engine.statistics.RecordCard(face, method)

    def statistics_games_new(message: 'Message.WhenGameWouldBegin'):
        Engine.statistics.RecordValue("games_new", 1)

    def statistics_generate_resources(message: 'Message.WhenCardBeSpendAsResource'):
        r = message.res.GetColor("R", convert_green_res=False)
        b = message.res.GetColor("B", convert_green_res=False)
        y = message.res.GetColor("Y", convert_green_res=False)
        g = message.res.GetColor("G", convert_green_res=False)
        if r:
            Engine.statistics.RecordValue("generate_resources_r", r)
        if b:
            Engine.statistics.RecordValue("generate_resources_b", b)
        if y:
            Engine.statistics.RecordValue("generate_resources_y", y)
        if g:
            Engine.statistics.RecordValue("generate_resources_g", g)

    def statistics_play_aspect(message: 'Message.AfterPlayerPlayedCard'):
        statistics_name: Dict[ClassCard.CARD_CLASS, Literal[
            'play_aspect_aggression',
            'play_aspect_justice',
            'play_aspect_leadership',
            'play_aspect_protection',
            'play_aspect_pool',
            'play_basic_cards',
            'play_identity_specific',
        ]] = {
            "Aggression":       'play_aspect_aggression',
            "Justice":          'play_aspect_justice',
            "Leadership":       'play_aspect_leadership',
            "Protection":       'play_aspect_protection',
            "'Pool":            'play_aspect_pool',
            "Basic":            'play_basic_cards',
            "IdentitySpecific": 'play_identity_specific',
        }
        for aspect in statistics_name:
            if message.played_face.IsClass(aspect):
                Engine.statistics.RecordValue(statistics_name[aspect], 1)
                break

    def statistics_run_out_of_deck(message: 'Message.AfterDeckRunOut'):
        Engine.statistics.RecordValue("run_out_of_deck", 1)

    def statistics_engaged(message: 'Message.AfterMinionEngagePlayer'):
        Engine.statistics.RecordValue("engaged_minions", 1)
        Engine.statistics.RecordMaximum("max_engaged_minions", len(message.engaged_player.GetEngagedMinions()))

    return [
        Ability(
            AbilityType.Statistics,
            Message.WhenEffectWouldResolve,
            [
                lambda effect, message:
                    not message.effect.is_rule and \
                    # not message.effect.ability.is_forced and \
                    (
                        message.effect.ability.flags.is_setup or
                        message.effect.ability.flags.is_action or
                        message.effect.ability.flags.is_interrupt or
                        message.effect.ability.flags.is_response or
                        message.effect.ability.flags.is_special or
                        message.effect.ability.flags.is_resource or
                        message.effect.ability.flags.is_when_reveal or
                        message.effect.ability.flags.is_when_defeated or
                        message.effect.ability.flags.is_when_completed or
                        message.effect.ability.flags.is_boost
                    ),
            ],
            lambda effect, message:
                statistics_record(message.effect.this, "Resolve")
        ),
        Ability(
            AbilityType.Statistics,
            Message.WhenEffectWouldResolve,
            [
                lambda effect, message:
                    not message.effect.is_rule and \
                    message.effect.ability.flags.is_status,
            ],
            lambda effect, message:
                statistics_record(message.effect.this, "Resolve")
        ),
        # Ability(
        #     AbilityType.Statistics,
        #     Send.WhenPlayerSelectHero,
        #     [],
        #     lambda effect, message:
        #         statistics_record(message.trigger, "Hero")
        # ),
        # Ability(
        #     AbilityType.Statistics,
        #     Send.AfterIdentityChangeForm,
        #     [],
        #     lambda effect, message:
        #         statistics_record(message.trigger, "Hero")
        # ),
        Ability(
            AbilityType.Statistics,
            Message.WhenCardRevealed,
            [
                lambda effect, message:
                    Treachery.IsType(message.trigger) or \
                    Obligation.IsType(message.trigger),
            ],
            lambda effect, message:
                statistics_record(message.trigger, "Reveal")
        ),
        Ability(
            AbilityType.Statistics,
            Message.WhenCardEnterPlay,
            [
                lambda effect, message:
                    Unit2.IsType(message.trigger) or \
                    Scheme2.IsType(message.trigger) or \
                    Support.IsType(message.trigger) or \
                    Challenge.IsType(message.trigger) or \
                    # Obligation.IsType(message.trigger) or \ # We do this in `WhenCardRevealed`
                    Environment.IsType(message.trigger),
            ],
            lambda effect, message:
                statistics_record(message.trigger, "PutIntoPlay")
        ),
        Ability(
            AbilityType.Statistics,
            Message.WhenPlayerPlayCard,
            [
                lambda effect, message:
                    Event.IsType(message.played_face),
            ],
            lambda effect, message:
                statistics_record(message.played_face, "Play")
        ),
        Ability(
            AbilityType.Statistics,
            Message.AfterSchemeBeDefeated,
            [],
            lambda effect, message:
                statistics_record(message.trigger, "Defeated")
        ),
        Ability(
            AbilityType.Statistics,
            Message.AfterUnitBeDefeated,
            [],
            lambda effect, message:
                statistics_record(message.trigger, "Defeated")
        ),
        Ability(
            AbilityType.Statistics,
            Message.WhenEffectWouldResolve,
            [
                lambda effect, message:
                    not message.effect.is_rule and \
                    Resource.IsType(message.effect.this) and \
                    message.effect.ability.flags.is_discard_pay,
            ],
            lambda effect, message:
                statistics_record(message.effect.this, "Resource")
        ),
        Ability(
            AbilityType.Statistics,
            Message.WhenCardWouldAttachTo,
            [],
            lambda effect, message:
                statistics_record(message.trigger, "Attached")
        ),
        Ability(
            AbilityType.Statistics,
            Message.AfterCardDiscard,
            [
                lambda effect, message:
                    message.from_area.flags.is_in_play and \
                    (
                        Upgrade.IsType(message.trigger) or \
                        Support.IsType(message.trigger)
                    ),
            ],
            lambda effect, message:
                statistics_record(message.trigger, "Discard")
        ),
        Ability(
            AbilityType.Statistics,
            Message.WhenEffectBeCancel,
            [
                lambda effect, message:
                    Treachery.IsType(message.trigger) or \
                    Obligation.IsType(message.trigger),
            ],
            lambda effect, message:
                statistics_record(message.trigger, "Cancel")
        ),
        Ability(
            AbilityType.Statistics,
            Message.WhenGameOver,
            [],
            lambda effect, message:
                statistics_gameover(message)
        ),
        Ability(
            AbilityType.Statistics,
            Message.AfterSchemeRemoveThreat,
            [
                lambda effect, message:
                    message.by_effect.IsPlayerInitiator(),
            ],
            lambda effect, message:
                remove_threats(message)
        ),
        Ability(
            AbilityType.Statistics,
            Message.AfterUnitHealHealth,
            [
                lambda effect, message:
                    Player.IsType(message.trigger.GetControlBy()),
            ],
            lambda effect, message:
                heal_damage(message)
        ),
        Ability(
            AbilityType.Statistics,
            Message.AfterPlayerDrewCards,
            [],
            lambda effect, message:
                player_drawn(message)
        ),
        Ability(
            AbilityType.Statistics,
            Message.AfterFaceDealDamage,
            [
                lambda effect, message:
                    Player.IsType(message.target.GetControlBy()),
            ],
            lambda effect, message:
                take_damage(message)
        ),
        Ability(
            AbilityType.Statistics,
            Message.AfterFaceDealDamage,
            [
                lambda effect, message:
                    # Unit2.IsType(message.attacker) and \
                    message.attacker != None and \
                    Player.IsType(message.attacker.GetControlBy()) or \
                    PlayerCard.IsType(message.by_effect.this),
            ],
            lambda effect, message:
                deal_damage(message)
        ),
        Ability(
            AbilityType.Statistics,
            Message.WhenGameWouldBegin,
            [],
            lambda effect, message:
                statistics_games_new(message)
        ),
        Ability(
            AbilityType.Statistics,
            Message.WhenCardBeSpendAsResource,
            [],
            lambda effect, message:
                statistics_generate_resources(message)
        ),
        Ability(
            AbilityType.Statistics,
            Message.AfterPlayerPlayedCard,
            [],
            lambda effect, message:
                statistics_play_aspect(message)
        ),
        Ability(
            AbilityType.Statistics,
            Message.AfterDeckRunOut,
            [
                lambda effect, message:
                    message.deck.flags.is_player_deck,
            ],
            lambda effect, message:
                statistics_run_out_of_deck(message)
        ),
        Ability(
            AbilityType.Statistics,
            Message.AfterMinionEngagePlayer,
            [],
            lambda effect, message:
                statistics_engaged(message)
        ),
    ]

