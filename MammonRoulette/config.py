# -*- encoding: utf-8 -*-
"""
@File      :    MammonRoulette/config.py
@Author    :    lianqingyuYuri恋倾雨
@Contact   :    xinghu2408@foxmail.com
@License   :    AGPLv3
@Copyright :    (C) 2026 MammonRoulette
@Desc      :    None
"""

from AmorLib import IniConfig

plugin_name = "恶魔轮盘"

default_db_path = "plugin/data/MammonRoulette/Roulette.db"
DB_PATH = ""
default_tmp_game_path = "plugin/tmp/MammonRoulette_data.json"
TMP_GAME_PATH = ""


def init_config():
    global DB_PATH, TMP_GAME_PATH
    with IniConfig("plugin/data/MammonRoulette/data/config.ini") as cfg:
        DB_PATH = cfg.get("database", "db_path", default_db_path)
        TMP_GAME_PATH = cfg.get("tmp", "tmp_game_path", default_tmp_game_path)
