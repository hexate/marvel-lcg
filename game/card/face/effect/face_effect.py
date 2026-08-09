from core import *
from game.card.face import *
from game.effect import *
from game.message import *
from game.message.message_type import HasEndEventMessage

class FaceEffect:
    
    def __init__(self, this: 'CardFace') -> None:
        self.face = this
        self.global_effects: List['Effect'] = []
        self.local_effects: List['Effect'] = []
        self.given_effects: List['Effect'] = []

    def GetAll(self) -> Sequence['Effect']:
        return self.global_effects + self.local_effects + self.given_effects

    ################################################################################
    # Ability
    @final
    def FindAbility(self, ability: 'Ability') -> 'Effect|None':
        effects = self.Find(name=ability.name,
                        # func_name=ability.func_names,
                        # label=ability.labels,
                        # type=ability.type,
                        when=ability.when
        )
        if effects:
            return effects[0]
        else:
            return None

    @final
    def Find(self,
            *,
            name: str|None=None,
            func_name: "Ability.FUNCTION_NAME|None"=None,
            label: 'Ability.LABEL|None'=None,
            type: 'AbilityType|None'=None,
            when: 'Type[Message2]|None'=None) -> List['Effect']:
        effects: List['Effect'] = []
        for effect in self.GetAll():
            if label != None and not effect.ability.IsLabel(label):
                continue
            if func_name != None and not effect.ability.IsFunction(func_name):
                continue
            if name != None and not effect.IsName(name):
                continue
            if type != None and not effect.IsType(type):
                continue
            try:
                # Fix "43007". Some abilities declare a union `when`, for example
                # Message.WhenUnitWouldAttack|Message.WhenUnitWouldThwart, and issubclass()
                # raises TypeError on a union rather than returning False. Skip those.
                #
                # Only TypeError is tolerated. A bare except would also absorb genuine
                # failures, and because the handler continues, the effect is dropped from the
                # result with no crash and no log, so a card silently stops working.
                if when != None and not issubclass(effect.ability.when, when):
                    continue
            except TypeError:
                continue
            effects.append(effect)
        return effects

    @final
    def UnRegisterGiven(self, ability: 'Ability') -> None:
        for effect in self.given_effects:
            if effect.ability == ability:
                effect.UnRegisterSelf()
                return
        assert False

    @final
    def RegisterGiven(self, ability: 'Ability') -> 'Effect':
        effect = self.face.card.RegisterEffect(ability, self.face, world=self.face.card.world, is_temp=True)
        self.given_effects.append(effect)
        return effect

    @final
    def Registers(self, *abilities: 'Ability') -> List['Effect']:
        effects: List['Effect'] = []
        for ability in abilities:
            effects.append(self.RegisterInternal(ability))
        return effects

    @final
    def RegisterInternal(self, ability: 'Ability') -> 'Effect':
        if ability.is_local:
            return self.RegisterLocalInternal(ability)
        else:
            effect = self.face.card.RegisterEffect(ability, self.face, world=self.face.card.world)
            self.global_effects.append(effect)
            return effect

    @final
    def RegisterLocalInternal(self, ability: 'Ability') -> 'Effect':
        effect = self.face.card.RegisterEffect(ability, self.face, is_local=True, world=self.face.card.world)
        self.local_effects.append(effect)
        return effect

    @final
    def RegisterTemp(self, *abilities: 'Ability',
                    unregister_after_exec: bool,
                    until_turn_end: bool=False,
                    until_next_turn_end: bool=False,
                    until_phase_end: bool=False,
                    until_round_end: bool=False,
                    until_this_leave_play: bool=False,
                    until_event_end: 'HasEndEventMessage|Message.WhenUnitWouldAttack|Message.WhenUnitWouldThwart|Message.WhenUnitWouldScheme|Message.WhenUnitWouldDefend|None'=None,
                    until_resolve_effect: 'Effect|None'=None,
                    ) -> List['Effect']:
        effects: List['Effect'] = []
        for ability in abilities:
            if ability.flags.is_delay_ability:
                assert unregister_after_exec == False
            effect = self.face.card.RegisterEffect(ability, self.face, is_temp=True, world=self.face.card.world)
            effect.SetDestroyedAfter(unregister_after_exec,
                until_turn_end=until_turn_end,
                until_next_turn_end=until_next_turn_end,
                until_phase_end=until_phase_end,
                until_round_end=until_round_end,
                until_this_leave_play=until_this_leave_play,
                until_after_event=until_event_end,
                until_after_resolve_effect=until_resolve_effect,
            )
            effects.append(effect)
        self.global_effects += effects

        return effects

