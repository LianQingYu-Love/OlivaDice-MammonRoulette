# -*- encoding: utf-8 -*-
"""
@File      :    MammonRoulette/config.py
@Author    :    lianqingyuYuri恋倾雨
@Contact   :    xinghu2408@foxmail.com
@License   :    AGPLv3
@Copyright :    (C) 2026 MammonRoulette
@Desc      :    None
"""

try:
    import OlivaDiceNativeGUI

    has_NativeGUI = True
except ImportError:
    has_NativeGUI = False

import copy
import json
import os

from AmorLib import IniConfig

from .msgCustom import dictDefsMode, dictDefsProp, dictDefsEffect

name = "恶魔轮盘"


dataDirRoot = "plugin/data/MammonRoulette/data"
configPath = "plugin/data/MammonRoulette/data/config.ini"

default_db_path = "plugin/data/MammonRoulette/Roulette.db"
DB_PATH = ""
default_tmp_game_path = "plugin/tmp/MammonRoulette_data.json"
TMP_GAME_PATH = ""

default_debug_flag = False
DEBUG_FLAG = 0

default_ai_model_dir = "plugin/data/MammonRoulette/data/ai_model/"
AI_MODEL_DIR = ""


def releaseDir(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


def initConfig(Proc):
    global DB_PATH, TMP_GAME_PATH, DEBUG_FLAG, AI_MODEL_DIR
    with IniConfig(configPath) as cfg:
        DB_PATH = cfg.get("path", "db_path", default_db_path)
        TMP_GAME_PATH = cfg.get("path", "tmp_game_path", default_tmp_game_path)
        DEBUG_FLAG = cfg.getboolean("flags", "debug_flag", default_debug_flag)
        AI_MODEL_DIR = cfg.get("dir", "ai_model_dir", default_ai_model_dir)
    for hash_this in Proc.Proc_data["bot_info_dict"]:
        releaseDir(dataDirRoot + "/" + hash_this)


def readConfig(Proc):
    global DB_PATH, TMP_GAME_PATH, DEBUG_FLAG
    with IniConfig(configPath) as cfg:
        DB_PATH = cfg.get("path", "db_path", default_db_path)
        TMP_GAME_PATH = cfg.get("path", "tmp_game_path", default_tmp_game_path)
        DEBUG_FLAG = cfg.getboolean("flags", "debug_flag", default_debug_flag)
        AI_MODEL_DIR = cfg.get("dir", "ai_model_dir", default_ai_model_dir)
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
    with IniConfig(configPath) as cfg:
        cfg.set("path", "db_path", DB_PATH)
        cfg.set("path", "tmp_game_path", TMP_GAME_PATH)
        cfg.set("flags", "debug_flag", DEBUG_FLAG)
        cfg.set("dir", "ai_model_dir", AI_MODEL_DIR)
        cfg.save()
    for hash_this in Proc.Proc_data["bot_info_dict"]:
        custom_path = dataDirRoot + "/" + hash_this
        releaseDir(custom_path)
        with open(custom_path + "/customMode.json", "w", encoding="utf-8") as f:
            json.dump(dictDefsMode[hash_this], f, ensure_ascii=False, indent=4)
        with open(custom_path + "/customProp.json", "w", encoding="utf-8") as f:
            json.dump(dictDefsProp[hash_this], f, ensure_ascii=False, indent=4)
        with open(custom_path + "/customEffect.json", "w", encoding="utf-8") as f:
            json.dump(dictDefsEffect[hash_this], f, ensure_ascii=False, indent=4)
