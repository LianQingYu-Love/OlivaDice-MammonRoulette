# -*- encoding: utf-8 -*-
"""
@File      :    MammonRoulette/Defs/mode.py
@Author    :    lianqingyuYuri恋倾雨
@Contact   :    xinghu2408@foxmail.com
@License   :    AGPLv3
@Copyright :    (C) 2026 MammonRoulette
@Desc      :    None
"""

import random

from ..Core.cmop import ModeComp
from ..Core.work import RegGameWork


class BaseMode:
    name = ""
    brief = ""
    points = 0

    class _seats:
        default: int = 2
        max: int = 8
        min: int = 2

    seats: type = _seats

    class _props:
        pool: list = []
        ban: list = []
        limit: int = 0

    props: type = _props

    class _modify:
        dmg: int = 1
        ammo_show: bool = True
        bullet_show: bool = False

    modify: type = _modify

    @classmethod
    def init(cls):
        pass

    @classmethod
    def start(cls, msg_manager):
        pass

    @classmethod
    def join(cls, msg_manager, user_id):
        pass

    # 装弹
    @classmethod
    def reload(cls, msg_manager):
        pass

    # 开枪
    @classmethod
    def shoot(cls, msg_manager):
        pass

    # 受伤
    @classmethod
    def damage(cls, msg_manager):
        pass

    # 死亡
    @classmethod
    def dead(cls, msg_manager):
        pass

    # 回合结束
    @classmethod
    def end_round(cls, msg_manager):
        pass

    # 换人
    @classmethod
    def switch(cls, msg_manager):
        pass


class 经典(ModeComp, BaseMode):
    name = "经典"
    brief = (
        "〈赏金〉50"
        "\n〈血量〉每名玩家4hp."
        "\n〈道具池〉(上限6)"
        "\n{手铐,锯子,花生,巧克力,香烟,红牛,邀请函,放大镜}"
        "\n〔机制〕 "
        "\n1. 游戏开始时, 首发玩家抽取 2 个道具, 非首发玩家抽取 1 个道具;"
        "\n2. 玩家回合开始时抽取 2 个道具."
    )
    points = 50

    class props:
        pool = ["手铐", "锯子", "花生", "巧克力", "香烟", "红牛", "邀请函", "放大镜"]
        ban = []
        limit = 6

    @classmethod
    def start(cls, msg_manager):
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        for pl in order[2:]:
            RegGameWork.draw_prop(msg_manager, pl, 1)
        RegGameWork.draw_prop(msg_manager, shooter, 2)

    @classmethod
    def join(cls, msg_manager, user_id):
        msg_manager.val["game"]["data"]["players"][user_id]["hp"] = 4

    # 换人
    @classmethod
    def switch(cls, msg_manager):
        RegGameWork.draw_prop(
            msg_manager, msg_manager.val["game"]["data"]["shooter"], 2
        )


class 道具(ModeComp, BaseMode):
    name = "道具"
    brief = (
        "〈赏金〉40"
        "\n〈血量〉前3名玩家5hp, 其余玩家6hp."
        "\n〈道具池〉(上限16)"
        "\n{手铐,锯子,邀请函,花生,巧克力,香烟,红牛,放大镜,口红,扑克,转盘,牛奶}"
        "\n〔机制〕"
        "\n1. 装弹时所有玩家抽取 4 个道具."
    )
    points = 40

    class props:
        pool = [
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
            "牛奶",
            "止疼药",
        ]
        ban = []
        limit = 16

    @classmethod
    def join(cls, msg_manager, user_id):
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        players[user_id]["hp"] = 5 if len(order) < 4 else 6

    # 装弹
    @classmethod
    def reload(cls, msg_manager):
        for pl in msg_manager.val["game"]["data"]["order"]:
            RegGameWork.draw_prop(msg_manager, pl, 4)


class 金币(ModeComp, BaseMode):
    name = "金币"
    brief = (
        "〈赏金〉60"
        "\n〈血量〉每名玩家5hp."
        "\n〈道具池(上限12)〉{金币}"
        "\n〔机制〕"
        "\n1. 回合开始时获得 1 枚金币;"
        "\n2. 玩家血量首次低至 2 时, 获得 1 枚金币."
    )
    points = 60

    class props:
        pool = ["金币"]
        ban = []
        limit = 12

    @classmethod
    def start(cls, msg_manager):
        RegGameWork.draw_prop(
            msg_manager, msg_manager.val["game"]["data"]["shooter"], 1
        )

    @classmethod
    def join(cls, msg_manager, user_id):
        msg_manager.val["game"]["data"]["players"][user_id]["hp"] = 5

    # 换人
    @classmethod
    def switch(cls, msg_manager):
        RegGameWork.draw_prop(
            msg_manager, msg_manager.val["game"]["data"]["shooter"], 1
        )

    # 受伤
    @classmethod
    def damage(cls, msg_manager):
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        target, dmg = tmp["target"], tmp["dmg"]
        comp = modify.setdefault("金币", [])
        if target not in comp and players[target]["hp"] - dmg <= 2:
            if RegGameWork.get_prop(game, target, "金币"):
                reply["info"].append(
                    f"金光乍現！一枚金幣落入{RegGameWork.get_name(game,target)}手中."
                )
            else:
                reply["info"].append(
                    f"金光乍現！一枚金幣落入{RegGameWork.get_name(game,target)}手中, 但不慎滑落."
                )
            comp.append(target)


class 勇者(ModeComp, BaseMode):
    name = "勇者"
    brief = (
        "〈赏金〉40"
        "\n〈血量〉每名玩家5hp."
        "\n〈道具池〉(上限12)"
        "\n{手铐,锯子,邀请函,花生,巧克力,香烟,红牛,放大镜,口红,扑克,转盘,牛奶,金币}"
        "\n〔机制〕"
        "\n1. 游戏开始时, 首发玩家抽取 1 个道具, 非首发玩家抽取 2 个道具."
        "\n2. 向自己开枪且为空包弹时抽取 2 个道具;"
        "\n3. 实弹有1/3的概率使伤害+1."
    )
    points = 40

    class props:
        pool = [
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
            "牛奶",
            "金币",
        ]
        ban = []
        limit = 12

    @classmethod
    def start(cls, msg_manager):
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        for pl in order:
            RegGameWork.draw_prop(msg_manager, pl, 2)
        RegGameWork.draw_prop(msg_manager, shooter, 1)

    @classmethod
    def join(cls, msg_manager, user_id):
        msg_manager.val["game"]["data"]["players"][user_id]["hp"] = 5

    # 开枪
    @classmethod
    def shoot(cls, msg_manager):
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        if bullet and random.randint(1, 3) == 1:
            tmp["dmg"] += 1
            reply["info"].append(f"伴隨七彩光芒，魔彈發射.")
        target, is_attack_me = tmp["target"], tmp["is_attack_me"]
        if is_attack_me and not bullet:
            RegGameWork.draw_prop(msg_manager, target, 2)


class 赌徒(ModeComp, BaseMode):
    name = "赌徒"
    brief = (
        "〈赏金〉40"
        "\n〈血量〉每名玩家5hp."
        "\n〈道具池〉(上限12)"
        "\n{手铐,锯子,邀请函,红牛,放大镜,口红,牛奶,金币}"
        "\n〔机制〕"
        "\n1. 游戏开始时, 所有玩家抽取 2 个道具;"
        "\n2. 向自己开枪且为空包弹时抽取 3 个道具;"
        "\n3. 每次开枪有1/3的概率反转子弹虚实;"
        "\n4. 实弹有1/3的概率使伤害+1;"
        "\n5. 不会正常显示弹药数量."
    )
    points = 40

    class props:
        pool = [
            "手铐",
            "锯子",
            "邀请函",
            "红牛",
            "放大镜",
            "口红",
            "牛奶",
            "金币",
        ]
        ban = []
        limit = 12

    class modify:
        ammo_show = False

    @staticmethod
    def reply():
        if random.randint(1, 54) > 2:
            suits = ("方片♦️", "梅花♣️", "红桃♥️", "黑桃♠️")
            ranks = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
            return random.choice(suits) + random.choice(ranks)
        else:
            return random.choice(["JOKER", "joker"])

    @classmethod
    def start(cls, msg_manager):
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        modify["ammo_hide"] = True
        for pl in order:
            RegGameWork.draw_prop(msg_manager, pl, 2)

    @classmethod
    def join(cls, msg_manager, user_id):
        msg_manager.val["game"]["data"]["players"][user_id]["hp"] = 5

    # 开枪
    @classmethod
    def shoot(cls, msg_manager):
        game, data, reply, tmp, modify, players, order, shooter, bullet = (
            RegGameWork.get_index(msg_manager)
        )
        target, is_attack_me = tmp["target"], tmp["is_attack_me"]
        if is_attack_me and not bullet:
            RegGameWork.draw_prop(msg_manager, target, 3)
        if random.randint(1, 3) == 1:
            data["bullet"] = not bullet
            data["ammo_blank"] += -1 if bullet else 1
            data["ammo_live"] += 1 if bullet else -1
            reply["info"].append(f"子彈擊穿突然出現的{cls.reply()}.")
        if data["bullet"] and random.randint(1, 3) == 1:
            tmp["dmg"] += 1
            reply["info"].append(f"伴隨七彩光芒，魔彈發射.")
