# -*- encoding: utf-8 -*-
"""
@File      :    MammonRoulette/config.py
@Author    :    lianqingyuYuri恋倾雨
@Contact   :    xinghu2408@foxmail.com
@License   :    AGPLv3
@Copyright :    (C) 2026 MammonRoulette
@Desc      :    None
"""

import copy
import json
import os

from AmorLib import IniConfig

from .msgCustom import dictDefsMode, dictDefsProp, dictDefsEffect

name = "恶魔轮盘"
debug = False

dataDirRoot = "plugin/data/MammonRoulette/data"

default_db_path = "plugin/data/MammonRoulette/Roulette.db"
DB_PATH = ""
default_tmp_game_path = "plugin/tmp/MammonRoulette_data.json"
TMP_GAME_PATH = ""


def releaseDir(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


def initConfig(Proc):
    global DB_PATH, TMP_GAME_PATH
    with IniConfig("plugin/data/MammonRoulette/data/config.ini") as cfg:
        DB_PATH = cfg.get("database", "db_path", default_db_path)
        TMP_GAME_PATH = cfg.get("tmp", "tmp_game_path", default_tmp_game_path)
    for hash_this in Proc.Proc_data["bot_info_dict"]:
        releaseDir(dataDirRoot + "/" + hash_this)


def readConfig(Proc):
    global DB_PATH, TMP_GAME_PATH
    with IniConfig("plugin/data/MammonRoulette/data/config.ini") as cfg:
        DB_PATH = cfg.get("database", "db_path", default_db_path)
        TMP_GAME_PATH = cfg.get("tmp", "tmp_game_path", default_tmp_game_path)
    for hash_this in Proc.Proc_data["bot_info_dict"]:
        custom_path = dataDirRoot + "/" + hash_this
        releaseDir(custom_path)
        dictDefsMode[hash_this] = copy.deepcopy(dictDefsMode["default"])
        dictDefsProp[hash_this] = copy.deepcopy(dictDefsProp["default"])
        dictDefsEffect[hash_this] = copy.deepcopy(dictDefsEffect["default"])
        try:
            with open(custom_path + "/customMode.json", "r", encoding="utf-8") as f:
                customDefs = json.load(f)
                dictDefsMode[hash_this].update(customDefs)
        except:
            pass
        try:
            with open(custom_path + "/customProp.json", "r", encoding="utf-8") as f:
                customDefs = json.load(f)
                dictDefsProp[hash_this].update(customDefs)
        except:
            pass
        try:
            with open(custom_path + "/customEffect.json", "r", encoding="utf-8") as f:
                customDefs = json.load(f)
                dictDefsEffect[hash_this].update(customDefs)
        except:
            pass


def saveConfig(Proc):
    for hash_this in Proc.Proc_data["bot_info_dict"]:
        custom_path = dataDirRoot + "/" + hash_this
        releaseDir(custom_path)
        with open(custom_path + "/customMode.json", "w", encoding="utf-8") as f:
            json.dump(dictDefsMode[hash_this], f, ensure_ascii=False, indent=4)
        with open(custom_path + "/customProp.json", "w", encoding="utf-8") as f:
            json.dump(dictDefsProp[hash_this], f, ensure_ascii=False, indent=4)
        with open(custom_path + "/customEffect.json", "w", encoding="utf-8") as f:
            json.dump(dictDefsEffect[hash_this], f, ensure_ascii=False, indent=4)
