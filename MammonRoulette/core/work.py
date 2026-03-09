import random

from AmorLib import DataBase, STRING_ROW

from .cmop import ModeComp, PropComp
from .. import DB_PATH


class RegGameWork:
    @staticmethod
    def get_name(game, user_id: str | None = None):  # 获取玩家昵称
        data = game["data"]
        if not user_id:
            user_id = data["shooter"]
        return data["players"][user_id]["name"]

    @staticmethod
    def format_reply(game):  # 格式化回复消息
        reply = game["reply"]
        if not reply["only"]:
            info, note = reply["info"], reply["note"]
            extra = [note[key] for key in ["ammo", "shooter"] if note[key]]
            if extra:
                info.extend(["▁▁▁▁▁▁▁▁▁▁▁▁▁▁"] + extra)
            msg = "\n".join(info)
        else:
            msg = reply["only"]
        reply.clear()
        return msg

    # region 事件
    @staticmethod
    def create_prop_event(game, callback, moments: STRING_ROW | str):
        moments = (moments,) if type(moments) == str else moments
        for moment in moments:
            game["data"]["prop_event"][moment].append(callback)

    @staticmethod
    def handle_event(game, moment, **kwargs):
        game["tmp"].update(kwargs)
        prop_event = game["data"]["prop_event"][moment]
        for prop in prop_event:
            if PropComp.trigger(game, prop, moment):
                prop_event.remove(prop)
        ModeComp.trigger(game, moment)

    # endregion
    # region 道具
    @staticmethod
    def get_prop(game, user_id, prop):  # 获取道具
        mode_props = game["mode"]["props"]
        pl_props = game["data"]["players"][user_id]["props"]
        if len(pl_props) >= mode_props["limit"]:
            return False
        elif prop in mode_props["ban"]:
            prop = random.choice(mode_props["pool"])
        pl_props.append(prop)
        return True

    @staticmethod
    def remove_prop(game, user_id, prop):  # 删除道具
        pl_props = game["data"]["players"][user_id]["props"]
        if prop not in pl_props:
            return False
        pl_props.remove(prop)
        return True

    @classmethod
    def draw_prop(cls, game, user_id, count, prop_pool=None):  # 抽取道具
        prop_pool = prop_pool or game["mode"]["props"]["pool"]
        draw_props = []
        for _ in range(count):
            prop = random.choice(prop_pool)
            if not cls.get_prop(game, user_id, prop):
                break
            draw_props.append(prop)
        if draw_props:
            game["reply"]["info"].append(
                f"{game['players'][user_id]['name']}抽取: {'、'.join(draw_props)}"
            )
        return

    # endregion
    # region action
    @classmethod
    def bullet(cls, game):  # 刷新子弹
        data = game["data"]
        if data["ammo_live"] < 1:
            ammo_live, ammo_blank = cls.reload(game)
        else:
            ammo_live, ammo_blank = game["ammo_live"], game["ammo_blank"]
        ammo = ammo_live + ammo_blank
        data["bullet"] = random.randint(1, ammo) > ammo_blank

        modify = data["modify"]
        ammo_reply = []
        if modify["ammo_show"]:
            ammo_reply.append(f"彈仓: {ammo_live} / {ammo}")
        if modify["bullet_show"]:
            ammo_reply.append(f"當前子彈: {'實彈' if data['bullet'] else '空包彈'}")
        game["reply"]["note"]["ammo"] = "\n".join(ammo_reply)
        return

    @classmethod
    def reload(cls, game):  # 装弹
        data = game["data"]
        cls.handle_event(game, "reload")
        ammo_live, ammo_blank = random.randint(1, 4), random.randint(1, 4)
        data["ammo_live"], data["ammo_blank"] = ammo_live, ammo_blank
        game["reply"]["info"].append("彈藥耗盡，重新裝填中……")
        return ammo_live, ammo_blank

    @classmethod
    def shoot(cls, game, target):  # 开枪
        data, reply, tmp = game["data"], game["reply"], game["tmp"]
        is_attack_me = target == data["shooter"]
        cls.handle_event(game, "shoot", target=target, is_attack_me=is_attack_me)
        target = tmp["target"]
        pl_target, pl_shooter = (
            data["players"][target],
            data["players"][data["shooter"]],
        )
        if data["bullet"]:
            hp_before = pl_target["hp"]
            cls.damage(game, target, data["modify"]["dmg"])
            hp_now = pl_target["hp"]
            data["ammo_live"] -= 1
            reply["info"].append(
                f"“嘭！”{pl_target['name']}被崩倒在地[hp {hp_before}->{hp_now}]."
            )
        else:
            data["ammo_blank"] -= 1
            if tmp["is_attack_me"]:
                pl_shooter["actions"] += 1
            reply["info"].append("“咔哒——”是空彈……")
        cls.bullet(game)
        cls.end_round(game)
        return

    @classmethod
    def damage(cls, game, target, dmg):  # 受伤
        data, reply = game["data"], game["reply"]
        cls.handle_event(game, "damage", target=target, dmg=dmg)
        target, dmg = game["tmp"]["target"], game["tmp"]["dmg"]
        pl_target, pl_shooter = (
            data["players"][target],
            data["players"][data["shooter"]],
        )
        name = pl_target["name"]
        pl_target["hp"] -= dmg
        if pl_target["hp"] <= 0:
            if game["tmp"]["is_attack_me"]:
                pl_target["suicide"] = True
                reply["info"].append(f"{name}自殺了……")
            else:
                pl_shooter["kills"] += 1
                pl_target["suicide"] = False
                reply["info"].append(f"{name}死於他手.")
            data["order"].remove(target)
        return

    @classmethod
    def end_round(cls, game):  # 回合结束
        data = game["data"]
        order = data["order"]
        if len(order) > 1:
            cls.handle_event(game, "end_round")
            pc_shooter = data["players"][data["shooter"]]
            pc_shooter["actions"] -= 1
            if pc_shooter["actions"] < 1:
                cls.switch(game)
        else:
            name = cls.get_name(game, order[0])
            cls.over(game)
            game.update({"reply": {"only": f"{name}用鮮血爲這場生死對局畫上句號."}})
        return

    @classmethod
    def switch(cls, game):  # 换人
        data = game["data"]
        order, shooter = data["order"], data["shooter"]
        for _ in range(game["seats"] * 10):
            shooter = order[(order.index(shooter) + 1) % len(order)]
            pc_shooter = data["players"][shooter]
            pc_shooter["actions"] += 1
            if pc_shooter["actions"] > 0:
                break
        if shooter != data["shooter"]:
            data["shooter"] = shooter
            pc_shooter = data["players"][shooter]
            game["reply"]["shooter"] = f"現在是{pc_shooter['name']}的回合。"
            cls.handle_event(game, "switch")
        return

    @classmethod
    def over(cls, game):  # 结算
        data = game["data"]
        players = data["players"]
        with DataBase(DB_PATH) as db:
            for pl in players.keys():
                pl_target = players[pl]
                mult = pl_target["points_mult"] + pl_target["kills"]
                if pl not in data["order"]:
                    mult -= 1
                    wl = "losses"
                else:
                    mult += 1
                    wl = "wins"
                db.update(
                    "gambler",
                    {
                        "points": game["mode"]["points"] * mult,
                        "kills": pl_target["kills"],
                        "suicide": 1 if pl_target["suicide"] else 0,
                        "surrender": 1 if pl_target["surrender"] else 0,
                        wl: 1,
                    },
                    "user_id = ?",
                    pl,
                    increment=("points", "kills", "suicide", wl),
                )
        game.clear()
        return

    # endregion
