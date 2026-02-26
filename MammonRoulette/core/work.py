import random

from AmorLib import DataBase, STRING_ROW

from .cmop import ModeComp, PropComp
from .. import DB_PATH


class RegGameWork:
    # 消息
    @staticmethod
    def reply(game):
        reply = game["reply"]
        msg = reply["over"]
        if not msg:
            info, ammo, shooter = reply["info"], reply["ammo"], reply["shooter"]
            extra = []
            if ammo:
                extra.append(ammo)
            if shooter:
                extra.append(shooter)
            if extra:
                info.extend(["▁▁▁▁▁▁▁▁▁▁▁▁▁▁"] + extra)
            msg = "\n".join(info)
            reply.update({"info": [], "ammo": "", "shooter": ""})
        return msg

    # 名字
    @staticmethod
    def get_name(game, target=None):
        pls = game["players"]
        if target:
            return pls[target]["name"]
        return pls[game["shooter"]]["name"]

    # region prop
    # 抽取道具
    @classmethod
    def draw_prop(cls, game, target, count, pool=None):
        pool = pool or game["props"]["pool"]
        prop_list = []
        for _ in range(count):
            prop = random.choice(pool)
            if not cls.get_prop(game, target, prop):
                break
            prop_list.append(prop)
        if prop_list:
            game["reply"]["info"].append(
                f"{game['players'][target]['name']}得到: {'、'.join(prop_list)}"
            )
        return

    # 删除道具
    @staticmethod
    def remove_prop(game, target, prop):
        pl_props = game["players"][target]["props"]
        if prop in pl_props:
            pl_props.remove(prop)
            return True
        return False

    # 获取道具
    @staticmethod
    def get_prop(game, target, prop):
        pl_props = game["players"][target]["props"]
        if len(pl_props) >= game["props"]["limit"]:
            return False
        elif prop in game["props"]["ban"]:
            prop = random.choice(game["props"]["pool"])
        pl_props.append(prop)
        return True

    # endregion
    # region event
    # 添加事件
    @staticmethod
    def event(game, prop, event_list: STRING_ROW | str):
        if type(event_list) == str:
            event_list = (event_list,)
        for event in set(event_list):
            game["callback"][event].append(prop)

    # 事件触发器
    @staticmethod
    def trigger(game, event, **kwargs):
        trigger = game["callback"][event]
        for prop in trigger:
            if PropComp.trigger(game, event, prop):
                trigger.remove(prop)
        ModeComp.trigger(game, game["mode"], event, **kwargs)

    # endregion
    # region action
    # 刷新子弹
    @classmethod
    def bullet(cls, game):
        if game["ammo_live"] < 1:
            ammo_live, ammo_blank = cls.reload(game)
        else:
            ammo_live, ammo_blank = game["ammo_live"], game["ammo_blank"]
        ammo = ammo_live + ammo_blank
        bullet = random.randint(1, ammo) > ammo_blank
        game["bullet"] = bullet

        ammo_info = []
        if not game["modify"].get("ammo_hide", False):
            ammo_info.append(f"彈仓: {ammo_live} / {ammo_live+ammo_blank}")
        if game["modify"].get("bullet_show"):
            ammo_info.append(f"當前子彈: {'實彈' if game['bullet'] else '空包彈'}")
        game["reply"]["ammo"] = "\n".join(ammo_info)
        return

    # 装弹
    @classmethod
    def reload(cls, game):
        cls.trigger(game, "reload")
        ammo_live, ammo_blank = random.randint(1, 4), random.randint(1, 4)
        game["ammo_live"] = ammo_live
        game["ammo_blank"] = ammo_blank
        game["reply"]["info"].append("彈藥耗盡，重新裝填中……")
        return ammo_live, ammo_blank

    # 开枪
    @classmethod
    def shoot(cls, game, target):
        cls.trigger(game, "shoot", target=target)
        bullet = game["bullet"]
        if bullet:
            cls.damage(game, target, 1 + game["modify"].get("dmg", 0))
            pl = game["players"][target]
            game["reply"]["info"].append(
                f"“嘭！”{pl['name']}被崩倒在地[hp->{pl['hp']}]."
            )
            game["ammo_live"] -= 1
        else:
            game["reply"]["info"].append("“咔哒——”是空彈……")
            game["ammo_blank"] -= 1
        shooter = game["shooter"]
        if not bullet and target == shooter:
            game["players"][shooter]["actions"] += 1
        cls.bullet(game)
        cls.end_round(game)
        return

    # 受伤
    @classmethod
    def damage(cls, game, target, dmg):
        cls.trigger(game, "damage", target=target, dmg=dmg)
        pl = game["players"][target]
        name = pl["name"]
        pl["hp"] -= dmg
        if pl["hp"] <= 0:
            shooter = game["shooter"]
            if shooter != target:
                suicide = False
                game["players"][shooter]["kills"] += 1
                game["reply"]["info"].append(f"{name}死於他手。")
            else:
                suicide = True
                game["reply"]["info"].append(f"{name}自殺了……")
            cls.dead(game, target, suicide)
        return

    # 死亡
    @classmethod
    def dead(cls, game, target, suicide):
        game["players"][target]["suicide"] = suicide
        game["order"].remove(target)
        cls.points(game, target, False)
        return

    # 回合结束
    @classmethod
    def end_round(cls, game):
        if len(game["order"]) > 1:
            cls.trigger(game, "end_round")
            shooter = game["shooter"]
            pc = game["players"][shooter]
            pc["actions"] -= 1
            if pc["actions"] < 1:
                cls.switch(game)
        else:
            win = game["order"][0]
            name = cls.get_name(game, win)
            cls.points(game, win, True)
            game.clear()
            game.update({"reply": {"over": f"{name}用鮮血爲這場生死對局畫上句號."}})
        return

    # 换人
    @classmethod
    def switch(cls, game):
        order = game["order"]
        shooter = game["shooter"]
        while True:
            shooter = order[(order.index(shooter) + 1) % len(order)]
            pl = game["players"][shooter]
            pl["actions"] += 1
            if pl["actions"] > 0:
                break
        if shooter != game["shooter"]:
            game["shooter"] = shooter
            game["reply"]["shooter"] = f"現在是{pl['name']}的回合。"
            cls.trigger(game, "switch")
        return

    # 结算积分
    @classmethod
    def points(cls, game, target, survived):
        pl = game["players"][target]
        kills = pl["kills"]
        suicide = pl["suicide"]
        mult = kills * 0.5
        if survived:
            mult += 1
        elif suicide:
            mult -= 0.5
        wl = "wins" if survived else "losses"
        with DataBase(DB_PATH) as db:
            db.update(
                "gambler",
                {
                    "points": game["points"] * mult,
                    "kills": kills,
                    "suicide": 1 if suicide else 0,
                    wl: 1,
                },
                "user_id = ?",
                target,
                increment=("points", "kills", "suicide", wl),
            )
        return

    # endregion


# class FWGameWork(RegGameWork):
#     pass
