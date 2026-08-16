# -*- encoding: utf-8 -*-
"""
@File      :    MammonRoulette/__init__.py
@Author    :    lianqingyuYuri恋倾雨
@Contact   :    xinghu2408@foxmail.com
@License   :    AGPLv3
@Copyright :    (C) 2026 MammonRoulette
@Desc      :    None
"""

from . import config

from . import Core
from . import Defs

from . import main
from . import msgCustom
from . import msgReply

import platform

if platform.system() == "Windows":
    from . import GUI
