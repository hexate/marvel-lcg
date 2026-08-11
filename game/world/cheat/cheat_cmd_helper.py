from core import *
from cards.database import CardsDB
from engine import Engine
from engine.file import FileManager
from engine.lib import Random
from engine.log import Log
from engine.security.command_validation import IsCommandSafe
from game.card.factory import CardFactory
from game.effect import Effect
from game.buff import *
from game.effect.rule import DebugRule, GameRule
from game.card import *
from game.card.face.base import Enemy
from game.card.face.base import ClassCard
from game.card.face.card_face import CardFace
from game.card.face.component.attach import PlacedCard
from game.card.face.component.inventory import Inventory
from game.element.resources import Resources
from game.message import Message
from game.operate.faces import Faces
from game.operate.worlds import Worlds
from game.player import Player
from game.puzzle import RunPuzzle
from game.test import Test
from game.world import *
from game.world.cheat.cheat_cmd import CheatCommand
from game.world.world import Phase
Unused(GameRule)
Unused(Random)
Unused(Player, Inventory, PlacedCard, CardFace, Message, Engine, Phase)
Unused(Tracker)

CATEGORY_NAME = "CHEAT"

world: 'World'
cheat: 'CheatCommand'
puzzle: 'RunPuzzle'

help = """
--- Variable ---
c: card     # e.g. c19 c33
p: player
h: hero
v: villain
m: Main Scheme

--- Functions ---
Gain    = Draw
Draw    (CardName, num = 1)
Edit    (CardName)
Play    (CardName)
Ready   (CardName)
Discard (CardName)
Remove  (CardName)

Heal    (CardName, int = 30)
Damage  (CardName, int = 30, CardFace = None)
Confuse (CardName)
Stun    (CardName)
Tough   (CardName)
Place   (CardName, int = 2)
Change  (CardName)
Change2 (CardName)
Blank   (CardName)
Trait   (CardName, trait)

Reveal  (CardName)
Boost   (CardName)
DoAttack(CardName)
DoScheme(CardName)

Put     (CardName, int = 1) # Put to deck top
Empty   (CardName, int = 10)
Sort    (CardName)
Shuffle (CardName)

Res     (str = "GGGG")

Test    (json_path)
"""

CardName = RunPuzzle.CardName

def LogTest(text: str):
    from colorama import Fore
    Log.Debug(CATEGORY_NAME, f"{Fore.BLUE}{text}{Fore.RESET}")

################################################################################
#
def Edit(card: CardName):
    face = puzzle.FindOrCreateFace(card)
    paper = face.paper
    file_path = f'./cards/pack/{paper.pack}/{paper.card_id}.py'
    if FileManager.Exists(file_path):
        FileManager.EditCode(file_path)
    else:
        Log.Warn(CATEGORY_NAME, f'{paper.card_id} not found!')

################################################################################
# Player
def Draw(num: int):
    puzzle.Draw(num)

@overload
def Gain(*cards: CardName) -> None: ...

@overload
def Gain(card: CardName, num: int=1) -> None: ...

def Gain(*args: CardName|int, **kwargs: Any) -> None:
    if len(args) == 2 and isinstance(args[1], int):  # Card and num case
        card_name = args[0]
        assert isinstance(card_name, CardName)
        num = args[1]
        for _ in range(num):
            face = puzzle.FindOrCreateFace(card_name)
            player = world.GetCurrentPlayer()
            effect = DebugRule(player.GetIdentity())
            player.GainCard(face, effect)
            if num != 1:
                cheat.LogDebugCommand(face)
    else:
        def is_cards(args: Any) -> TypeGuard[List[CardName]]:
            return True
        assert is_cards(args)
        puzzle.Gain(*args, call_back=cheat.LogDebugCommand)

def Gains(*cards: CardName):
    puzzle.Gain(*cards, call_back=cheat.LogDebugCommand)

def Play(card: CardName) -> 'CardFace':
    face = puzzle.FindOrCreateFace(card)
    played = False
    if ClassCard.IsType(face):
        effects = face.effect.Find(func_name="Play")
        for play_effect in effects:
            player = world.GetCurrentPlayer()
            play_effect.context.initiator = player
            effect =  DebugRule(player.GetIdentity())
            message = Message.WhenPlayerLikeInTurn(player, effect)
            message.Send()
            play_effect.checker.UpdateLegalTargets()
            # effect.targets = effect.all_legal_targets[:effect.target_range[1]]
            play_effect.context.targets_internal = player.AskChooseFaces(play_effect.context.all_legal_targets, play_effect.context.target_range, play_effect)
            play_effect.context.bind_message = message
            from_area = face.card.area
            Faces.MoveAllToProcessingArea([face], play_effect)
            face.Play(player, play_effect, message, Resources("0"), from_area, False)
            played = True
    if not played:
        Gain(face)
    return face

################################################################################
# Card
def Ready(*cards: CardName):
    puzzle.Ready(*cards)

def Exhaust(*cards: CardName):
    puzzle.Exhaust(*cards)

def Discard(*cards: CardName):
    puzzle.Discard(*cards)

def Remove(*cards: CardName):
    puzzle.Remove(*cards)

def Flip(*cards: CardName):
    puzzle.Flip(*cards)

################################################################################
# Unit
def Heal(card: CardName, val: int=30):
    puzzle.Heal(card, val)

def Damage(card: CardName, val: int=30, source: CardFace|None=None):
    puzzle.Damage(card, val, source)

def Confuse(card: CardName):
    puzzle.Confuse(card)

def Stun(card: CardName):
    puzzle.Stun(card)

def Tough(card: CardName):
    puzzle.Tough(card)

def PlaceThreat(card: CardName, val: int=2):
    puzzle.PlaceThreat(card, val)

def Threat(card: CardName, val: int=2):
    PlaceThreat(card, val)

def SetThreat(card: CardName, val: int):
    puzzle.SetThreat(card, val)

@deprecated("PlaceThreat")
def Place(card: CardName, val: int=2):
    PlaceThreat(card, val)

def ChangeForm(card: CardName, rule: Literal['', 'Identity', 'Hero']=''):
    puzzle.ChangeForm(card, rule)

@deprecated("ChangeForm")
def Change(card: CardName):
    ChangeForm(card, 'Identity')

@deprecated("ChangeForm")
def Change2(card: CardName):
    ChangeForm(card, 'Hero')

as_blank_effect: 'Effect|None' = None

def Blank(*cards: CardName):
    global as_blank_effect
    if as_blank_effect == None or as_blank_effect.world != world:
        villain = Worlds.GetAllVillains(world)[0]
        as_blank_effect = DebugRule(villain)

    for card in cards:
        face = puzzle.FindOrCreateFace(card)

        if as_blank_effect in face.GetBuff(BuffIsTreatAsIfBlank).by_effects:
            face.TreatAsIfBlankInternal(-1, as_blank_effect)
        else:
            face.TreatAsIfBlankInternal(+1, as_blank_effect)

as_trait_effect: 'Effect|None' = None

def Trait(card: CardName, trait: "CardFace.TRAITS"):
    global as_trait_effect
    face = puzzle.FindOrCreateFace(card)

    if as_trait_effect == None:
        as_trait_effect = DebugRule(world.GetFirstPlayer().GetIdentity())

    if as_trait_effect and face.HasTrait(trait):
        face.GainTraits(-1, trait, as_trait_effect)
    else:
        face.GainTraits(+1, trait, as_trait_effect)

def Counter(card: CardName, name: 'CardFace.COUNTER', size: int=3):
    return puzzle.Counter(card, name, size)

def Token(card: CardName, name: 'CardFace.TOKEN', size: int=3):
    return puzzle.Token(card, name, size)

################################################################################
# Treachery
def Reveal(card: CardName) -> 'CardFace':
    return puzzle.Reveal(card, call_back=cheat.LogDebugCommand)

def PutIntoPlay(card: CardName) -> 'CardFace':
    return puzzle.PutIntoPlay(card)

def Boost(card: CardName) -> 'CardFace':
    return puzzle.Boost(card)

def Deal(card: CardName) -> 'CardFace':
    return puzzle.Deal(card)

################################################################################
# Enemy
def DoAttack(card: CardName) -> 'CardFace':
    face = puzzle.FindOrCreateFace(card)
    if Enemy.IsType(face):
        player = world.GetCurrentPlayer()
        effect = DebugRule(player.GetIdentity())
        face.DoAttackYou(player, effect)
    return face

def DoScheme(card: CardName) -> 'CardFace':
    face = puzzle.FindOrCreateFace(card)
    if Enemy.IsType(face):
        player = world.GetCurrentPlayer()
        effect = DebugRule(player.GetIdentity())
        face.DoSchemes(player, effect)
    return face

def DoActivate(card: CardName) -> 'CardFace':
    face = puzzle.FindOrCreateFace(card)
    if Enemy.IsType(face):
        player = world.GetCurrentPlayer()
        effect = DebugRule(player.GetIdentity())
        face.DoActivate(player, effect)
    return face

################################################################################
# Check
def CannotTarget(face: CardName, effect_name: str|None, *targets: CardName):
    face = puzzle.FindOrCreateFace(face)
    faces = puzzle.FindCommandCards(*targets)
    if faces == []:
        for effect in world.controller_manager.console.effect_list:
            if effect.this == face and (effect_name == None or effect.IsName(effect_name)):
                assert False
            else:
                LogTest(f"Check OK: {effect}")
        LogTest(f"Check done")
    else:
        for effect in world.controller_manager.console.effect_list:
            if effect.this == face and (effect_name == None or effect.IsName(effect_name)):
                assert all(x not in effect.context.all_legal_targets for x in faces)
                LogTest(f"Check OK: {effect}")
        LogTest(f"Check done")

def CanTarget(face: CardName, effect_name: str|None, *targets: CardName):
    face = puzzle.FindOrCreateFace(face)
    faces = puzzle.FindCommandCards(*targets)
    check_faces: Set['CardFace'] = set()
    for effect in world.controller_manager.console.effect_list:
        ok = False
        if effect.this == face and (effect_name == None or effect.IsName(effect_name)):
            if targets == ():
                ok = True # Check can trigger
            else:
                for target in effect.context.all_legal_targets:
                    if target in faces:
                        ok = True
                        check_faces.add(target)
        if ok:
            LogTest(f"Check OK: {effect}")
    assert check_faces == set(faces)

################################################################################
# Deck
def PutIntoDeck(*cards: CardName):
    puzzle.PutIntoDeck(*cards)

@deprecated("PutIntoDeck")
def Put(card: CardName, num: int = 1):
    PutIntoDeck(*[card]*num)

def PutAll(card: CardName):
    face = puzzle.FindOrCreateFace(card)
    faces = face.card.area.Get()[:]
    face_deck = {x: x.card.area for x in faces}
    for face in faces:
        player = world.GetCurrentPlayer()
        effect = DebugRule(player.GetIdentity())
        if face.card.GetOwner() == player:
            Faces.MoveAllTo([face], player.player_deck, effect)
        else:
            villain = Worlds.FindVillainByGameArea(player.GetIdentity().card.game_area)
            if villain:
                Faces.MoveAllTo([face], villain.encounter_deck, effect)
    message = Message.AfterCardsMoved(face_deck)
    message.Send()

def DiscardDeck(card: CardName, size: int|Literal["All", "Except"], from_top:bool=True):
    face = puzzle.FindOrCreateFace(card)
    effect = DebugRule(face)
    if size == "Except":
        faces = face.card.area.GetAll(from_top)
        faces.remove(face)
        Faces.DiscardAll(faces, effect)
    elif size == "All":
        face.card.area.DiscardAll(effect)
    else:
        Faces.DiscardAll(face.card.area.GetAll(from_top)[:size], effect)

@deprecated("DiscardDeck")
def DiscardAll(card: CardName):
    DiscardDeck(card, "All")

@deprecated("DiscardDeck")
def Empty(card: CardName, size: int|Literal["All"]=10):
    DiscardDeck(card, size)

# def Drop(card: CardName):
#     card = FindOrCreateCard(card)
#     card.area.DiscardAll(DebugRule(card.face))

def SortDeck(card: CardName):
    face = puzzle.FindOrCreateFace(card)
    face.card.area.Sort()

@deprecated("SortDeck")
def Sort(card: CardName):
    SortDeck(card)

def Shuffle(card: CardName):
    face = puzzle.FindOrCreateFace(card)
    effect = DebugRule(face)
    face.card.area.Shuffle(effect)

def Unshuffle(card: CardName):
    face = puzzle.FindOrCreateFace(card)
    effect = DebugRule(face)
    Random.Undo()
    face.card.area.Unshuffle(effect)

def Res(res: str = "RBYG"):
    player = world.GetCurrentPlayer()
    effect = DebugRule(player.GetIdentity())
    player.res_pool.Gain(Resources.FromText(res), effect)

def Eliminate(player_id: int):
    player = world.const_seat_order_players[player_id]
    effect = DebugRule(player.GetIdentity())
    player.Eliminate(effect)

def Sets(card_id: str):
    set_name = CardsDB.papers[card_id].set_name
    if set_name in CardsDB.sets_cards:
        deck = world.scenario.encounter_deck
        CardFactory.GenerateCards(CardsDB.sets_cards[set_name], deck, world)

################################################################################
#
def IsUntrustedScenePath(scene_path: str) -> bool:
    """Did this scene come from the internet rather than from this machine?

    Downloaded crash saves land under `crashs/dl`, and a scene can carry debug commands that
    `RunCheat` will `exec`, so those get a break first. The test used to be a literal
    `"crashs\\dl"`, which is only ever how the path looks on Windows: on macOS and Linux the
    separator is `/`, the test never matched, and the break in front of `exec` quietly never
    happened on the platforms this fork runs on.
    """
    return "crashs/dl" in scene_path.replace("\\", "/")

################################################################################
#
def RunCheat(current_world: 'World', commands: Sequence[str], player_id: int):
    global world, cheat, puzzle
    world   = current_world
    cheat   = world.cheat
    puzzle  = RunPuzzle(world)

    # if not world.is_game_started:
    #     if world.phase.state != Phase.State.ResolveMulligans:
    #         assert commands == ["break"], f"{commands=}"

    player      = world.GetCurrentPlayer()
    hero        = player.GetIdentity()
    villains    = Worlds.GetAllVillains(world)
    rule        = world.rule

    Unused(hero)
    Unused(villains)
    Unused(rule)

    for c in world.object_manager.card_dict:
        exec(f'c{c} = world.object_manager.card_dict[{c}].face')

    for e in world.object_manager.effect_dict:
        exec(f'e{e} = world.object_manager.effect_dict[{e}]')

    for i in range(len(world.const_players)):
        exec(f'p{i} = world.const_players[{i}]')

    c = world.object_manager.card_dict
    e = world.object_manager.effect_dict
    p = player
    Unused(c)
    Unused(e)
    Unused(p)

    # event_manager = world.event_manager
    # Unused(event_manager)

    for command in commands:
        if not Test.IsInTesting():
            Log.Debug(CATEGORY_NAME, "> " + command)
        else:
            Log.Test("> " + command)

        if command.startswith('#') or command == '':
            pass
        elif command == 'break':
            Debug.DebugBreak()
        elif not IsCommandSafe(command):
            Log.Assert(CATEGORY_NAME, f"Unsafe code detected: {command}")
            Debug.DebugBreak()
        else:
            val: Any = None
            Unused(val)

            cmd = f"""
val = {command}
if val != None:
    if isinstance(val, list) and isinstance(val[0], CardFace):
        if not Test.is_in_test:
            for i in range(len(val)):
                Log.Debug(f'{{i}}. {{val[i]}}')
        val = None
if val != None and not Test.is_in_test:
    Log.Debug(f'{{val}}')
"""
            try:
                if IsUntrustedScenePath(world.scene.path):
                    """This save is download from internet, please make sure it is safe enough"""
                    Debug.DebugBreak()
                exec(cmd)

            except Exception as exc:
                Log.Print(f"Error when running debug command: {command}")
                Log.Print(f"```py{cmd}```")
                Log.FailedTrace(CATEGORY_NAME, exc, no_take_as_error=True)
                raise

    # if world.is_game_over:
    #     Engine.game.session.SaveScene(delete_old=True)
    return

