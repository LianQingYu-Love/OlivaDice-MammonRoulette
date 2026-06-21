# -*- encoding: utf-8 -*-
"""
@File      :    MammonRoulette/Defs/prop.py
@Author    :    LianQingYu-Love恋倾雨
@Contact   :    xinghu2408@foxmail.com
@License   :    AGPLv3
@Copyright :    (C) 2026 MammonRoulette
@Desc      :    None
"""

import random
import string

from ..main import commands
from ..custom import dictHelpDoc
from ..Core.cmop import ModeComp, PropComp, EffectComp
from ..Core.work import RegGameWork


class BaseProp:
    name = ""
    brief = ""

    @classmethod
    def init(cls):
        pass

    @classmethod
    def apply(cls, msg_manager, target) -> bool | None:
        pass

    @classmethod
    def callback(cls, msg_manager, moment) -> bool | None:
        pass


class 手铐(PropComp, BaseProp):
    name = "手铐"
    brief = "使用者不可作为目标. 束缚目标行动 1 回合, 且在目标恢复行动前无法再次将其选为目标."

    @staticmethod
    def reply():
        return random.choice(("双手", "双手", "双手", "双腿"))

    @classmethod
    def apply(cls, msg_manager, target):
        game = msg_manager.val["game"]
        data, reply = game["data"], game["reply"]
        if target == data["shooter"]:
            order = data["order"]
            target = order[(order.index(data["shooter"]) + 1) % len(order)]
        comp = data["modify"].setdefault("手铐", [])
        pl_target = data["players"][target]
        if target not in comp:
            comp.append(target)
            pl_target["actions"] -= 1
            RegGameWork.create_prop_event(game, "手铐", "switch")
            reply["info"].append(f"{pl_target['name']}被銬住了{cls.reply()}.")
            return True
        reply["info"].append(f"{pl_target['name']}已經被铐住了.")
        return False

    @classmethod
    def callback(cls, msg_manager, moment):
        game = msg_manager.val["game"]
        data = game["data"]
        comp = data["modify"]["手铐"]
        shooter = data["shooter"]
        if shooter in comp:
            comp.remove(shooter)
            return True
        return False


class 锯子(PropComp, BaseProp):
    name = "锯子"
    brief = "这个道具在开枪前只能使用 1 次. 使下次开枪为实弹时伤害 +1."

    @classmethod
    def apply(cls, msg_manager, target):
        game, _, reply, _, _, _, modify = RegGameWork.get_index(msg_manager)
        if not modify.get("锯子", False):
            RegGameWork.create_prop_event(game, "锯子", "shoot")
            modify["锯子"] = True
            reply["info"].append("槍管被鋸斷.")
            return True
        reply["info"].append("槍管早已被鋸斷.")
        return False

    @classmethod
    def callback(cls, msg_manager, moment):
        game, _, _, tmp, _, _, modify = RegGameWork.get_index(msg_manager)
        if moment == "shoot":
            RegGameWork.create_prop_event(game, "锯子", "damage")
            tmp["dmg"] = modify["dmg"] + 1
            modify["锯子"] = False
        return True


class 邀请函(PropComp, BaseProp):
    name = "邀请函"
    brief = "使目标抽取 2 个道具, 并结束使用者回合."
    pool = ("手铐", "锯子", "红牛", "放大镜", "口红", "牛奶", "止疼药")

    @classmethod
    def apply(cls, msg_manager, target):
        game = msg_manager.val["game"]
        data, reply = game["data"], game["reply"]
        shooter = data["shooter"]
        RegGameWork.draw_prop(msg_manager, target, 2, cls.pool)
        RegGameWork.end_round(msg_manager)
        name = RegGameWork.get_name(game)
        if target == shooter:
            reply["info"].append(f"{name}將邀請函撕碎.")
        else:
            reply["info"].append(
                f"{name}邀請{RegGameWork.get_name(game, target)}參加宴會."
            )
        return True


class 花生(PropComp, BaseProp):
    name = "花生"
    brief = "装填 1 发空包弹, 并重新上膛."

    @classmethod
    def apply(cls, msg_manager, target):
        game = msg_manager.val["game"]
        game["data"]["ammo_blank"] += 1
        RegGameWork.bullet(msg_manager)
        name = RegGameWork.get_name(game)
        game["reply"]["info"].append(f"{name}裝入1发空包彈.")
        return True


class 巧克力(PropComp, BaseProp):
    name = "巧克力"
    brief = "装填 1 发实弹, 并重新上膛."

    @staticmethod
    def reply():
        return random.choice(
            (
                "酒心",
                "果仁",
                "果醬",
                "奶油",
                "焦糖",
                "咖啡",
                "抹茶",
                "香草",
                "芝士",
                "辣味",
                "慕斯",
                "奶油",
            )
        )

    @classmethod
    def apply(cls, msg_manager, target):
        game = msg_manager.val["game"]
        game["data"]["ammo_live"] += 1
        RegGameWork.bullet(msg_manager)
        game["reply"]["info"].append(f"{cls.reply()}巧克力被塞進彈倉.")
        return True


class 香烟(PropComp, BaseProp):
    name = "香烟"
    brief = "取出 1 发空包弹, 并重新上膛. 若弹仓内只有实弹, 则取出 1 发实弹."

    @classmethod
    def apply(cls, msg_manager, target):
        game = msg_manager.val["game"]
        data = game["data"]
        if data["ammo_blank"] > 0:
            data["ammo_blank"] -= 1
            bullet = "空包彈"
        else:
            data["ammo_live"] -= 1
            bullet = "實彈"
        RegGameWork.bullet(msg_manager)
        game["reply"]["info"].append(
            f"{RegGameWork.get_name(game)}扔掉香煙, 取出一發{bullet}."
        )
        return True


class 红牛(PropComp, BaseProp):
    name = "红牛"
    brief = "恢复目标 1 点HP."

    @staticmethod
    def reply():
        return random.choice(("胰島素", "白開水", "辣椒粉", "薯片", "益達", "紅牛?"))

    @classmethod
    def apply(cls, msg_manager, target):
        game = msg_manager.val["game"]
        data, reply = game["data"], game["reply"]
        RegGameWork.damage(msg_manager, target, -1)
        name = RegGameWork.get_name(game)
        if target == data["shooter"]:
            reply["info"].append(f"{name}將混著{cls.reply()}的紅牛將其一飲而盡.")
        else:
            reply["info"].append(
                f"{name}將混著{cls.reply()}的紅牛喂給{RegGameWork.get_name(game, target)}."
            )
        return True


class 放大镜(PropComp, BaseProp):
    name = "放大镜"
    brief = "这个道具在开枪前只能使用 1 次. 在开枪前持续显示下一发子弹的虚实."

    @classmethod
    def apply(cls, msg_manager, target):
        game = msg_manager.val["game"]
        data, reply = game["data"], game["reply"]
        modify = data["modify"]
        if not modify.get("放大镜"):
            modify["放大镜"] = True
            modify["ammo_show"] = True
            modify["bullet_show"] = True
            RegGameWork.create_prop_event(game, "放大镜", "shoot")
            reply["info"].append(
                f"{RegGameWork.get_name(game)}砸碎放大鏡, 發現槍膛裏是{'實彈' if data['bullet'] else '空包彈'}."
            )
            return True
        reply["info"].append("已用放大镜, 开枪前可查看子弹虚实.")
        return False

    @classmethod
    def callback(cls, msg_manager, moment):
        game = msg_manager.val["game"]
        modify = game["data"]["modify"]
        modify["放大镜"] = False
        modify["ammo_show"] = ModeComp.get(game["mode"]["name"]).modify.ammo_show
        modify["bullet_show"] = ModeComp.get(game["mode"]["name"]).modify.bullet_show
        return True


class 口红(PropComp, BaseProp):
    name = "口红"
    brief = "夺取目标口红和金币以外的 1 个道具, 或重新抽取 1 个道具."

    @staticmethod
    def reply():
        return random.choice(("塗上", "塗上", "吃下")) + random.choice(
            (
                "複古正紅",
                "牛血色",
                "姨媽紅",
                "梅子紅",
                "磚紅色",
                "楓葉紅",
                "車厘子紅",
                "酒紅色",
                "山楂紅",
                "朱砂紅",
                "元氣橙色",
                "珊瑚色",
                "西柚色",
                "南瓜色",
                "胡蘿蔔色",
                "髒橘色",
                "赤陶色",
                "焦糖色",
                "芒果色",
                "柿子色",
                "淺粉色",
                "桃粉色",
                "玫瑰色",
                "煙熏玫瑰",
                "豆沙紅",
                "幹枯玫瑰",
                "豆沙粉",
                "薔薇粉",
                "奶茶玫瑰",
                "蜜桃玫瑰",
                "五彩斑斓的黑",
                "顔色正在變幻?",
            )
        )

    @classmethod
    def apply(cls, msg_manager, target):
        game = msg_manager.val["game"]
        data, reply = game["data"], game["reply"]
        shooter = data["shooter"]
        name = RegGameWork.get_name(game)
        props_list = [
            prop
            for prop in data["players"][target]["props"]
            if prop not in ("口红", "金币")
        ]
        if target == shooter or not props_list:
            prop = random.choice(game["mode"]["props"]["pool"])
            reply["info"].append(f"{name}{cls.reply()}的口紅, 神明贈予{prop}.")
        else:
            prop = random.choice(props_list)
            target_name = RegGameWork.get_name(game, target)
            RegGameWork.remove_prop(game, target, prop)
            reply["info"].append(
                f"{name}給{target_name}{cls.reply()}的口紅, {target_name}以{prop}回贈."
            )
        RegGameWork.get_prop(game, shooter, prop)
        return True


class 扑克(PropComp, BaseProp):
    name = "扑克"
    brief = "反转子弹虚实, 并在效果期间隐藏弹仓."

    @staticmethod
    def reply():
        if random.randint(1, 54) > 2:
            suits = ("方片♦️", "梅花♣️", "红桃♥️", "黑桃♠️")
            ranks = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
            return random.choice(suits) + random.choice(ranks)
        else:
            return random.choice(["JOKER", "joker"])

    @classmethod
    def apply(cls, msg_manager, target):
        game = msg_manager.val["game"]
        data, reply = game["data"], game["reply"]
        modify = data["modify"]
        prop_event = data["prop_event"]
        if "扑克" not in prop_event["shoot"] + prop_event["reload"]:
            RegGameWork.create_prop_event(game, "扑克", ("shoot", "reload"))
        bullet = not data["bullet"]
        data["bullet"] = bullet
        if bullet:
            data["ammo_blank"] -= 1
            data["ammo_live"] += 1
        else:
            data["ammo_blank"] += 1
            data["ammo_live"] -= 1
        modify["扑克"] = True
        modify["ammo_show"] = False
        reply["info"].append(f"從牌堆抽到[{cls.reply()}], 命運已然改變.")
        return True

    @classmethod
    def callback(cls, msg_manager, moment):
        game = msg_manager.val["game"]
        data = game["data"]
        modify = data["modify"]
        prop_event = data["prop_event"]
        if moment == "shoot":
            prop_event["reload"].remove("扑克")
        elif moment == "reload":
            prop_event["shoot"].remove("扑克")
            game["reply"]["info"].append("迷霧被驅散了.")
        modify["ammo_show"] = ModeComp.get(game["mode"]["name"]).modify.ammo_show
        return True


class 转盘(PropComp, BaseProp):
    name = "转盘"
    brief = "以特殊比例重新装填弹仓."

    @staticmethod
    def reply():
        return "".join(
            random.choice(string.ascii_letters + string.digits + string.punctuation)
            for _ in range(8)
        )

    @classmethod
    def apply(cls, msg_manager, target):
        game = msg_manager.val["game"]
        data, reply = game["data"], game["reply"]
        ammo = random.randint(1, 6)
        ammo_blank = ammo - random.randint(1, ammo)
        ammo_live = ammo - ammo_blank
        data["ammo_live"], data["ammo_blank"] = ammo_live, ammo_blank
        RegGameWork.bullet(msg_manager)
        reply["info"].append(f"鏽迹斑斑的轉盤開始變換……現在是世界線[{cls.reply()}]")
        game["reply"]["note"]["ammo"] = f"彈仓: {ammo_live} / {ammo}"
        return True


class 牛奶(PropComp, BaseProp):
    name = "牛奶"
    brief = "使目标抽取 2 个道具, 其余赌徒抽取 1 个道具."
    pool = (
        "手铐",
        "锯子",
        "邀请函",
        "花生",
        "巧克力",
        "香烟",
        "红牛",
        "放大镜",
        "口红",
        "扑克",
        "转盘",
    )

    @staticmethod
    def reply():
        return (
            random.choice(
                (
                    "生鮮牛乳",
                    "酸奶",
                    "純牛奶",
                    "調味奶",
                    "煉乳",
                    "奶昔",
                    "奶酪",
                    "複原乳",
                    "濃縮牛乳",
                    "變質牛乳",
                    "冷凍牛乳",
                )
            )
            + ", 在暈眩中神明降下賜福."
        )

    @classmethod
    def apply(cls, msg_manager, target):
        game = msg_manager.val["game"]
        data, reply = game["data"], game["reply"]
        RegGameWork.draw_prop(msg_manager, target, 2, cls.pool)
        for pl in data["order"]:
            if pl != target:
                RegGameWork.draw_prop(msg_manager, pl, 1, cls.pool)
        name = RegGameWork.get_name(game)
        if target == data["shooter"]:
            reply["info"].append(f"{name}飲下{cls.reply()}")
        else:
            reply["info"].append(
                f"{name}讓{RegGameWork.get_name(game, target)}飲下{cls.reply()}"
            )
        return True


class 金币(PropComp, BaseProp):
    name = "金币"
    brief = "兑换任意 1 个未被ban的道具.\n#增加指令\n购买(道具名) //使用金币兑换道具."

    @classmethod
    def init(cls):
        prop_list = (prop for prop in PropComp.list() if prop != "金币")
        dictHelpDoc["恶赌 命令"] += "\n购买(道具名) //使用金币兑换道具."

        @commands.route("play", f"^(?:购买|購買) *({'|'.join(prop_list)})$")
        def purchase(plugin_event, Proc, msg_manager, groups):
            user_id, game = msg_manager.user_id, msg_manager.val["game"]
            data = game["data"]
            shooter = data["shooter"]
            if user_id != shooter:
                reply = msg_manager.msg_format(
                    "strMrGamblerTurn",
                    {"tGamblerName": RegGameWork.get_name(game, shooter)},
                )
                plugin_event.reply(reply)
                return
            if "金币" not in data["players"][user_id]["props"]:
                reply = msg_manager.msg_format(
                    "strMrGamblerNoProp", {"tPropName": "金币"}
                )
                plugin_event.reply(reply)
                return
            cls.purchase(game, user_id, groups[0])
            reply = RegGameWork.format_reply(game)
            plugin_event.reply(reply)
            return

    @staticmethod
    def reply():
        return random.choice(
            ("嶄新", "啞暗", "磨損", "變形", "鏽蝕", "斑駁", "鏤空", "黏膩", "沾血")
        )

    @classmethod
    def purchase(cls, game, user_id, prop):
        data = game["data"]
        if prop in game["mode"]["props"]["ban"]:
            game["reply"]["info"].append(f"{prop}被禁售了.")
            return
        pl_user = data["players"][user_id]
        props = pl_user["props"]
        props[props.index("金币")] = prop
        name = pl_user["name"]
        reply = f"{name}向自動販賣機投入一枚{cls.reply()}的金幣, " + (
            f"結果沒有任何反應, {name}將其砸爛，取出{prop}."
            if random.randint(1, 4) == 1
            else f"自動販賣機吐出{prop}."
        )
        game["reply"]["info"].append(reply)
        return


class 止疼药(PropComp, BaseProp):
    name = "止疼药"
    brief = "使目标在其回合结束前受到的伤害转变为等值的[神经麻痹]. 对自身使用时, 效果延长到下回合结束.\n[神经麻痹]回合结束时失去所有[神经麻痹]并受到等值的神经麻痹伤害."

    @classmethod
    def apply(cls, msg_manager, target):
        game, _, reply, _, _, shooter, modify = RegGameWork.get_index(msg_manager)
        comp = modify.setdefault("止疼药", [])
        if target in comp:
            reply["info"].append(f"{RegGameWork.get_name(game, target)}已服用止疼药.")
            return False
        comp.append(target)
        RegGameWork.create_prop_event(game, "止疼药", "damage")
        if target == shooter:
            RegGameWork.create_prop_event(game, "止疼药", "switch")
        else:
            RegGameWork.create_prop_event(game, "止疼药", "end_round")
        reply["info"].append(f"{RegGameWork.get_name(game, target)}服用止疼药.")
        return True

    @classmethod
    def callback(cls, msg_manager, moment):
        game, _, reply, tmp, _, shooter, modify = RegGameWork.get_index(msg_manager)
        comp = modify["止疼药"]
        if moment == "damage":
            target = tmp["target"]
            if target in comp and tmp["dmg_type"] == "shoot":
                dmg, tmp["dmg"] = tmp["dmg"], 0
                stacks_before = RegGameWork.get_effect_stacks(game, "神经麻痹", target)
                stacks_now = stacks_before + dmg
                EffectComp.give(msg_manager, "神经麻痹", target, dmg)
                modify["神经麻痹"][target]["final_attacker"] = tmp["murderer"]
                reply["info"].append(
                    f"{RegGameWork.get_name(game, target)}感到神经麻痹[{stacks_before}->{stacks_now}]."
                )
        elif moment == "end_round" and shooter in comp:
            comp.remove(shooter)
            RegGameWork.remove_prop_event(game, "止疼药", "damage")
            return True
        elif moment == "switch":
            RegGameWork.create_prop_event(game, "止疼药", "end_round")
            return True
        return False
