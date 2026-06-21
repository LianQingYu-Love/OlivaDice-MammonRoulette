from ..Core.cmop import EffectComp
from ..Core.work import RegGameWork


class BaseEffect:
    name = ""
    brief = ""

    @classmethod
    def init(cls):
        pass

    @classmethod
    def apply(cls, msg_manager, target, stacks) -> bool | None:
        pass

    @classmethod
    def callback(cls, msg_manager, moment, target, stacks) -> bool | None:
        pass


class 神经麻痹(EffectComp, BaseEffect):
    """
    "modify":{
        "神经麻痹":{
            "user_id":{
                "final_attacker": str,
            }
        }
    }
    """

    name = "神经麻痹"
    brief = "回合结束时失去所有[神经麻痹], 并失去等同值+1的HP."

    @classmethod
    def apply(cls, msg_manager, target, stacks):
        game, _, _, _, players, _, modify = RegGameWork.get_index(msg_manager)
        RegGameWork.create_effect_event(game, "神经麻痹", target, stacks)
        comp = modify.setdefault("神经麻痹", {})
        comp.setdefault(target, {"final_attacker": ""})
        return True

    @classmethod
    def callback(cls, msg_manager, moment, target, stacks):
        game, _, reply, tmp, _, shooter, modify = RegGameWork.get_index(msg_manager)
        if moment != "end_round" or target != shooter:
            return False
        comp = modify["神经麻痹"]
        murderer = comp[target]["final_attacker"]
        del comp[target]
        tmp["dmg_type"] = "神经麻痹"
        tmp["is_attack_me"] = target == murderer
        RegGameWork.damage(msg_manager, target, stacks, murderer)
        reply["info"].append(
            f"{RegGameWork.get_name(game, target)}感到神经絮乱[hp{tmp['hp_before']}->{tmp['hp_now']}]."
        )
        return True
