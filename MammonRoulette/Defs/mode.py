import random

from ..Core.cmop import ModeComp
from ..Core.work import GameWork


class BaseMode:
    name = ""
    brief = ""
    points = 0

    class seats:  # type: ignore
        default: int = 2
        max: int = 8
        min: int = 2

    seats: type = seats

    class props:  # type: ignore
        pool: list = []
        ban: list = []
        limit: int = 0

    props: type = props

    @classmethod
    def start(cls, game):
        pass

    @classmethod
    def join(cls, game, user_id):
        pass

    # 装弹
    @classmethod
    def reload(cls, game, **kwargs):
        pass

    # 开枪
    @classmethod
    def shoot(cls, game, **kwargs):
        pass

    # 受伤
    @classmethod
    def damage(cls, game, **kwargs):
        pass

    # 回合结束
    @classmethod
    def end_round(cls, game, **kwargs):
        pass

    # 换人
    @classmethod
    def switch(cls, game, **kwargs):
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
        "\n2. 回合开始时抽取 2 个道具."
    )
    points = 50

    class props:
        pool = ["手铐", "锯子", "花生", "巧克力", "香烟", "红牛", "邀请函", "放大镜"]
        ban = []
        limit = 6

    @classmethod
    def start(cls, game):
        for pl in game["order"][2:]:
            GameWork.prop_draw(game, pl, 1)
        GameWork.prop_draw(game, game["shooter"], 2)

    @classmethod
    def join(cls, game, user_id):
        game["players"][user_id]["hp"] = 4

    # 换人
    @classmethod
    def switch(cls, game, **kwargs):
        GameWork.prop_draw(game, game["shooter"], 2)


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
        ]
        ban = []
        limit = 16

    @classmethod
    def join(cls, game, user_id):
        pl = game["players"][user_id]
        if len(game["order"]) < 4:
            pl["hp"] = 5
        else:
            pl["hp"] = 6

    # 装弹
    @classmethod
    def reload(cls, game, **kwargs):
        for pl in game["order"]:
            GameWork.prop_draw(game, pl, 4)


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
    def start(cls, game):
        GameWork.prop_get(game, game["shooter"], "金币")

    @classmethod
    def join(cls, game, user_id):
        game["players"][user_id]["hp"] = 5

    # 换人
    @classmethod
    def switch(cls, game, **kwargs):
        GameWork.prop_draw(game, game["shooter"], 1)

    # 受伤
    @classmethod
    def damage(cls, game, **kwargs):
        target, dmg = kwargs["target"], kwargs["dmg"]
        comp = game["modify"].setdefault("金币", [])
        if target not in comp and game["players"][target]["hp"] - dmg <= 2:
            GameWork.prop_draw(game, target, 1)
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
        "\n2. 向自己开枪且为空弹时抽取 2 个道具;"
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
    def start(cls, game):
        for pl in game["order"][2:]:
            GameWork.prop_draw(game, pl, 2)
        GameWork.prop_draw(game, game["shooter"], 1)

    @classmethod
    def join(cls, game, user_id):
        game["players"][user_id]["hp"] = 5

    # 开枪
    @classmethod
    def shoot(cls, game, **kwargs):
        bullet = game["bullet"]
        if bullet and random.randint(1, 3) == 1:
            game["reply"]["brief"].append(f"伴隨七彩光芒，魔彈發射.")
            modify = game["modify"]
            modify["dmg"] = modify.get("dmg", 0) + 1
            modify["魔弹"] = True
        target = kwargs["target"]
        if target == game["shooter"] and not bullet:
            GameWork.prop_draw(game, target, 2)

    # 回合结束
    @classmethod
    def end_round(cls, game, **kwargs):
        modify = game["modify"]
        if modify.get("魔弹"):
            modify["魔弹"] = False
            modify["dmg"] = modify.get("dmg", 1) - 1


class 赌徒(ModeComp, BaseMode):
    name = "赌徒"
    brief = (
        "〈赏金〉40"
        "\n〈血量〉每名玩家5hp."
        "\n〈道具池〉(上限12)"
        "\n{手铐,锯子,邀请函,红牛,放大镜,口红,牛奶,金币}"
        "\n〔机制〕"
        "\n1. 游戏开始时, 所有玩家抽取 2 个道具;"
        "\n2. 向自己开枪且为空弹时抽取 3 个道具;"
        "\n3. 实弹有1/3的概率使伤害+1;"
        "\n4. 每次开枪有1/3的概率反转子弹虚实."
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

    @staticmethod
    def reply():
        if random.randint(1, 54) > 2:
            suits = ("方片♦️", "梅花♣️", "红桃♥️", "黑桃♠️")
            ranks = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
            return random.choice(suits) + random.choice(ranks)
        else:
            return random.choice(["JOKER", "joker"])

    @classmethod
    def start(cls, game):
        game["modify"]["ammo_hide"] = True
        for pl in game["order"]:
            GameWork.prop_draw(game, pl, 2)

    @classmethod
    def join(cls, game, user_id):
        game["players"][user_id]["hp"] = 5

    # 开枪
    @classmethod
    def shoot(cls, game, **kwargs):
        if random.randint(1, 3) == 1:
            game["reply"]["brief"].append(f"子彈擊穿突然出現的{cls.reply()}.")
            bullet = not game["bullet"]
            game["bullet"] = bullet
            game["ammo_blank"] += -1 if bullet else 1
            game["ammo_live"] += 1 if bullet else -1
        if game["bullet"] and random.randint(1, 3) == 1:
            game["reply"]["brief"].append(f"伴隨七彩光芒，魔彈發射.")
            modify = game["modify"]
            modify["dmg"] = modify.get("dmg", 0) + 1
            modify["魔弹"] = True
        target = kwargs["target"]
        if target == game["shooter"] and not game["bullet"]:
            GameWork.prop_draw(game, target, 3)

    # 回合结束
    @classmethod
    def end_round(cls, game, **kwargs):
        modify = game["modify"]
        modify["ammo_hide"] = True
        if modify.get("魔弹"):
            modify["魔弹"] = False
            modify["dmg"] = modify.get("dmg", 1) - 1
