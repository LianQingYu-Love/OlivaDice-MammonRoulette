# -*- encoding: utf-8 -*-
"""
@File      :    MammonRoulette/Defs/prop.py
@Author    :    lianqingyuYuri恋倾雨
@Contact   :    xinghu2408@foxmail.com
@License   :    AGPLv3
@Copyright :    (C) 2026 MammonRoulette
@Desc      :    None
"""

import random
import string

from ..main import commands
from ..msgCustom import dictHelpDoc
from ..Core.comp import ModeComp, PropComp, EffectComp
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
    def callback(cls, msg_manager, moment, prop_data) -> bool | None:
        pass

    @classmethod
    def unapply(cls, msg_manager, prop_data) -> bool | None:
        pass


class 手铐(PropComp, BaseProp):
    name = "手铐"
    brief = "不能将枪手选为目标. 束缚目标行动 1 回合, 且在目标恢复行动前无法将其再次选为目标."

    @staticmethod
    def reply():
        return random.choice(("双手", "双手", "双手", "双腿"))

    @classmethod
    def apply(cls, msg_manager, target):
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        # 默认目标为下一个玩家
        if target == shooter:
            target = order[(order.index(shooter) + 1) % len(order)]
        pl_target = players[target]
        if not RegGameWork.get_effect_stacks(game, "束缚", target):
            pl_target["actions"] -= 1
            EffectComp.give(msg_manager, "束缚", target)
            RegGameWork.reply_info(
                msg_manager, f"{pl_target['name']}被銬住了{cls.reply()}."
            )
            return True
        RegGameWork.reply_info(msg_manager, f"{pl_target['name']}已經被铐住了.")
        return False


class 锯子(PropComp, BaseProp):
    name = "锯子"
    brief = "每次开枪前只能使用 1 次. 下一发子弹若为实弹则伤害 +1."

    @classmethod
    def apply(cls, msg_manager, target):
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        if not RegGameWork.get_prop_data(game, prop_name=cls.name):
            prop_data = {"name": cls.name}
            RegGameWork.create_prop_event(msg_manager, prop_data)
            RegGameWork.reply_info(msg_manager, "槍管被鋸斷.")
            return True
        RegGameWork.reply_info(msg_manager, "槍管早已被鋸斷.")
        return False

    @classmethod
    def callback(cls, msg_manager, moment, prop_data):
        if moment != "shoot":
            return False
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        tmp["dmg"] = modify["dmg"] + 1
        return True


class 邀请函(PropComp, BaseProp):
    name = "邀请函"
    brief = "在特定道具池中, 使目标抽取 2 个道具, 并结束枪手回合."
    pool = ("手铐", "锯子", "红牛", "放大镜", "口红", "牛奶", "止疼药")

    @classmethod
    def apply(cls, msg_manager, target):
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        name = RegGameWork.get_name(game)
        RegGameWork.draw_prop(msg_manager, target, 2, cls.pool)
        RegGameWork.end_round(msg_manager)
        if target == shooter:
            RegGameWork.reply_info(msg_manager, f"{name}將邀請函撕碎.")
        else:
            RegGameWork.reply_info(
                msg_manager, f"{name}邀請{RegGameWork.get_name(game, target)}參加宴會."
            )
        return True


class 花生(PropComp, BaseProp):
    name = "花生"
    brief = "装填 1 发空包弹, 然后重新上膛."

    @classmethod
    def apply(cls, msg_manager, target):
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        data["ammo_blank"] += 1
        RegGameWork.bullet(msg_manager)
        name = RegGameWork.get_name(game)
        RegGameWork.reply_info(msg_manager, f"{name}裝入1发空包彈.")
        return True


class 巧克力(PropComp, BaseProp):
    name = "巧克力"
    brief = "装填 1 发实弹, 然后重新上膛."

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
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        data["ammo_live"] += 1
        RegGameWork.bullet(msg_manager)
        RegGameWork.reply_info(msg_manager, f"{cls.reply()}巧克力被塞進彈倉.")
        return True


class 香烟(PropComp, BaseProp):
    name = "香烟"
    brief = "取出 1 发空包弹, 然后重新上膛. 若弹仓内只有实弹, 则取出 1 发实弹."

    @classmethod
    def apply(cls, msg_manager, target):
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        if data["ammo_blank"] > 0:
            data["ammo_blank"] -= 1
            bullet = "空包彈"
        else:
            data["ammo_live"] -= 1
            bullet = "實彈"
        RegGameWork.bullet(msg_manager)
        RegGameWork.reply_info(
            msg_manager, f"{RegGameWork.get_name(game)}扔掉香煙, 取出一發{bullet}."
        )
        return True


class 红牛(PropComp, BaseProp):
    name = "红牛"
    brief = "使目标HP+1."

    @staticmethod
    def reply():
        return random.choice(("胰島素", "白開水", "辣椒粉", "薯片", "益達", "紅牛?"))

    @classmethod
    def apply(cls, msg_manager, target):
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        RegGameWork.damage(msg_manager, target, -1, shooter)
        name = RegGameWork.get_name(game)
        if target == shooter:
            RegGameWork.reply_info(
                msg_manager,
                f"{name}將混著{cls.reply()}的紅牛將其一飲而盡[hp {tmp['hp_before']}->{tmp['hp_now']}].",
            )
        else:
            RegGameWork.reply_info(
                msg_manager,
                f"{name}將混著{cls.reply()}的紅牛喂給{RegGameWork.get_name(game, target)}[hp {tmp['hp_before']}->{tmp['hp_now']}].",
            )
        return True


class 放大镜(PropComp, BaseProp):
    name = "放大镜"
    brief = "每次开枪前只能使用 1 次. 在开枪前持续显示下一发子弹的虚实."

    @classmethod
    def apply(cls, msg_manager, target):
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        if not RegGameWork.get_prop_data(game, prop_name=cls.name):
            prop_data = {"name": cls.name}
            modify["ammo_show"] = True
            modify["bullet_show"] = True
            RegGameWork.create_prop_event(msg_manager, prop_data)
            RegGameWork.reply_info(
                msg_manager,
                f"{RegGameWork.get_name(game)}砸碎放大鏡, 發現槍膛裏是{'實彈' if bullet else '空包彈'}.",
            )
            return True
        RegGameWork.reply_info(msg_manager, "已用放大镜, 开枪前可查看子弹虚实.")
        return False

    @classmethod
    def callback(cls, msg_manager, moment, prop_data):
        if moment != "shoot":
            return False
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
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
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        name = RegGameWork.get_name(game)
        props_list = [
            prop
            for prop in data["players"][target]["props"]
            if prop not in ("口红", "金币")
        ]
        if target == shooter or not props_list:
            prop = random.choice(game["mode"]["props"]["pool"])
            RegGameWork.reply_info(
                msg_manager, f"{name}{cls.reply()}的口紅, 神明贈予{prop}."
            )
        else:
            prop = random.choice(props_list)
            target_name = RegGameWork.get_name(game, target)
            RegGameWork.remove_prop(game, target, prop)
            RegGameWork.reply_info(
                msg_manager,
                f"{name}給{target_name}{cls.reply()}的口紅, {target_name}以{prop}回贈.",
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
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        if not RegGameWork.get_prop_data(game, prop_name=cls.name):
            prop_data = {"name": cls.name}
            RegGameWork.create_prop_event(msg_manager, prop_data)
        data["bullet"] = not bullet
        if bullet:
            data["ammo_blank"] += 1
            data["ammo_live"] -= 1
        else:
            data["ammo_blank"] -= 1
            data["ammo_live"] += 1
        modify["ammo_show"] = False
        RegGameWork.reply_info(msg_manager, f"從牌堆抽到[{cls.reply()}], 命運已然改變.")
        return True

    @classmethod
    def callback(cls, msg_manager, moment, prop_data):
        if not moment in ["shoot", "reload"]:
            return False
        cls.unapply(msg_manager, prop_data)
        return True

    @classmethod
    def unapply(cls, msg_manager, prop_data):
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        RegGameWork.reply_info(msg_manager, "迷霧被驅散了.")
        modify["ammo_show"] = ModeComp.get(game["mode"]["name"]).modify.ammo_show
        return


class 转盘(PropComp, BaseProp):
    name = "转盘"
    brief = "以特殊比例重新装填弹仓."
    clear_prop = ["扑克"]

    @staticmethod
    def reply():
        return "".join(
            random.choice(string.ascii_letters + string.digits + string.punctuation)
            for _ in range(8)
        )

    @classmethod
    def apply(cls, msg_manager, target):
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        ammo = random.randint(1, 6)
        ammo_blank = ammo - random.randint(1, ammo)
        ammo_live = ammo - ammo_blank
        data["ammo_live"], data["ammo_blank"] = ammo_live, ammo_blank
        RegGameWork.bullet(msg_manager)
        for clear_prop in cls.clear_prop:
            prop_data = RegGameWork.get_prop_data(game, prop_name=clear_prop)
            if prop_data:
                RegGameWork.remove_prop_event(msg_manager, prop_data[0]["id"])
        RegGameWork.reply_info(
            msg_manager, f"鏽迹斑斑的轉盤開始變換……現在是世界線[{cls.reply()}]"
        )
        reply["note"]["ammo"] = True
        return True


class 牛奶(PropComp, BaseProp):
    name = "牛奶"
    brief = "在特定道具池中, 使目标抽取 2 个道具, 其余赌徒抽取 1 个道具."
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
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        RegGameWork.draw_prop(msg_manager, target, 2, cls.pool)
        for pl in order:
            if pl != target:
                RegGameWork.draw_prop(msg_manager, pl, 1, cls.pool)
        name = RegGameWork.get_name(game)
        if target == shooter:
            RegGameWork.reply_info(msg_manager, f"{name}飲下{cls.reply()}")
        else:
            RegGameWork.reply_info(
                msg_manager,
                f"{name}讓{RegGameWork.get_name(game, target)}飲下{cls.reply()}",
            )
        return True


class 金币(PropComp, BaseProp):
    name = "金币"
    brief = (
        "兑换任意 1 个未被ban的道具, 部分道具兑换后将直接使用. 增加指令: 购买(道具名)."
    )
    direct_use = ["锯子", "花生", "巧克力", "香烟", "放大镜", "扑克", "转盘", "牛奶"]

    @staticmethod
    def reply():
        return random.choice(
            ("嶄新", "啞暗", "磨損", "變形", "鏽蝕", "斑駁", "鏤空", "黏膩", "沾血")
        )

    @classmethod
    def init(cls):
        prop_list = (prop for prop in PropComp.list() if prop != cls.name)
        dictHelpDoc["恶赌 命令"] += "\n购买(道具名) //使用金币兑换道具."

        @commands.route("play", f"^(?:购买|購買) *({'|'.join(prop_list)})$")
        def purchase(plugin_event, Proc, msg_manager, groups):
            user_id = msg_manager.user_id
            game, data, reply, tmp, modify, players, order, shooter, bullet = (
                RegGameWork.get_index(msg_manager)
            )
            # 检查是否是玩家回合
            if user_id != shooter:
                msg_reply = msg_manager.msg_format(
                    "strMrGamblerTurn",
                    {"tGamblerName": RegGameWork.get_name(game, shooter)},
                )
                plugin_event.reply(msg_reply)
                return
            # 检查是否持有金币
            if cls.name not in players[user_id]["props"]:
                msg_reply = msg_manager.msg_format(
                    "strMrGamblerNoProp", {"tPropName": cls.name}
                )
                plugin_event.reply(msg_reply)
                return
            # cls.purchase(msg_manager, user_id, groups[0])
            prop = groups[0]
            # 检查道具是否被禁售
            if prop in game["mode"]["props"]["ban"]:
                RegGameWork.reply_info(msg_manager, f"{prop}被禁售了.")
                msg_reply = RegGameWork.format_reply(msg_manager)
                plugin_event.reply(msg_reply)
                return
            # 兑换道具
            pl_user = players[user_id]
            props = pl_user["props"]
            props[props.index(cls.name)] = prop
            name = pl_user["name"]
            RegGameWork.reply_info(
                msg_manager,
                f"{name}向自動販賣機投入一枚{cls.reply()}的金幣, "
                + (
                    f"結果沒有任何反應, {name}將其砸爛，取出{prop}."
                    if random.randint(1, 4) == 1
                    else f"自動販賣機吐出{prop}."
                ),
            )
            # 部分道具将直接使用
            if prop in cls.direct_use:
                if PropComp.use(msg_manager, prop, user_id):
                    RegGameWork.remove_prop(game, user_id, prop)
            msg_reply = RegGameWork.format_reply(msg_manager)
            plugin_event.reply(msg_reply)
            return


class 止疼药(PropComp, BaseProp):
    name = "止疼药"
    brief = "使目标在其回合结束前受到的枪击伤害转变为等值的神经麻痹. 对自身使用时, 效果延长到下回合结束."

    @classmethod
    def apply(cls, msg_manager, target):
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        if RegGameWork.get_effect_stacks(game, "神经麻痹", target):
            RegGameWork.reply_info(
                msg_manager, f"{RegGameWork.get_name(game, target)}已服用止疼药."
            )
            return False
        EffectComp.give(msg_manager, "神经麻痹", target, 0)
        RegGameWork.reply_info(
            msg_manager, f"{RegGameWork.get_name(game, target)}服用止疼药."
        )
        return True


class 烟花(PropComp, BaseProp):
    name = "烟花"
    brief = "所有赌徒各有1/2的概率HP-1. 每杀死一名赌徒, 重新生效一次, 且概率提高至2/3. 每生效一次, 所有赌徒抽取 1 个道具."

    @classmethod
    def apply(cls, msg_manager, target) -> bool | None:
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        msg_reply = f"{RegGameWork.get_name(game, target)}燃放煙花, 天空變得五彩斑斕."
        RegGameWork.reply_info(msg_manager, msg_reply)
        prop_data = {"name": cls.name, "data": {"reactivation": 0, "draws": 1}}
        RegGameWork.create_prop_event(msg_manager, prop_data)
        tmp["check_over"] = False
        order_before = order.copy()
        for pl in order_before:
            tmp[f"{pl}_hp_before"], tmp[f"{pl}_hp_now"] = (
                players[pl]["hp"],
                players[pl]["hp"],
            )
            if random.randint(1, 2) == 1:
                RegGameWork.damage(msg_manager, pl, 1, shooter)
                tmp[f"{pl}_hp_now"] = tmp["hp_now"]
        cls.explosion(msg_manager, order_before)
        RegGameWork.remove_prop_event(msg_manager, prop_name=cls.name)
        tmp["check_over"] = True
        situation = [
            f"{RegGameWork.get_name(game, pl)}[hp {tmp[f'{pl}_hp_before']}->{tmp[f'{pl}_hp_now']}]."
            for pl in order_before
            if tmp[f"{pl}_hp_before"] != tmp[f"{pl}_hp_now"]
        ]
        situation_str = "\n".join(situation)
        if not RegGameWork.is_over(msg_manager):
            RegGameWork.reply_info(msg_manager, situation_str)
            draws = prop_data["data"]["draws"]
            for pl in order:
                RegGameWork.draw_prop(msg_manager, pl, draws)
        return True

    @classmethod
    def callback(cls, msg_manager, moment, prop_data):
        if moment != "dead":
            return False
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        prop_data = RegGameWork.get_prop_data(game, prop_name=cls.name)[0]
        prop_data["data"]["reactivation"] += 1
        prop_data["data"]["draws"] += 1
        return False

    @classmethod
    def explosion(cls, msg_manager, order_before):
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        prop_data = RegGameWork.get_prop_data(game, prop_name=cls.name)[0]
        while prop_data["data"]["reactivation"] > 0:
            prop_data["data"]["reactivation"] -= 1
            for pl in order_before:
                if random.randint(1, 3) != 3:
                    RegGameWork.damage(msg_manager, pl, 1, shooter)
                    tmp[f"{pl}_hp_now"] = tmp["hp_now"]
        return
