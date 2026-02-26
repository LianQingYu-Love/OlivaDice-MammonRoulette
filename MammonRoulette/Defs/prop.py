import random
import string

from ..main import commands
from ..msgCustom import dictHelpDocTemp
from ..Core.cmop import PropComp
from ..Core.work import RegGameWork


class BaseProp:
    name = ""
    brief = ""

    @classmethod
    def init(cls):
        pass

    @classmethod
    def apply(cls, game, target) -> bool | None:
        return False

    @classmethod
    def callback(cls, game, event) -> bool | None:
        pass


class 手铐(PropComp, BaseProp):
    name = "手铐"
    brief = "使用者不可作为目标. 束缚目标行动 1 回合, 且在目标恢复行动前无法再次将其选为目标."

    @staticmethod
    def reply():
        return random.choice(("双手", "双手", "双手", "双腿"))

    @classmethod
    def apply(cls, game, target):
        if target == game["shooter"]:
            order = game["order"]
            target = order[(order.index(game["shooter"]) + 1) % len(order)]
        comp = game["modify"].setdefault("手铐", [])
        pl = game["players"][target]
        if target not in comp:
            game["reply"]["info"].append(f"{pl['name']}被銬住了{cls.reply()}.")
            comp.append(target)
            pl["actions"] -= 1
            RegGameWork.event(game, "手铐", "switch")
            return True
        game["reply"]["info"].append(f"{pl['name']}已經被铐住了.")
        return False

    @classmethod
    def callback(cls, game, event):
        modify = game["modify"]
        comp = modify["手铐"]
        shooter = game["shooter"]
        if shooter in comp:
            comp.remove(shooter)
            return True
        return False


class 锯子(PropComp, BaseProp):
    name = "锯子"
    brief = "这个道具在开枪前只能使用 1 次. 使下次开枪为实弹时伤害 +1."

    @classmethod
    def apply(cls, game, target):
        modify = game["modify"]
        if not modify.get("锯子", {}).get("ban"):
            game["reply"]["info"].append("槍管被鋸斷了.")
            modify["dmg"] = modify.get("dmg", 0) + 1
            modify["锯子"] = {"ban": True, "shoot": False}
            RegGameWork.event(game, "锯子", ("shoot", "end_round"))
            return True
        game["reply"]["info"].append("槍管早已被鋸斷.")
        return False

    @classmethod
    def callback(cls, game, event):
        modify = game["modify"]
        comp = modify["锯子"]
        if event == "shoot":
            comp["shoot"] = True
        elif comp["shoot"] and event == "end_round":
            modify["dmg"] = modify.get("dmg", 1) - 1
        comp["ban"] = False
        return True


class 邀请函(PropComp, BaseProp):
    name = "邀请函"
    brief = "使目标抽取 2 个道具, 并结束使用者回合."
    pool = ("手铐", "锯子", "红牛", "放大镜", "口红", "牛奶")

    @classmethod
    def apply(cls, game, target):
        name = RegGameWork.get_name(game)
        if target == game["shooter"]:
            game["reply"]["info"].append(f"{name}將邀請函撕碎.")
        else:
            game["reply"]["info"].append(
                f"{name}邀請{RegGameWork.get_name(game, target)}參加宴會."
            )
        RegGameWork.draw_prop(game, target, 2, cls.pool)
        RegGameWork.end_round(game)
        return True


class 花生(PropComp, BaseProp):
    name = "花生"
    brief = "装填 1 发空包弹, 并重新上膛."

    @classmethod
    def apply(cls, game, target):
        game["reply"]["info"].append("花生殼被塞進彈倉.")
        game["ammo_blank"] += 1
        RegGameWork.bullet(game)
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
    def apply(cls, game, target):
        game["reply"]["info"].append(f"{cls.reply()}巧克力被塞進彈倉.")
        game["ammo_live"] += 1
        RegGameWork.bullet(game)
        return True


class 香烟(PropComp, BaseProp):
    name = "香烟"
    brief = "取出 1 发空包弹, 并重新上膛. 若弹仓内只有实弹, 则取出 1 发实弹."

    @classmethod
    def apply(cls, game, target):
        ammo_blank = game["ammo_blank"]
        if ammo_blank > 0:
            game["ammo_blank"] -= 1
            bullet = "空包彈"
        else:
            game["ammo_live"] -= 1
            bullet = "實彈"
        game["reply"]["info"].append(
            f"{RegGameWork.get_name(game)}扔掉香煙, 取出一發{bullet}."
        )
        RegGameWork.bullet(game)
        return True


class 红牛(PropComp, BaseProp):
    name = "红牛"
    brief = "恢复目标 1 点HP."

    @staticmethod
    def reply():
        return random.choice(("胰島素", "白開水", "辣椒粉", "薯片", "益達", "紅牛?"))

    @classmethod
    def apply(cls, game, target):
        name = RegGameWork.get_name(game)
        if target == game["shooter"]:
            game["reply"]["info"].append(
                f"{name}將混著{cls.reply()}的紅牛將其一飲而盡."
            )
        else:
            game["reply"]["info"].append(
                f"{name}將混著{cls.reply()}的紅牛喂給{RegGameWork.get_name(game, target)}."
            )
        RegGameWork.damage(game, target, -1)
        return True


class 放大镜(PropComp, BaseProp):
    name = "放大镜"
    brief = "这个道具在开枪前只能使用 1 次. 在开枪前持续显示下一发子弹的虚实."

    @classmethod
    def apply(cls, game, target):
        modify = game["modify"]
        if not modify.get("放大镜"):
            game["reply"]["info"].append(
                f"{RegGameWork.get_name(game)}砸碎放大鏡, 發現槍膛裏是{'實彈' if game['bullet'] else '空包彈'}."
            )
            modify["放大镜"] = True
            modify["bullet_show"] = True
            modify["ammo_hide"] = False
            RegGameWork.event(game, "放大镜", "shoot")
            return True
        game["reply"]["info"].append("已用放大镜, 开枪前可查看子弹虚实.")
        return False

    @classmethod
    def callback(cls, game, event):
        modify = game["modify"]
        modify["放大镜"] = False
        modify["bullet_show"] = False
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
    def apply(cls, game, target):
        name = RegGameWork.get_name(game)
        props_list = [
            prop
            for prop in game["players"][target]["props"]
            if prop not in ("口红", "金币")
        ]
        if target == game["shooter"] or not props_list:
            prop = random.choice(game["props"]["pool"])
            game["reply"]["info"].append(f"{name}{cls.reply()}的口紅, 神明贈予{prop}.")
        else:
            prop = random.choice(props_list)
            target_name = RegGameWork.get_name(game, target)
            game["reply"]["info"].append(
                f"{name}給{target_name}{cls.reply()}的口紅, {target_name}以{prop}回贈."
            )
            RegGameWork.remove_prop(game, target, prop)
        RegGameWork.get_prop(game, game["shooter"], prop)
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
    def apply(cls, game, target):
        game["reply"]["info"].append(f"從牌堆抽到[{cls.reply()}], 命運已然改變.")
        modify = game["modify"]
        modify["扑克"] = True
        modify["ammo_hide"] = True
        callback = game["callback"]
        if "扑克" not in callback["shoot"] + callback["reload"]:
            RegGameWork.event(game, "扑克", ("shoot", "reload"))
        bullet = not game["bullet"]
        game["bullet"] = bullet
        if bullet:
            game["ammo_blank"] -= 1
            game["ammo_live"] += 1
        else:
            game["ammo_blank"] += 1
            game["ammo_live"] -= 1
        return True

    @classmethod
    def callback(cls, game, event):
        modify = game["modify"]
        modify["ammo_hide"] = False
        callback = game["callback"]
        if event == "shoot":
            callback["reload"].remove("扑克")
        elif event == "reload":
            game["reply"]["info"].append("霰彈槍的迷霧被驅散了.")
            callback["shoot"].remove("扑克")
        return True


class 转盘(PropComp, BaseProp):
    name = "转盘"
    brief = "以特殊比例重新装填弹仓."

    @classmethod
    def apply(cls, game, target):
        all_chars = string.ascii_letters + string.digits + string.punctuation
        gibberish = "".join(random.choice(all_chars) for _ in range(8))
        game["reply"]["info"].append(
            f"鏽迹斑斑的轉盤開始變換……現在是世界線[{gibberish}]"
        )
        ammo = random.randint(1, 6)
        ammo_blank = ammo - random.randint(1, ammo)
        ammo_live = ammo - ammo_blank
        game["ammo_live"] = ammo_live
        game["ammo_blank"] = ammo_blank
        RegGameWork.bullet(game)
        game["reply"]["ammo"] = f"彈仓: {ammo_live} / {ammo}"
        return True


class 牛奶(PropComp, BaseProp):
    name = "牛奶"
    brief = "使目标抽取 2 个道具, 其余恶魔抽取 1 个道具."
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
    def apply(cls, game, target):
        name = RegGameWork.get_name(game)
        if target == game["shooter"]:
            game["reply"]["info"].append(f"{name}飲下{cls.reply()}")
        else:
            game["reply"]["info"].append(
                f"{name}讓{RegGameWork.get_name(game, target)}飲下{cls.reply()}"
            )
        RegGameWork.draw_prop(game, target, 2, cls.pool)
        for pl in game["order"]:
            if pl != target:
                RegGameWork.draw_prop(game, pl, 1, cls.pool)
        return True


class 金币(PropComp, BaseProp):
    name = "金币"
    brief = "兑换任意 1 个未被ban的道具.\n#增加指令\n购买(道具名) //使用金币兑换道具."

    @classmethod
    def init(cls):
        prop_list = (prop for prop in PropComp.list() if prop != "金币")
        dictHelpDocTemp["恶赌 命令"] += "\n购买(道具名) //使用金币兑换道具."

        @commands.route("play", f"^(?:购买|購買) *({'|'.join(prop_list)})$")
        def purchase(plugin_event, Proc, msg_manager, groups):
            msg_manager.val["game_update"] = True
            user_id, game = msg_manager.user_id, msg_manager.val["game"]
            if game["shooter"] != user_id:
                reply = msg_manager.msg_format(
                    "strMrActionsError", {"gamblerName": RegGameWork.get_name(game)}
                )
                plugin_event.reply(reply)
                return False
            if "金币" not in game["players"][user_id]["props"]:
                reply = msg_manager.msg_format("strMrPropError", {"propName": "金币"})
                plugin_event.reply(reply)
                return False
            cls.purchase(game, user_id, groups[0])
            reply = RegGameWork.reply(game)
            plugin_event.reply(reply)
            return True

    @staticmethod
    def reply():
        return random.choice(
            ("嶄新", "啞暗", "磨損", "變形", "鏽蝕", "斑駁", "鏤空", "黏膩", "沾血")
        )

    @classmethod
    def purchase(cls, game, user_id, prop):
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
