# -*- encoding: utf-8 -*-
"""
@File      :    tests/test_MammonRoulette.py
@Desc      :    恶魔轮盘(MammonRoulette) 自动化测试套件.

                依赖 debug.py 提供的本地桩环境, 无需真实 OlivOS 即可运行.
                覆盖范围:
                  1. 模式/道具/效果 注册表与配置一致性检查
                  2. 对局流程(匹配/加入/退出/开枪/投降/结算)
                  3. 各模式专属机制(经典/道具/金币/勇者/赌徒)
                  4. 各道具判定(手铐/锯子/邀请函/花生/巧克力/香烟/红牛/
                     放大镜/口红/扑克/转盘/牛奶/金币/止疼药/烟花)
                  5. 效果判定(束缚/神经麻痹)
                  6. AI 合法动作与自对弈

运行:
    cd 项目根目录
    .venv\\Scripts\\python.exe tests\\test_MammonRoulette.py
    或
    .venv\\Scripts\\python.exe -m unittest discover -s tests -v
"""

import contextlib
import os
import random
import sys
import unittest
from unittest import mock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import debug as D  # noqa: E402
from debug import init_env, send_message, make_msg_manager, make_ai_game  # noqa: E402

MR, PROC = init_env()

from AmorLib import DataBase  # noqa: E402
from MammonRoulette import config  # noqa: E402
from MammonRoulette.Core.work import RegGameWork  # noqa: E402
from MammonRoulette.Core.comp import ModeComp, PropComp, EffectComp, BotComp  # noqa: E402
from MammonRoulette.msgCustom import dictStrCustom, dictHelpDoc, dictDefsMode  # noqa: E402

ALL_MODES = ["经典", "道具", "金币", "勇者", "赌徒"]
ALL_PROPS = [
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
    "止疼药",
    "烟花",
]
ALL_EFFECTS = ["束缚", "神经麻痹"]


# ======================== 工具 ========================
_gid_counter = [900000]


def new_gid():
    _gid_counter[0] += 1
    return str(_gid_counter[0])


def game_state(gid):
    return MR.main.game_data.get(gid, {})


def open_game(mode, seats, gid=None, users=None):
    """以 seats 名人类玩家开设并开局一局 mode 模式对局."""
    gid = gid or new_gid()
    users = users or ["t{}_{}".format(gid, i) for i in range(1, seats + 1)]
    replies = [send_message(users[0], "{}匹配{}p".format(mode, seats), group_id=gid)]
    for u in users[1:]:
        replies.append(send_message(u, "加入", group_id=gid))
    return gid, users, replies


def db_row(user_id):
    with DataBase(config.DB_PATH) as db:
        rows = db.select("gambler", "*", "user_id = ?", user_id)
    assert rows, "数据库无该用户: {}".format(user_id)
    return dict(rows[0])


def shoot_direct(gid, shooter, target):
    """绕过消息路由, 直接触发开枪核心逻辑."""
    mm = make_msg_manager(shooter, gid)
    mm.val["game"]["tmp"] = {}
    RegGameWork.shoot(mm, target)
    return mm


def use_direct(gid, user, prop, target=None):
    """绕过消息路由, 直接触发道具使用核心逻辑."""
    mm = make_msg_manager(user, gid)
    mm.val["game"]["tmp"] = {}
    PropComp.use(mm, prop, user, target if target is not None else user)
    return mm


def effect_stacks(gid, target, effect):
    """读取目标 effect_event 的 stacks 数值."""
    return game_state(gid)["data"]["players"][target]["effect_event"].get(effect, {}).get("stacks", 0)


@contextlib.contextmanager
def rigged(randint=1, choice=0, shuffle_identity=True):
    """钉死 random 模块: randint 恒定, choice 取固定下标, shuffle 可选不做.

    使概率分支(1/3 概率、装弹数量、抽牌结果)确定化, 保证测试可复现.
    注意: 需要概率确定的行为必须整体位于 with 块内.
    """

    def _randint(a, b):
        return max(a, min(randint, b))

    def _choice(seq):
        return seq[choice]

    patches = [
        mock.patch.object(random, "randint", _randint),
        mock.patch.object(random, "choice", _choice),
    ]
    if shuffle_identity:
        patches.append(mock.patch.object(random, "shuffle", lambda x: None))
    for p in patches:
        p.start()
    try:
        yield
    finally:
        for p in patches:
            p.stop()


# ======================== 1. 注册表与配置 ========================
class TestRegistry(unittest.TestCase):
    def setUp(self):
        MR.main.game_data.clear()

    def test_modes_registered(self):
        self.assertEqual(set(ModeComp.list()), set(ALL_MODES))

    def test_props_registered(self):
        self.assertEqual(set(PropComp.list()), set(ALL_PROPS))

    def test_effects_registered(self):
        self.assertEqual(set(EffectComp.list()), set(ALL_EFFECTS))

    def test_mode_cfg_consistency(self):
        """每个模式: 座位范围合法, 赏金为正, 道具池全部是已注册道具."""
        for name in ModeComp.list():
            cfg = dictDefsMode["unity"][name]
            seats = cfg["seats"]
            self.assertLessEqual(seats["min"], seats["default"], name)
            self.assertLessEqual(seats["default"], seats["max"], name)
            self.assertGreater(cfg["points"], 0, name)
            props = cfg["props"]
            self.assertGreaterEqual(props["limit"], 1, name)
            for p in props["pool"] + props["ban"]:
                self.assertIn(p, PropComp.list(), "{} 模式道具池含未注册道具 {}".format(name, p))

    def test_reply_fields_registered(self):
        """模式/道具/效果 声明的回复词必须都已注册, 否则运行时 reply 为 None."""
        missing = []
        for name, cls in ModeComp._register.items():
            for field, _, _ in cls.reply:
                if field not in dictStrCustom:
                    missing.append((name, field))
        for name, cls in PropComp._register.items():
            for field, _, _ in cls.reply:
                if field not in dictStrCustom:
                    missing.append((name, field))
        for name, cls in EffectComp._register.items():
            for field, _, _ in cls.reply:
                if field not in dictStrCustom:
                    missing.append((name, field))
        self.assertFalse(missing, "未注册的回复词: {}".format(missing))

    def test_help_doc(self):
        self.assertIn("恶赌模式 经典", dictHelpDoc)
        self.assertIn("恶赌道具 手铐", dictHelpDoc)
        self.assertIn("恶赌效果 束缚", dictHelpDoc)

    def test_gold_direct_use_list_valid(self):
        """金币 direct_use 列表内的道具必须是已注册道具."""
        from MammonRoulette.Defs.prop import 金币

        for prop in 金币.direct_use:
            self.assertIn(prop, PropComp.list())


# ======================== 2. 对局流程 ========================
class TestGameFlow(unittest.TestCase):
    def setUp(self):
        MR.main.game_data.clear()

    def test_match_start_2p_classic(self):
        with rigged():
            gid, users, _ = open_game("经典", 2)
        game = game_state(gid)
        data = game["data"]
        self.assertTrue(game["start"])
        self.assertEqual(len(data["order"]), 2)
        for u in users:
            self.assertEqual(data["players"][u]["hp"], 4)
        self.assertEqual(data["players"][data["shooter"]]["actions"], 1)
        self.assertEqual((data["ammo_live"], data["ammo_blank"]), (1, 1))
        self.assertFalse(data["bullet"])

    def test_match_seats_out_of_range(self):
        r = send_message("u1", "经典匹配1p", group_id=new_gid())
        self.assertTrue(r and "非法人数" in r[-1])
        r = send_message("u2", "经典匹配9p", group_id=new_gid())
        self.assertTrue(r and "非法人数" in r[-1])

    def test_match_mode_mismatch(self):
        gid = new_gid()
        send_message("u1", "经典匹配2p", group_id=gid)
        r = send_message("u2", "道具匹配2p", group_id=gid)
        self.assertTrue(r and "已开设经典对局" in r[-1])

    def test_prep_join_exit(self):
        gid = new_gid()
        send_message("u1", "经典匹配3p", group_id=gid)
        game = game_state(gid)
        self.assertFalse(game["start"])
        send_message("u2", "加入", group_id=gid)
        self.assertEqual(len(game["data"]["order"]), 2)
        send_message("u2", "退出", group_id=gid)
        self.assertEqual(len(game["data"]["order"]), 1)
        send_message("u1", "退出", group_id=gid)
        self.assertFalse(game_state(gid))

    def test_join_after_start_ignored(self):
        with rigged():
            gid, users, _ = open_game("经典", 2)
        r = send_message("u_outsider", "加入", group_id=gid)
        self.assertEqual(len(game_state(gid)["data"]["order"]), 2)
        self.assertFalse(r)

    def test_not_your_turn(self):
        with rigged():
            gid, users, _ = open_game("经典", 2)
        game = game_state(gid)
        shooter = game["data"]["shooter"]
        other = next(u for u in users if u != shooter)
        r = send_message(other, "开枪", group_id=gid)
        self.assertTrue(r and "回合" in r[-1])

    def test_shoot_blank_and_switch(self):
        with rigged():
            gid, users, _ = open_game("经典", 2)
        game = game_state(gid)
        data = game["data"]
        shooter = data["shooter"]
        other = next(u for u in data["order"] if u != shooter)
        data["bullet"] = False
        data["ammo_live"], data["ammo_blank"] = 1, 1
        shoot_direct(gid, shooter, other)
        # 空包弹打他人消耗行动 → 换人
        self.assertEqual(game_state(gid)["data"]["shooter"], other)

    def test_shoot_blank_self_keeps_turn(self):
        with rigged():
            gid, users, _ = open_game("经典", 2)
        game = game_state(gid)
        data = game["data"]
        shooter = data["shooter"]
        data["bullet"] = False
        data["ammo_live"], data["ammo_blank"] = 1, 1
        shoot_direct(gid, shooter, shooter)
        self.assertEqual(game_state(gid)["data"]["shooter"], shooter)

    def test_shoot_kill_and_over(self):
        with rigged():
            gid, users, _ = open_game("经典", 2)
        game = game_state(gid)
        data = game["data"]
        shooter = data["shooter"]
        other = next(u for u in data["order"] if u != shooter)
        wins_before = int(db_row(shooter)["wins"])
        data["players"][other]["hp"] = 1
        data["bullet"] = True
        data["ammo_live"], data["ammo_blank"] = 1, 1
        shoot_direct(gid, shooter, other)
        game = game_state(gid)
        self.assertTrue(game["over"])
        self.assertEqual(game["data"]["order"], [shooter])
        self.assertEqual(game["data"]["players"][shooter]["kills"], 1)
        wins_after = int(db_row(shooter)["wins"])
        self.assertEqual(wins_after, wins_before + 1)

    def test_suicide_ends_game(self):
        with rigged():
            gid, users, _ = open_game("经典", 2)
        game = game_state(gid)
        data = game["data"]
        shooter = data["shooter"]
        other = next(u for u in data["order"] if u != shooter)
        data["players"][shooter]["hp"] = 1
        data["bullet"] = True
        data["ammo_live"], data["ammo_blank"] = 1, 1
        shoot_direct(gid, shooter, shooter)
        game = game_state(gid)
        self.assertTrue(game["over"])
        self.assertEqual(game["data"]["order"], [other])
        self.assertTrue(game["data"]["players"][shooter]["suicide"])

    def test_surrender_ends_game_when_one_left(self):
        """枪手投降后仅剩1人 → 对局应结束并结算(对局数据被清空, 回复含胜负)."""
        with rigged():
            gid, users, _ = open_game("经典", 2)
            game = game_state(gid)
            shooter = game["data"]["shooter"]
            sur_before = int(db_row(shooter)["surrender"])
            r = send_message(shooter, "投降", group_id=gid)
            game = game_state(gid)
            self.assertFalse(game.get("data", {}).get("order"), "枪手投降后仅剩1人, 对局应立即结束并清空")
            self.assertTrue(r and "臨陣脫逃" in r[-1] and "畫上句號" in r[-1], "投降回复应含投降与胜负文案")
            self.assertEqual(int(db_row(shooter)["surrender"]), sur_before + 1, "投降应计入数据库")

    def test_surrender_shooter_hands_over(self):
        """枪手投降且还有多人 → 枪交给下一位玩家, 对局继续."""
        with rigged():
            gid, users, _ = open_game("经典", 3)
        game = game_state(gid)
        data = game["data"]
        shooter = data["shooter"]
        next_uid = data["order"][(data["order"].index(shooter) + 1) % len(data["order"])]
        send_message(shooter, "投降", group_id=gid)
        game = game_state(gid)
        self.assertFalse(game.get("over"))
        self.assertNotIn(shooter, game["data"]["order"])
        self.assertEqual(game["data"]["shooter"], next_uid)

    def test_surrender_non_shooter_continues(self):
        with rigged():
            gid, users, _ = open_game("经典", 3)
        game = game_state(gid)
        data = game["data"]
        shooter = data["shooter"]
        other = next(u for u in data["order"] if u != shooter)
        send_message(other, "投降", group_id=gid)
        game = game_state(gid)
        self.assertFalse(game.get("over"))
        self.assertEqual(game["data"]["shooter"], shooter)
        self.assertNotIn(other, game["data"]["order"])

    def test_surrender_hands_over_to_ai(self):
        """枪手投降后剩余AI → AI接管并完成对局."""
        with rigged():
            gid = new_gid()
            send_message("hu_ai1", "经典匹配2p", group_id=gid)
            D.add_ai_to_game(gid)
            game = game_state(gid)
            shooter = game["data"]["shooter"]
            self.assertIn("hu_ai1", game["data"]["order"])
            r = send_message(shooter, "投降", group_id=gid)
            game = game_state(gid)
            self.assertTrue(r and "臨陣脫逃" in r[-1], "投降应得到回复")
            self.assertTrue(game.get("over") or not game, "剩余AI接管后对局应进行至终局")

    def test_shoot_target_by_number(self):
        with rigged():
            gid, users, _ = open_game("经典", 3)
            game = game_state(gid)
            data = game["data"]
            shooter = data["shooter"]
            next_uid = data["order"][(data["order"].index(shooter) + 1) % len(data["order"])]
            data["bullet"] = False
            data["ammo_live"], data["ammo_blank"] = 1, 1
            r = send_message(shooter, "开枪{}".format(data["order"].index(next_uid) + 1), group_id=gid)
            self.assertTrue(r)
            self.assertEqual(game_state(gid)["data"]["shooter"], next_uid)

    def test_shoot_target_by_uid(self):
        """纯数字用户ID(QQ号)可直接作为开枪目标."""
        with rigged():
            gid = new_gid()
            users = ["80001", "80002", "80003"]
            gid, users, _ = open_game("经典", 3, gid=gid, users=users)
            game = game_state(gid)
            data = game["data"]
            shooter = data["shooter"]
            next_uid = data["order"][(data["order"].index(shooter) + 1) % len(data["order"])]
            data["bullet"] = False
            data["ammo_live"], data["ammo_blank"] = 1, 1
            send_message(shooter, "开枪{}".format(next_uid), group_id=gid)
            self.assertEqual(game_state(gid)["data"]["shooter"], next_uid)

    def test_use_prop_not_owned(self):
        with rigged():
            gid, users, _ = open_game("经典", 2)
        game = game_state(gid)
        shooter = game["data"]["shooter"]
        other = next(u for u in users if u != shooter)
        if "手铐" not in game["data"]["players"][other]["props"]:
            game["data"]["players"][other]["props"] = []
        send_message(shooter, "使用手铐", group_id=gid)
        game = game_state(gid)
        if "手铐" in game["data"]["players"][shooter]["props"]:
            game["data"]["players"][shooter]["props"].remove("手铐")
        r = send_message(shooter, "使用手铐", group_id=gid)
        self.assertTrue(r and "你没有" in r[-1])

    def test_situation_reply(self):
        with rigged():
            gid, users, _ = open_game("经典", 2)
        r = send_message(users[0], "局势", group_id=gid)
        self.assertTrue(r)
        self.assertIn("hp:", r[-1])
        self.assertIn("槍手", r[-1])

    def test_signed_card_leaderboard(self):
        gid = new_gid()
        r = send_message("u_card1", "张三签署生死状", group_id=gid)
        self.assertTrue(r and "生死狀" in r[-1])
        r = send_message("u_card1", "恶魔名片", group_id=gid)
        self.assertTrue(r and "张三" in r[-1])
        r = send_message("u_card1", "恶魔赏金榜", group_id=gid)
        self.assertTrue(r and "赏金" in r[-1])


# ======================== 3. 模式机制 ========================
class TestModes(unittest.TestCase):
    def setUp(self):
        MR.main.game_data.clear()

    def test_mode_classic_start_draw(self):
        """经典模式: 首发抽2, 其余所有非首发玩家各抽1."""
        with rigged():
            gid, users, _ = open_game("经典", 3)
        game = game_state(gid)
        order = game["data"]["order"]
        counts = [len(game["data"]["players"][u]["props"]) for u in order]
        self.assertEqual(counts[0], 2, "首发玩家应抽2个道具")
        for idx, u in enumerate(order[1:], 1):
            self.assertEqual(counts[idx], 1, "非首发玩家 {} 应抽1个道具".format(u))

    def test_mode_classic_switch_draw(self):
        """经典模式: 换人后新枪手抽2个道具."""
        with rigged():
            gid, users, _ = open_game("经典", 2)
        game = game_state(gid)
        data = game["data"]
        shooter = data["shooter"]
        other = next(u for u in data["order"] if u != shooter)
        before = len(data["players"][other]["props"])
        data["bullet"] = False
        data["ammo_live"], data["ammo_blank"] = 1, 1
        shoot_direct(gid, shooter, other)
        game = game_state(gid)
        self.assertEqual(game["data"]["shooter"], other)
        self.assertEqual(len(game["data"]["players"][other]["props"]), before + 2)

    def test_mode_item_hp(self):
        """道具模式: 前3名玩家5hp, 其余6hp."""
        with rigged():
            gid, users, _ = open_game("道具", 4)
        data = game_state(gid)["data"]
        for u in users[:3]:
            self.assertEqual(data["players"][u]["hp"], 5)
        self.assertEqual(data["players"][users[3]]["hp"], 6)

    def test_mode_item_reload_draw(self):
        """道具模式: 装弹时所有存活玩家抽4个道具."""
        with rigged():
            gid, users, _ = open_game("道具", 2)
            game = game_state(gid)
            data = game["data"]
            for u in data["order"]:
                data["players"][u]["props"] = []
            data["ammo_live"], data["ammo_blank"] = 0, 0
            mm = make_msg_manager(data["shooter"], gid)
            RegGameWork.bullet(mm)
            for u in data["order"]:
                self.assertEqual(len(data["players"][u]["props"]), 4)
            self.assertEqual((data["ammo_live"], data["ammo_blank"]), (1, 1))

    def test_mode_gold_draw_on_start_and_switch(self):
        """金币模式: 首发与每位新枪手获得1枚金币."""
        with rigged():
            gid, users, _ = open_game("金币", 2)
        game = game_state(gid)
        data = game["data"]
        shooter = data["shooter"]
        other = next(u for u in data["order"] if u != shooter)
        self.assertEqual(data["players"][shooter]["props"], ["金币"])
        self.assertEqual(data["players"][other]["props"], [])
        data["bullet"] = False
        data["ammo_live"], data["ammo_blank"] = 1, 1
        shoot_direct(gid, shooter, other)
        self.assertEqual(game_state(gid)["data"]["players"][other]["props"], ["金币"])

    def test_mode_gold_low_hp_grant_once(self):
        """金币模式: 血量首次低至2时获得金币, 只触发一次."""
        with rigged():
            gid, users, _ = open_game("金币", 2)
            game = game_state(gid)
            data = game["data"]
            shooter = data["shooter"]
            other = next(u for u in data["order"] if u != shooter)
            data["players"][other]["hp"] = 3
            mm = make_msg_manager(shooter, gid)
            mm.val["game"]["tmp"] = {}
            RegGameWork.damage(mm, other, 1, shooter)
            self.assertEqual(game_state(gid)["data"]["players"][other]["hp"], 2)
            self.assertIn("金币", game_state(gid)["data"]["players"][other]["props"])
            before = game_state(gid)["data"]["players"][other]["props"].count("金币")
            mm.val["game"]["tmp"] = {}
            RegGameWork.damage(mm, other, 1, shooter)
            self.assertEqual(game_state(gid)["data"]["players"][other]["props"].count("金币"), before)

    def test_mode_hero_start_draw(self):
        """勇者模式: 首发抽1, 非首发各抽2."""
        with rigged():
            gid, users, _ = open_game("勇者", 3)
        game = game_state(gid)
        order = game["data"]["order"]
        counts = [len(game["data"]["players"][u]["props"]) for u in order]
        self.assertEqual(counts[0], 1)
        for idx in (1, 2):
            self.assertEqual(counts[idx], 2)

    def test_mode_hero_self_blank_draw(self):
        """勇者模式: 对自己开枪且为空包弹 → 抽2个道具."""
        with rigged(randint=3):
            gid, users, _ = open_game("勇者", 2)
            game = game_state(gid)
            data = game["data"]
            shooter = data["shooter"]
            before = len(data["players"][shooter]["props"])
            data["bullet"] = False
            data["ammo_live"], data["ammo_blank"] = 1, 1
            shoot_direct(gid, shooter, shooter)
            self.assertEqual(len(game_state(gid)["data"]["players"][shooter]["props"]), before + 2)
            self.assertEqual(game_state(gid)["data"]["shooter"], shooter)

    def test_mode_hero_live_dmg_bonus(self):
        """勇者模式: 实弹1/3概率伤害+1 (钉死触发)."""
        with rigged(randint=1):
            gid, users, _ = open_game("勇者", 2)
            game = game_state(gid)
            data = game["data"]
            shooter = data["shooter"]
            other = next(u for u in data["order"] if u != shooter)
            data["players"][other]["hp"] = 5
            data["bullet"] = True
            data["ammo_live"], data["ammo_blank"] = 2, 1
            shoot_direct(gid, shooter, other)
            self.assertEqual(game_state(gid)["data"]["players"][other]["hp"], 3)

    def test_mode_gambler_start_draw(self):
        """赌徒模式: 开局所有玩家抽2个道具."""
        with rigged():
            gid, users, _ = open_game("赌徒", 3)
        game = game_state(gid)
        for u in game["data"]["order"]:
            self.assertEqual(len(game["data"]["players"][u]["props"]), 2)

    def test_mode_gambler_self_blank_draw(self):
        """赌徒模式: 对自己开枪且为空包弹 → 抽3个道具."""
        with rigged(randint=3):
            gid, users, _ = open_game("赌徒", 2)
            game = game_state(gid)
            data = game["data"]
            shooter = data["shooter"]
            before = len(data["players"][shooter]["props"])
            data["bullet"] = False
            data["ammo_live"], data["ammo_blank"] = 1, 1
            shoot_direct(gid, shooter, shooter)
            self.assertEqual(len(game_state(gid)["data"]["players"][shooter]["props"]), before + 3)

    def test_mode_gambler_flip(self):
        """赌徒模式: 1/3概率反转虚实(钉死触发), 空包弹反转为实弹并命中."""
        with rigged(randint=1):
            gid, users, _ = open_game("赌徒", 2)
            game = game_state(gid)
            data = game["data"]
            shooter = data["shooter"]
            other = next(u for u in data["order"] if u != shooter)
            data["players"][other]["hp"] = 5
            data["bullet"] = False
            data["ammo_live"], data["ammo_blank"] = 1, 1
            shoot_direct(gid, shooter, other)
            game = game_state(gid)
            # 空包(1/1)反转为实弹 → 命中, 弹药 0空/1实; 伤害加成同时触发 → 2
            self.assertEqual(game["data"]["players"][other]["hp"], 3)
            self.assertEqual((game["data"]["ammo_live"], game["data"]["ammo_blank"]), (1, 0))

    def test_mode_gambler_ammo_hidden(self):
        """赌徒模式: 不显示弹药数量."""
        with rigged():
            gid, users, _ = open_game("赌徒", 2)
        game = game_state(gid)
        self.assertFalse(game["data"]["modify"]["ammo_show"])
        r = send_message(users[0], "局势", group_id=gid)
        self.assertTrue(r and "迷霧" in r[-1])


# ======================== 4. 道具判定 ========================
class TestProps(unittest.TestCase):
    def setUp(self):
        MR.main.game_data.clear()

    def test_prop_handcuff_skip_turn(self):
        """手铐: 目标行动-1, 被跳过1回合后恢复并解除束缚."""
        with rigged():
            gid, users, _ = open_game("经典", 2)
            game = game_state(gid)
            data = game["data"]
            shooter = data["shooter"]
            other = next(u for u in data["order"] if u != shooter)
            data["players"][shooter]["props"].append("手铐")
            use_direct(gid, shooter, "手铐", shooter)  # 对自己使用 → 默认目标下一位
            self.assertEqual(data["players"][other]["actions"], -1)
            self.assertEqual(effect_stacks(gid, other, "束缚"), 1)
            # 空包打自己 → 不换人
            data["bullet"] = False
            data["ammo_live"], data["ammo_blank"] = 1, 1
            shoot_direct(gid, shooter, shooter)
            self.assertEqual(game_state(gid)["data"]["shooter"], shooter)
            # 空包打他人 → 换人时 other 被跳过 → 枪手不变
            game = game_state(gid)
            game["data"]["bullet"] = False
            game["data"]["ammo_live"], game["data"]["ammo_blank"] = 1, 1
            shoot_direct(gid, shooter, other)
            self.assertEqual(game_state(gid)["data"]["shooter"], shooter)
            self.assertEqual(game_state(gid)["data"]["players"][other]["actions"], 0)
            # 再一回合 → other 恢复, 束缚解除
            game = game_state(gid)
            game["data"]["bullet"] = False
            game["data"]["ammo_live"], game["data"]["ammo_blank"] = 1, 1
            shoot_direct(gid, shooter, other)
            self.assertEqual(game_state(gid)["data"]["shooter"], other)
            self.assertEqual(effect_stacks(gid, other, "束缚"), 0)

    def test_prop_handcuff_second_use_fails(self):
        with rigged():
            gid, users, _ = open_game("经典", 2)
            game = game_state(gid)
            data = game["data"]
            shooter = data["shooter"]
            other = next(u for u in data["order"] if u != shooter)
            data["players"][shooter]["props"] = ["手铐", "手铐"]
            use_direct(gid, shooter, "手铐", other)
            self.assertEqual(effect_stacks(gid, other, "束缚"), 1)
            use_direct(gid, shooter, "手铐", other)
            self.assertEqual(effect_stacks(gid, other, "束缚"), 1, "已束缚目标不应叠加")
            self.assertEqual(data["players"][shooter]["props"].count("手铐"), 1, "失败使用不应消耗道具")

    def test_prop_saw(self):
        """锯子: 每次开枪前限1次, 下一发实弹伤害+1, 开枪后移除."""
        with rigged():
            gid, users, _ = open_game("经典", 2)
            game = game_state(gid)
            data = game["data"]
            shooter = data["shooter"]
            other = next(u for u in data["order"] if u != shooter)
            data["players"][shooter]["props"].append("锯子")
            mm = use_direct(gid, shooter, "锯子", shooter)
            self.assertEqual(len(RegGameWork.get_prop_data(mm, prop_name="锯子")), 1)
            data["players"][shooter]["props"].append("锯子")
            use_direct(gid, shooter, "锯子", shooter)
            self.assertEqual(len(RegGameWork.get_prop_data(mm, prop_name="锯子")), 1, "重复使用不生效")
            self.assertEqual(data["players"][shooter]["props"].count("锯子"), 1)
            data["players"][other]["hp"] = 4
            data["bullet"] = True
            data["ammo_live"], data["ammo_blank"] = 2, 1
            shoot_direct(gid, shooter, other)
            self.assertEqual(game_state(gid)["data"]["players"][other]["hp"], 2)
            self.assertEqual(len(RegGameWork.get_prop_data(mm, prop_name="锯子")), 0)

    def test_prop_invite(self):
        """邀请函: 目标抽2个道具并结束枪手回合(换人)."""
        with rigged():
            gid, users, _ = open_game("经典", 2)
            game = game_state(gid)
            data = game["data"]
            shooter = data["shooter"]
            other = next(u for u in data["order"] if u != shooter)
            data["players"][other]["props"] = []
            data["players"][shooter]["props"].append("邀请函")
            use_direct(gid, shooter, "邀请函", other)
            game = game_state(gid)
            self.assertEqual(game["data"]["shooter"], other)
            self.assertEqual(len(game["data"]["players"][other]["props"]), 4)  # 邀请函抽2 + 换人抽2
            self.assertNotIn("邀请函", game["data"]["players"][shooter]["props"])

    def test_prop_ammo_props(self):
        """花生/巧克力/香烟 对弹药数量的影响."""
        with rigged():
            gid, users, _ = open_game("经典", 2)
            game = game_state(gid)
            data = game["data"]
            shooter = data["shooter"]
            data["players"][shooter]["props"] += ["花生", "巧克力", "香烟", "香烟", "香烟"]
            data["ammo_live"], data["ammo_blank"] = 1, 1
            use_direct(gid, shooter, "花生", shooter)
            self.assertEqual(data["ammo_blank"], 2)
            use_direct(gid, shooter, "巧克力", shooter)
            self.assertEqual(data["ammo_live"], 2)
            use_direct(gid, shooter, "香烟", shooter)  # 取空包弹
            self.assertEqual((data["ammo_live"], data["ammo_blank"]), (2, 1))
            use_direct(gid, shooter, "香烟", shooter)  # 再取空包弹
            self.assertEqual((data["ammo_live"], data["ammo_blank"]), (2, 0))
            use_direct(gid, shooter, "香烟", shooter)  # 无空包弹 → 取实弹
            self.assertEqual((data["ammo_live"], data["ammo_blank"]), (1, 0))

    def test_prop_redcow_heal(self):
        """红牛: 目标HP+1, 不消耗行动."""
        with rigged():
            gid, users, _ = open_game("经典", 2)
            game = game_state(gid)
            data = game["data"]
            shooter = data["shooter"]
            data["players"][shooter]["hp"] = 2
            data["players"][shooter]["props"].append("红牛")
            use_direct(gid, shooter, "红牛", shooter)
            self.assertEqual(game_state(gid)["data"]["players"][shooter]["hp"], 3)
            self.assertEqual(game_state(gid)["data"]["players"][shooter]["actions"], 1)

    def test_prop_magnifier(self):
        """放大镜: 开枪前持续显示子弹, 开枪后恢复模式默认显示."""
        with rigged():
            gid, users, _ = open_game("经典", 2)
            game = game_state(gid)
            data = game["data"]
            shooter = data["shooter"]
            data["players"][shooter]["props"] += ["放大镜", "放大镜"]
            mm = use_direct(gid, shooter, "放大镜", shooter)
            self.assertTrue(data["modify"]["bullet_show"])
            use_direct(gid, shooter, "放大镜", shooter)
            self.assertEqual(data["players"][shooter]["props"].count("放大镜"), 1, "重复使用不消耗道具")
            self.assertEqual(len(RegGameWork.get_prop_data(mm, prop_name="放大镜")), 1)
            data["bullet"] = False
            data["ammo_live"], data["ammo_blank"] = 1, 1
            shoot_direct(gid, shooter, shooter)
            game = game_state(gid)
            self.assertFalse(game["data"]["modify"]["bullet_show"])
            self.assertTrue(game["data"]["modify"]["ammo_show"])

    def test_prop_lipstick_steal(self):
        """口红: 夺取目标1个道具(口红/金币除外), 自身口红被消耗."""
        with rigged():
            gid, users, _ = open_game("经典", 2)
            game = game_state(gid)
            data = game["data"]
            shooter = data["shooter"]
            other = next(u for u in data["order"] if u != shooter)
            data["players"][shooter]["props"].append("口红")
            data["players"][other]["props"] = ["香烟"]
            use_direct(gid, shooter, "口红", other)
            game = game_state(gid)
            self.assertNotIn("香烟", game["data"]["players"][other]["props"])
            self.assertIn("香烟", game["data"]["players"][shooter]["props"])
            self.assertNotIn("口红", game["data"]["players"][shooter]["props"])

    def test_prop_lipstick_self_draw(self):
        with rigged():
            gid, users, _ = open_game("经典", 2)
            game = game_state(gid)
            data = game["data"]
            shooter = data["shooter"]
            data["players"][shooter]["props"].append("口红")
            before = len(data["players"][shooter]["props"])
            use_direct(gid, shooter, "口红", shooter)
            game = game_state(gid)
            self.assertNotIn("口红", game["data"]["players"][shooter]["props"])
            self.assertEqual(len(game["data"]["players"][shooter]["props"]), before, "口红换1个新道具")

    def test_prop_poker(self):
        """扑克: 反转子弹并隐藏弹仓, 开枪后迷雾驱散."""
        with rigged():
            gid, users, _ = open_game("经典", 2)
            game = game_state(gid)
            data = game["data"]
            shooter = data["shooter"]
            data["players"][shooter]["props"].append("扑克")
            data["bullet"] = False
            data["ammo_live"], data["ammo_blank"] = 1, 1
            use_direct(gid, shooter, "扑克", shooter)
            self.assertTrue(data["bullet"])
            self.assertEqual((data["ammo_live"], data["ammo_blank"]), (2, 0))
            self.assertFalse(data["modify"]["ammo_show"])
            self.assertFalse(data["modify"]["bullet_show"])
            data["players"][shooter]["hp"] = 4
            shoot_direct(gid, shooter, shooter)
            game = game_state(gid)
            self.assertTrue(game["data"]["modify"]["ammo_show"])
            self.assertEqual(game["data"]["players"][shooter]["hp"], 3)

    def test_prop_roulette(self):
        """转盘: 重新装填弹仓并清除扑克迷雾."""
        with rigged():
            gid, users, _ = open_game("经典", 2)
            game = game_state(gid)
            data = game["data"]
            shooter = data["shooter"]
            data["players"][shooter]["props"] += ["扑克", "转盘"]
            data["bullet"] = False
            data["ammo_live"], data["ammo_blank"] = 1, 1
            use_direct(gid, shooter, "扑克", shooter)
            self.assertFalse(data["modify"]["ammo_show"])
            use_direct(gid, shooter, "转盘", shooter)
            self.assertEqual((data["ammo_live"], data["ammo_blank"]), (1, 0))  # rigged: 总1发全实弹
            self.assertTrue(data["modify"]["ammo_show"])

    def test_prop_milk(self):
        """牛奶: 目标抽2个, 其余每人抽1个."""
        with rigged():
            gid, users, _ = open_game("经典", 3)
            game = game_state(gid)
            data = game["data"]
            shooter = data["shooter"]
            others = [u for u in data["order"] if u != shooter]
            for u in data["order"]:
                data["players"][u]["props"] = []
            data["players"][shooter]["props"].append("牛奶")
            use_direct(gid, shooter, "牛奶", others[0])
            game = game_state(gid)
            self.assertEqual(len(game["data"]["players"][others[0]]["props"]), 2)
            self.assertEqual(len(game["data"]["players"][others[1]]["props"]), 1)
            self.assertEqual(len(game["data"]["players"][shooter]["props"]), 1)

    def test_prop_gold_purchase(self):
        """金币(购买): 兑换道具, direct_use 道具立即生效."""
        with rigged():
            gid, users, _ = open_game("金币", 2)
        game = game_state(gid)
        data = game["data"]
        shooter = data["shooter"]
        self.assertIn("金币", data["players"][shooter]["props"])
        r = send_message(shooter, "购买锯子", group_id=gid)
        self.assertTrue(r)
        game = game_state(gid)
        self.assertNotIn("金币", game["data"]["players"][shooter]["props"])
        self.assertNotIn("锯子", game["data"]["players"][shooter]["props"])  # 立即使用
        mm = make_msg_manager(shooter, gid)
        self.assertEqual(len(RegGameWork.get_prop_data(mm, prop_name="锯子")), 1)

    def test_prop_gold_purchase_non_holder(self):
        with rigged():
            gid, users, _ = open_game("金币", 2)
        game = game_state(gid)
        shooter = game["data"]["shooter"]
        other = next(u for u in game["data"]["order"] if u != shooter)
        r = send_message(other, "购买锯子", group_id=gid)
        self.assertTrue(r and "回合" in r[-1])

    def test_prop_painkiller_reject_second_use(self):
        """止疼药: 目标已受神经麻痹保护时再次使用应失败且不消耗道具."""
        with rigged():
            gid, users, _ = open_game("经典", 2)
            game = game_state(gid)
            data = game["data"]
            shooter = data["shooter"]
            other = next(u for u in data["order"] if u != shooter)
            data["players"][shooter]["props"] += ["止疼药", "止疼药"]
            use_direct(gid, shooter, "止疼药", other)
            effect = data["players"][other]["effect_event"]["神经麻痹"]
            self.assertEqual(len(effect["data"]), 1)
            use_direct(gid, shooter, "止疼药", other)
            self.assertEqual(len(effect["data"]), 1, "已受保护的目标不应重复生效")
            self.assertEqual(data["players"][shooter]["props"].count("止疼药"), 1, "失败使用不应消耗道具")

    def test_prop_firework(self):
        """烟花: 每人1/2概率HP-1(钉死触发), 每生效一次每人抽1个道具."""
        with rigged(randint=1):
            gid, users, _ = open_game("经典", 2)
            game = game_state(gid)
            data = game["data"]
            shooter = data["shooter"]
            for u in data["order"]:
                data["players"][u]["hp"] = 5
            before = {u: len(data["players"][u]["props"]) for u in data["order"]}
            data["players"][shooter]["props"].append("烟花")
            use_direct(gid, shooter, "烟花", shooter)
            game = game_state(gid)
            self.assertFalse(game.get("over"))
            for u in data["order"]:
                self.assertEqual(game["data"]["players"][u]["hp"], 4)
                self.assertEqual(len(game["data"]["players"][u]["props"]), before[u] + 1)

    def test_prop_firework_tied(self):
        """烟花: 全员阵亡 → 平局并结算."""
        with rigged(randint=1):
            gid, users, _ = open_game("经典", 2)
            game = game_state(gid)
            data = game["data"]
            shooter = data["shooter"]
            for u in data["order"]:
                data["players"][u]["hp"] = 1
            data["players"][shooter]["props"].append("烟花")
            use_direct(gid, shooter, "烟花", shooter)
            game = game_state(gid)
            self.assertTrue(game["over"])
            self.assertEqual(game["data"]["order"], [])


# ======================== 5. 效果判定 ========================
class TestEffects(unittest.TestCase):
    def setUp(self):
        MR.main.game_data.clear()

    def test_effect_paralysis_converts_damage(self):
        """神经麻痹: 回合结束前受到的枪击伤害转为等值层数, 回合结束结算掉血并移除."""
        with rigged(randint=3):
            gid, users, _ = open_game("经典", 2)
            game = game_state(gid)
            data = game["data"]
            shooter = data["shooter"]
            other = next(u for u in data["order"] if u != shooter)
            data["players"][shooter]["props"].append("止疼药")
            use_direct(gid, shooter, "止疼药", other)
            effect = data["players"][other]["effect_event"]["神经麻痹"]
            self.assertIsNotNone(effect)
            self.assertTrue(effect["expired"])  # 对他人使用: 对方回合结束即结算
            # 实弹命中: 伤害转层数, HP 不变
            data["players"][other]["hp"] = 4
            data["bullet"] = True
            data["ammo_live"], data["ammo_blank"] = 2, 1
            shoot_direct(gid, shooter, other)
            self.assertEqual(game_state(gid)["data"]["players"][other]["hp"], 4)
            self.assertEqual(effect["stacks"], 1)
            # 对方回合结束 → 结算 1 点伤害, 效果移除
            game = game_state(gid)
            game["data"]["shooter"] = other
            mm = make_msg_manager(other, gid)
            mm.val["game"]["tmp"] = {"consume_action": 1}
            RegGameWork.end_round(mm)
            game = game_state(gid)
            self.assertEqual(game["data"]["players"][other]["hp"], 3)
            self.assertNotIn("神经麻痹", game["data"]["players"][other]["effect_event"])

    def test_effect_paralysis_self_lasts_next_round(self):
        """神经麻痹(对自己): 效果延长到下回合结束."""
        with rigged(randint=3):
            gid, users, _ = open_game("经典", 2)
            game = game_state(gid)
            data = game["data"]
            shooter = data["shooter"]
            data["players"][shooter]["props"].append("止疼药")
            use_direct(gid, shooter, "止疼药", shooter)
            effect = data["players"][shooter]["effect_event"]["神经麻痹"]
            self.assertFalse(effect["expired"])
            # 本回合结束: 标记过期但不结算
            mm = make_msg_manager(shooter, gid)
            mm.val["game"]["tmp"] = {"consume_action": 1}
            RegGameWork.end_round(mm)
            self.assertTrue(effect["expired"])
            self.assertIn("神经麻痹", game_state(gid)["data"]["players"][shooter]["effect_event"])
            # 下回合结束: 结算并移除
            game = game_state(gid)
            game["data"]["shooter"] = shooter
            mm = make_msg_manager(shooter, gid)
            mm.val["game"]["tmp"] = {"consume_action": 1}
            RegGameWork.end_round(mm)
            self.assertNotIn("神经麻痹", game_state(gid)["data"]["players"][shooter]["effect_event"])

    def test_effect_bind_stacks(self):
        """束缚: 被手铐囚禁的标识, 层数为1."""
        with rigged():
            gid, users, _ = open_game("经典", 2)
            game = game_state(gid)
            data = game["data"]
            shooter = data["shooter"]
            other = next(u for u in data["order"] if u != shooter)
            data["players"][shooter]["props"].append("手铐")
            use_direct(gid, shooter, "手铐", shooter)
            self.assertEqual(effect_stacks(gid, other, "束缚"), 1)


# ======================== 6. AI ========================
class TestAI(unittest.TestCase):
    def setUp(self):
        MR.main.game_data.clear()

    def test_ai_legal_actions_structure(self):
        """AI 合法动作: 永远包含吞枪, 被束缚目标不可再被手铐选中."""
        with rigged():
            gid, users, _ = open_game("经典", 3)
            game = game_state(gid)
            data = game["data"]
            shooter = data["shooter"]
            order = data["order"]
            next_uid = order[(order.index(shooter) + 1) % len(order)]
            data["players"][shooter]["props"].append("手铐")
            use_direct(gid, shooter, "手铐", shooter)
            mm = make_msg_manager(shooter, gid)
            actions = BotComp.legal_actions(mm)
            self.assertIn("吞枪", actions)
            self.assertNotIn("使用手铐", actions, "下一位已被束缚, 手铐无合法目标")
            self.assertNotIn("使用手铐{}".format(order.index(next_uid) + 1), actions)

    def test_ai_self_play_completes(self):
        """AI 自对弈一局必须能正常终局(胜者≤1)."""
        import numpy as np

        random.seed(20240908)
        np.random.seed(20240908)
        gid = new_gid()
        game = make_ai_game(gid)
        self.assertTrue(game.get("over"), "AI自对弈应正常结束")
        self.assertLessEqual(len(game["data"]["order"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
