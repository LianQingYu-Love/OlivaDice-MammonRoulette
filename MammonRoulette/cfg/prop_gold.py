import random

from ..cmd import commands
from ..doc import helpdoc
from ..core.work import GameWork
from ..core.cmop import PropComp


prop_list = [prop for prop in PropComp.list() if prop != "金币"]


@helpdoc.update_cmd("购买(道具名) #使用金币兑换道具")
@commands.route("play", f"^(:?购买|購買) *({'|'.join(prop_list)})$")
def purchase(game, user_id, group_id, msg_groups):
    if game["shooter"] != user_id:
        return f"現在是{GameWork.get_name(game)}的回合."
    if "金币" not in game["players"][user_id]["props"]:
        return "沒錢還想買道具?"
    Gold.apply(game, user_id, msg_groups[0])
    return GameWork.reply(game), True


class Gold(PropComp):
    name = "金币"
    brief = "兑换任意 1 个未被ban的道具.\n#增加指令\n购买(道具名) //使用金币兑换道具."

    @staticmethod
    def reply():
        return random.choice(
            ("嶄新", "啞暗", "磨損", "變形", "鏽蝕", "斑駁", "鏤空", "黏膩", "沾血")
        )

    @classmethod
    def apply(cls, game, user_id, prop):
        if prop in game["props"]["ban"]:
            game["reply"]["info"].append(f"{prop}被禁售了.")
            return False
        pl = game["players"][user_id]
        props = pl["props"]
        props[props.index("金币")] = prop
        name = pl["name"]
        reply = f"{name}向自動販賣機投入一枚{cls.reply()}的金幣, " + (
            f"結果沒有任何反應, {name}將其砸爛，取出{prop}."
            if random.randint(1, 4) == 1
            else f"自動販賣機吐出{prop}."
        )
        game["reply"]["info"].append(reply)
        return True
