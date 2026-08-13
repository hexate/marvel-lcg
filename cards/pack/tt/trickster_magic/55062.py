from . import *

# Love Triangle

def GetAbilities() -> Sequence['Ability']:

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            "YourAlly",
            if_cannot_gain_surge=True
        ),
        *AbilityFactory.UnitCannotAttackTarget(
            "AttachedAlly",
            cannot_attack=Villain
        ),
        *AbilityFactory.UnitCannotDefend(
            "AttachedAlly",
            Villain,
            # Only the attached ally is restricted, not its controller, so there is no
            # player-level ban on defense abilities here. The UnitCannotAttackTarget call above
            # already adds none for the attack half.
            cannot_trigger_defense_ability=False
        ),
        AbilityFactory.PlayerActionToDiscardThis(
            AbilityType.AlterEgoAction,
        ).SetCost(Cost("B"))
        .SetCostFunc(CostFunc.Exhaust("Attached")),
    ]

