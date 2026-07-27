"""《空杯俱乐部》：给 AI 玩的零依赖文字酒吧游戏。

对外接口：
    new_game(seed)
    cmd("指令")
    write_archive()
    restore_archive(archive_text)
    conversation_turn(user_message)  # 离店后每次回复用户前强制调用
    register_guest(card) # 给私人世界包增加候选来客

游戏本体不依赖第三方库。当前环境内自动写入同目录 bar_save.json；
跨窗口时用严格的【AI酒吧档案｜V1】交给 AI 的长期记忆保存。
"""

from __future__ import annotations

import base64
import json
import math
import os
import shlex
import uuid
import zlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


VERSION = 1
MASK32 = 0xFFFFFFFF
SAVE_PATH = Path(__file__).with_name("bar_save.json")
ARCHIVE_BEGIN = "【AI酒吧档案｜V1】"
ARCHIVE_END = "【档案结束】"
WHOLESALE_COST_SCALE = 2.0

TAGS = {
    "sweet": "甜",
    "sour": "酸",
    "bitter": "苦",
    "dry": "干爽",
    "smoky": "烟熏",
    "herbal": "草本",
    "fruity": "果香",
    "floral": "花香",
    "spiced": "辛香",
    "woody": "木香",
    "crisp": "清冽",
    "rich": "醇厚",
}

TASTE_PHRASES = {
    "sweet": "柔和的甜意先贴住舌面",
    "sour": "明亮的酸味从舌尖迅速收拢口腔",
    "bitter": "干净的苦味压住了浮在表面的甜",
    "dry": "入口收得很干，几乎不留下黏腻感",
    "smoky": "烟与微焦的气味先从鼻腔后面升起来",
    "herbal": "草叶、药材和冷香在中段慢慢展开",
    "fruity": "成熟果肉的气味在入口后变得清楚",
    "floral": "很轻的花香浮在酒液上方",
    "spiced": "辛香从喉咙一路暖到胸口",
    "woody": "旧木、烘烤和桶陈气息留在余味里",
    "crisp": "冰凉而清冽，落口很快",
    "rich": "酒体厚实，余味停留得比预想更久",
}


BASE_PRODUCTS: Dict[str, Dict[str, Any]] = {
    "house_gin": {
        "name": "白塔干金酒",
        "kind": "gin",
        "cost": 52,
        "servings": 12,
        "units": 1.25,
        "tags": ["dry", "herbal", "crisp"],
        "rarity": "常备",
        "edition": "基础版",
    },
    "amber_rum": {
        "name": "琥珀海岸朗姆",
        "kind": "rum",
        "cost": 58,
        "servings": 12,
        "units": 1.35,
        "tags": ["sweet", "spiced", "rich"],
        "rarity": "常备",
        "edition": "基础版",
    },
    "night_whisky": {
        "name": "北岸烟熏威士忌",
        "kind": "whisky",
        "cost": 72,
        "servings": 12,
        "units": 1.55,
        "tags": ["smoky", "woody", "rich"],
        "rarity": "常备",
        "edition": "基础版",
    },
    "clear_vodka": {
        "name": "极夜伏特加",
        "kind": "vodka",
        "cost": 48,
        "servings": 12,
        "units": 1.4,
        "tags": ["crisp", "dry"],
        "rarity": "常备",
        "edition": "基础版",
    },
    "sun_tequila": {
        "name": "赤日银龙舌兰",
        "kind": "tequila",
        "cost": 62,
        "servings": 12,
        "units": 1.45,
        "tags": ["herbal", "crisp", "spiced"],
        "rarity": "常备",
        "edition": "基础版",
    },
    "old_brandy": {
        "name": "旧城白兰地",
        "kind": "brandy",
        "cost": 68,
        "servings": 12,
        "units": 1.45,
        "tags": ["fruity", "woody", "rich"],
        "rarity": "常备",
        "edition": "基础版",
    },
    "red_wine": {
        "name": "暮丘红葡萄酒",
        "kind": "wine",
        "cost": 46,
        "servings": 8,
        "units": 1.05,
        "tags": ["fruity", "dry", "woody"],
        "rarity": "常备",
        "edition": "基础版",
    },
    "plum_liqueur": {
        "name": "春灯青梅酒",
        "kind": "liqueur",
        "cost": 42,
        "servings": 10,
        "units": 0.9,
        "tags": ["sweet", "sour", "fruity"],
        "rarity": "常备",
        "edition": "基础版",
    },
    "cloud_sake": {
        "name": "云川纯米吟酿",
        "kind": "sake",
        "cost": 50,
        "servings": 10,
        "units": 0.95,
        "tags": ["crisp", "floral", "dry"],
        "rarity": "常备",
        "edition": "基础版",
    },
    "stone_baijiu": {
        "name": "青石浓香白酒",
        "kind": "baijiu",
        "cost": 64,
        "servings": 14,
        "units": 1.7,
        "tags": ["rich", "fruity", "spiced"],
        "rarity": "常备",
        "edition": "基础版",
    },
    "harbor_ale": {
        "name": "旧港琥珀艾尔",
        "kind": "beer",
        "cost": 34,
        "servings": 8,
        "units": 0.7,
        "tags": ["bitter", "woody", "crisp"],
        "rarity": "常备",
        "edition": "基础版",
    },
    "orchard_cider": {
        "name": "风坡苹果西打",
        "kind": "cider",
        "cost": 36,
        "servings": 8,
        "units": 0.65,
        "tags": ["fruity", "sour", "crisp"],
        "rarity": "常备",
        "edition": "基础版",
    },
    "sun_mead": {
        "name": "日轮蜂蜜酒",
        "kind": "mead",
        "cost": 45,
        "servings": 10,
        "units": 0.9,
        "tags": ["sweet", "floral", "rich"],
        "rarity": "常备",
        "edition": "基础版",
    },
    "red_vermouth": {
        "name": "绯叶甜味美思",
        "kind": "vermouth",
        "cost": 44,
        "servings": 12,
        "units": 0.75,
        "tags": ["herbal", "bitter", "sweet"],
        "rarity": "常备",
        "edition": "基础版",
    },
    "island_shochu": {
        "name": "离岛麦烧酒",
        "kind": "shochu",
        "cost": 47,
        "servings": 12,
        "units": 1.05,
        "tags": ["dry", "woody", "crisp"],
        "rarity": "常备",
        "edition": "基础版",
    },
    "star_sparkling": {
        "name": "星屑起泡酒",
        "kind": "sparkling",
        "cost": 54,
        "servings": 8,
        "units": 0.8,
        "tags": ["floral", "fruity", "crisp"],
        "rarity": "常备",
        "edition": "基础版",
    },
}

SPECIAL_PARTS = {
    "gin": [
        ("雾庭月桂金酒", ["herbal", "floral", "dry"], "月蚀小批次"),
        ("零度星港金酒", ["crisp", "floral", "bitter"], "极光纪念版"),
        ("雨林夜航金酒", ["herbal", "sour", "spiced"], "季风限定版"),
    ],
    "rum": [
        ("沉船黑糖朗姆", ["sweet", "spiced", "smoky"], "旧海图典藏版"),
        ("双月陈年朗姆", ["rich", "fruity", "woody"], "双桶限定版"),
        ("火山甘蔗朗姆", ["smoky", "fruity", "rich"], "黑沙岛纪念版"),
    ],
    "whisky": [
        ("灰鲸泥煤威士忌", ["smoky", "woody", "bitter"], "潮汐桶限定版"),
        ("水楢回声威士忌", ["woody", "floral", "spiced"], "十二年纪念版"),
        ("极北雷鸣威士忌", ["smoky", "spiced", "dry"], "暴风桶强版"),
    ],
    "vodka": [
        ("彗尾冰晶伏特加", ["crisp", "dry", "floral"], "彗星批次"),
        ("白夜黑麦伏特加", ["dry", "spiced", "rich"], "冬至版"),
        ("深海盐雾伏特加", ["crisp", "sour", "dry"], "潜航纪念版"),
    ],
    "tequila": [
        ("蓝焰陈年龙舌兰", ["herbal", "smoky", "rich"], "火山岩桶版"),
        ("沙海银龙舌兰", ["crisp", "spiced", "floral"], "流星限定版"),
        ("仙人掌日冕龙舌兰", ["herbal", "sour", "dry"], "日食限定版"),
    ],
    "brandy": [
        ("无花果旧桶白兰地", ["fruity", "woody", "sweet"], "庄园私藏版"),
        ("时钟塔白兰地", ["rich", "spiced", "woody"], "百年纪念版"),
        ("冬宫樱桃白兰地", ["fruity", "sour", "rich"], "落雪年份版"),
    ],
    "wine": [
        ("赤月谷红葡萄酒", ["fruity", "dry", "rich"], "赤月年份版"),
        ("云上花园白葡萄酒", ["floral", "crisp", "sour"], "浮岛限定版"),
        ("黑曜庄园橙酒", ["bitter", "fruity", "woody"], "陶罐珍藏版"),
    ],
    "liqueur": [
        ("梦境蜂蜜利口酒", ["sweet", "floral", "rich"], "睡神典藏版"),
        ("苦艾绿时钟", ["herbal", "bitter", "spiced"], "午夜批次"),
        ("熔岩可可利口酒", ["sweet", "smoky", "rich"], "红龙私藏版"),
    ],
    "sake": [
        ("雪国雾酿", ["crisp", "floral", "dry"], "初雪限定版"),
        ("月兔浊酒", ["sweet", "rich", "fruity"], "月宫小批次"),
        ("深海盐花清酒", ["crisp", "sour", "floral"], "潮汐熟成版"),
    ],
    "baijiu": [
        ("长安夜宴酒", ["rich", "fruity", "spiced"], "诗仙纪念版"),
        ("青铜祭火酒", ["smoky", "herbal", "rich"], "古窖典藏版"),
        ("天门清香酒", ["dry", "crisp", "floral"], "云巅限量版"),
    ],
    "beer": [
        ("矮人熔炉黑啤", ["smoky", "bitter", "rich"], "矿坑桶藏版"),
        ("银河啤酒花艾尔", ["floral", "bitter", "crisp"], "星云鲜酿版"),
        ("雨季酸麦啤", ["sour", "fruity", "crisp"], "季风限定版"),
    ],
    "cider": [
        ("女巫林黑莓西打", ["fruity", "sour", "herbal"], "月圆批次"),
        ("金苹果干型西打", ["dry", "fruity", "crisp"], "丰收限定版"),
        ("时间梨园西打", ["sweet", "floral", "woody"], "倒流年份版"),
    ],
    "mead": [
        ("瓦尔哈拉蜂蜜酒", ["sweet", "spiced", "rich"], "英灵宴会版"),
        ("沙漠藏红花蜜酒", ["floral", "spiced", "dry"], "绿洲私藏版"),
        ("彗星蓝花蜜酒", ["floral", "sour", "crisp"], "百年回归版"),
    ],
    "vermouth": [
        ("午夜苦橙美思", ["bitter", "fruity", "herbal"], "钟楼限定版"),
        ("玫瑰航线干味美思", ["dry", "floral", "spiced"], "远洋批次"),
        ("炼金师琥珀美思", ["herbal", "rich", "woody"], "秘方典藏版"),
    ],
    "shochu": [
        ("火山甘薯烧酒", ["smoky", "sweet", "woody"], "黑土熟成版"),
        ("雪岭荞麦烧酒", ["dry", "bitter", "crisp"], "冬藏版"),
        ("海风黑糖烧酒", ["sweet", "fruity", "crisp"], "离岛限定版"),
    ],
    "sparkling": [
        ("极光粉红气泡酒", ["floral", "fruity", "crisp"], "极夜纪念版"),
        ("深空零重力起泡酒", ["dry", "crisp", "herbal"], "轨道站限定版"),
        ("王冠金箔香槟", ["rich", "floral", "dry"], "加冕典藏版"),
    ],
}

RECIPES: Dict[str, Dict[str, Any]] = {
    "gimlet": {
        "name": "冷月吉姆雷特",
        "kind": "gin",
        "tags": ["sour", "dry", "herbal", "crisp"],
        "price": 31,
        "unit_factor": 0.9,
    },
    "daiquiri": {
        "name": "白浪戴奎里",
        "kind": "rum",
        "tags": ["sour", "sweet", "fruity", "crisp"],
        "price": 30,
        "unit_factor": 0.9,
    },
    "highball": {
        "name": "北风高球",
        "kind": "whisky",
        "tags": ["smoky", "dry", "crisp"],
        "price": 33,
        "unit_factor": 0.75,
    },
    "old_fashioned": {
        "name": "旧日低语",
        "kind": "whisky",
        "tags": ["bitter", "sweet", "woody", "spiced"],
        "price": 39,
        "unit_factor": 1.0,
    },
    "vodka_tonic": {
        "name": "极夜汤力",
        "kind": "vodka",
        "tags": ["bitter", "dry", "crisp"],
        "price": 28,
        "unit_factor": 0.8,
    },
    "paloma": {
        "name": "赤日帕洛玛",
        "kind": "tequila",
        "tags": ["sour", "fruity", "crisp"],
        "price": 32,
        "unit_factor": 0.85,
    },
    "sidecar": {
        "name": "旧城边车",
        "kind": "brandy",
        "tags": ["sour", "fruity", "dry", "rich"],
        "price": 37,
        "unit_factor": 0.95,
    },
    "wine_spritz": {
        "name": "暮丘气泡",
        "kind": "wine",
        "tags": ["fruity", "floral", "crisp"],
        "price": 26,
        "unit_factor": 0.75,
    },
    "plum_soda": {
        "name": "春灯苏打",
        "kind": "liqueur",
        "tags": ["sweet", "sour", "fruity", "crisp"],
        "price": 24,
        "unit_factor": 0.7,
    },
    "sake_fizz": {
        "name": "雪灯清酒菲士",
        "kind": "sake",
        "tags": ["sour", "floral", "crisp"],
        "price": 29,
        "unit_factor": 0.78,
    },
    "baijiu_sour": {
        "name": "长安酸",
        "kind": "baijiu",
        "tags": ["sour", "rich", "fruity"],
        "price": 36,
        "unit_factor": 0.72,
    },
    "beer_flip": {
        "name": "熔炉翻转",
        "kind": "beer",
        "tags": ["rich", "bitter", "spiced"],
        "price": 25,
        "unit_factor": 0.82,
    },
    "cider_cooler": {
        "name": "果园晚风",
        "kind": "cider",
        "tags": ["fruity", "sour", "crisp"],
        "price": 23,
        "unit_factor": 0.75,
    },
    "mead_toddy": {
        "name": "蜂巢热托地",
        "kind": "mead",
        "tags": ["sweet", "spiced", "rich"],
        "price": 30,
        "unit_factor": 0.88,
    },
    "vermouth_cobbler": {
        "name": "绯叶库伯勒",
        "kind": "vermouth",
        "tags": ["herbal", "fruity", "crisp"],
        "price": 28,
        "unit_factor": 0.8,
    },
    "shochu_highball": {
        "name": "离岛风球",
        "kind": "shochu",
        "tags": ["dry", "woody", "crisp"],
        "price": 27,
        "unit_factor": 0.72,
    },
    "sparkling_bellini": {
        "name": "星屑贝里尼",
        "kind": "sparkling",
        "tags": ["fruity", "floral", "sweet"],
        "price": 32,
        "unit_factor": 0.8,
    },
}

# 现实酒吧中长期流传的经典款。使用紧凑表维护，但进入游戏后与原有配方
# 完全相同：会根据实际库存中的基酒改变风味、酒精量和售价。
_REAL_COCKTAIL_EXPANSION = [
    ("dry_martini", "干马天尼", "gin", ["dry", "herbal", "crisp"], 38, 1.00),
    ("negroni", "尼格罗尼", "gin", ["bitter", "herbal", "rich"], 39, 0.95),
    ("tom_collins", "汤姆柯林斯", "gin", ["sour", "sweet", "crisp"], 32, 0.78),
    ("aviation", "航空", "gin", ["floral", "sour", "dry"], 40, 0.92),
    ("french_75", "法兰西75", "gin", ["dry", "sour", "crisp"], 42, 0.86),
    ("gin_fizz", "金菲士", "gin", ["sour", "sweet", "crisp"], 31, 0.76),
    ("bees_knees", "蜜蜂之膝", "gin", ["sweet", "sour", "floral"], 35, 0.84),
    ("last_word", "遗言", "gin", ["herbal", "sour", "rich"], 43, 0.95),
    ("mojito", "莫吉托", "rum", ["herbal", "sour", "sweet", "crisp"], 32, 0.74),
    ("mai_tai", "迈泰", "rum", ["fruity", "sour", "rich"], 43, 1.00),
    ("cuba_libre", "自由古巴", "rum", ["sweet", "sour", "spiced"], 30, 0.82),
    ("pina_colada", "椰林飘香", "rum", ["sweet", "fruity", "rich"], 36, 0.78),
    ("dark_stormy", "黑暗风暴", "rum", ["spiced", "sour", "rich"], 35, 0.88),
    ("hurricane", "飓风", "rum", ["fruity", "sweet", "sour"], 41, 1.05),
    ("planters_punch", "种植园潘趣", "rum", ["fruity", "spiced", "sour"], 39, 0.96),
    ("caipirinha", "卡琵莉亚", "rum", ["sour", "sweet", "crisp"], 34, 0.92),
    ("manhattan", "曼哈顿", "whisky", ["woody", "bitter", "rich"], 43, 1.00),
    ("whisky_sour", "威士忌酸", "whisky", ["sour", "sweet", "rich"], 38, 0.90),
    ("mint_julep", "薄荷朱利普", "whisky", ["herbal", "sweet", "crisp"], 39, 0.92),
    ("irish_coffee", "爱尔兰咖啡", "whisky", ["bitter", "sweet", "rich"], 42, 0.84),
    ("rusty_nail", "锈钉", "whisky", ["sweet", "herbal", "rich"], 44, 1.02),
    ("boulevardier", "林荫大道", "whisky", ["bitter", "woody", "rich"], 45, 1.00),
    ("rob_roy", "罗布·罗伊", "whisky", ["woody", "herbal", "dry"], 42, 0.98),
    ("penicillin", "盘尼西林", "whisky", ["smoky", "sour", "sweet"], 46, 0.94),
    ("moscow_mule", "莫斯科骡子", "vodka", ["spiced", "sour", "crisp"], 33, 0.78),
    ("bloody_mary", "血腥玛丽", "vodka", ["spiced", "sour", "rich"], 36, 0.82),
    ("cosmopolitan", "大都会", "vodka", ["fruity", "sour", "crisp"], 38, 0.86),
    ("espresso_martini", "浓缩咖啡马天尼", "vodka", ["bitter", "sweet", "rich"], 41, 0.90),
    ("white_russian", "白俄罗斯", "vodka", ["sweet", "rich", "bitter"], 37, 0.92),
    ("black_russian", "黑俄罗斯", "vodka", ["bitter", "sweet", "rich"], 35, 0.96),
    ("screwdriver", "螺丝起子", "vodka", ["fruity", "sweet", "crisp"], 29, 0.75),
    ("sea_breeze", "海风", "vodka", ["fruity", "sour", "crisp"], 31, 0.74),
    ("margarita", "玛格丽特", "tequila", ["sour", "dry", "crisp"], 37, 0.88),
    ("tequila_sunrise", "龙舌兰日出", "tequila", ["fruity", "sweet", "crisp"], 34, 0.80),
    ("el_diablo", "暗黑破坏神", "tequila", ["fruity", "spiced", "sour"], 39, 0.90),
    ("ranch_water", "牧场水", "tequila", ["dry", "sour", "crisp"], 32, 0.74),
    ("brandy_alexander", "白兰地亚历山大", "brandy", ["sweet", "rich", "spiced"], 42, 0.88),
    ("stinger", "毒刺", "brandy", ["herbal", "sweet", "rich"], 40, 0.94),
    ("sazerac", "萨泽拉克", "brandy", ["bitter", "herbal", "rich"], 46, 1.02),
    ("between_sheets", "床笫之间", "brandy", ["sour", "fruity", "rich"], 44, 0.98),
    ("sangria", "桑格利亚", "wine", ["fruity", "sweet", "spiced"], 31, 0.76),
    ("kalimotxo", "卡里莫求", "wine", ["sweet", "fruity", "rich"], 24, 0.70),
    ("kir", "基尔", "wine", ["fruity", "sweet", "dry"], 30, 0.78),
    ("wine_spritzer", "葡萄酒苏打", "wine", ["dry", "fruity", "crisp"], 25, 0.66),
    ("grasshopper", "蚱蜢", "liqueur", ["sweet", "herbal", "rich"], 34, 0.82),
    ("amaretto_sour", "杏仁酸", "liqueur", ["sweet", "sour", "rich"], 33, 0.86),
    ("b_52", "B-52", "liqueur", ["sweet", "bitter", "rich"], 36, 0.90),
    ("aperol_spritz", "阿佩罗橙光", "sparkling", ["bitter", "fruity", "crisp"], 35, 0.76),
    ("mimosa", "含羞草", "sparkling", ["fruity", "sweet", "crisp"], 31, 0.68),
    ("kir_royale", "皇家基尔", "sparkling", ["fruity", "dry", "crisp"], 38, 0.76),
    ("sake_martini", "清酒马天尼", "sake", ["dry", "floral", "crisp"], 35, 0.90),
    ("chu_hi", "烧酒嗨棒", "shochu", ["sour", "dry", "crisp"], 27, 0.72),
    ("shandy", "香迪", "beer", ["sour", "sweet", "crisp"], 22, 0.62),
    ("snakebite", "蛇咬", "cider", ["fruity", "bitter", "crisp"], 25, 0.74),
    ("americano", "美式鸡尾酒", "vermouth", ["bitter", "herbal", "crisp"], 32, 0.78),
]

RECIPES.update(
    {
        item[0]: {
            "name": item[1],
            "kind": item[2],
            "tags": item[3],
            "price": item[4],
            "unit_factor": item[5],
        }
        for item in _REAL_COCKTAIL_EXPANSION
    }
)

# 影视、文学、游戏、神话与原创幻想世界中的酒。它们作为游商或商店限定
# 瓶装酒出现，不保证每次开档都能遇见。
_FICTIONAL_DRINK_EXPANSION = {
    "beer": [
        ("黄油啤酒", ["sweet", "spiced", "rich"], "魔法村冬季版"),
        ("绿龙酒馆黑啤", ["smoky", "bitter", "rich"], "冒险者桶藏版"),
        ("星际港口泡沫酒", ["crisp", "sour", "fruity"], "零重力罐装版"),
        ("英雄庆功麦酒", ["sweet", "woody", "rich"], "终章纪念版"),
    ],
    "whisky": [
        ("火焰威士忌", ["smoky", "spiced", "rich"], "巫师酒馆珍藏版"),
        ("胜利牌琴酒式烈酒", ["dry", "bitter", "herbal"], "大洋国配给版"),
        ("侦探壁炉威士忌", ["woody", "smoky", "dry"], "贝克街私藏版"),
        ("西部仿生人威士忌", ["bitter", "woody", "rich"], "记忆测试版"),
    ],
    "rum": [
        ("宾克斯之酒", ["fruity", "sweet", "spiced"], "海盗合唱版"),
        ("黑珍珠船长朗姆", ["smoky", "sweet", "rich"], "诅咒金币版"),
        ("骷髅岛甘蔗酒", ["fruity", "sour", "smoky"], "失落航线版"),
        ("红线尽头朗姆", ["spiced", "rich", "woody"], "伟大航路典藏版"),
    ],
    "gin": [
        ("潘银河系含漱爆破酒", ["sour", "bitter", "spiced"], "宇宙旅行指南版"),
        ("罗慕兰蓝麦酒", ["crisp", "bitter", "floral"], "中立区违禁版"),
        ("银翼霓虹琴酒", ["dry", "smoky", "bitter"], "雨夜复制人版"),
        ("十三号时间琴酒", ["herbal", "sour", "dry"], "循环限定版"),
    ],
    "wine": [
        ("醉生梦死", ["fruity", "woody", "bitter"], "荒漠记忆版"),
        ("红堡夏日葡萄酒", ["fruity", "sweet", "spiced"], "王室宴会版"),
        ("吸血伯爵夜宴红酒", ["rich", "fruity", "woody"], "永夜年份版"),
        ("精灵月光葡萄酒", ["floral", "crisp", "dry"], "银叶森林版"),
    ],
    "mead": [
        ("琼浆玉露", ["sweet", "floral", "rich"], "天宫宴饮版"),
        ("英灵殿无尽蜜酒", ["sweet", "spiced", "rich"], "诸神黄昏前夜版"),
        ("黄金苹果蜜酒", ["fruity", "sweet", "floral"], "永恒青春版"),
        ("龙巢火蜜酒", ["smoky", "spiced", "sweet"], "鳞火封蜡版"),
    ],
    "sake": [
        ("忘川酒", ["bitter", "floral", "dry"], "彼岸摆渡版"),
        ("月读清酒", ["floral", "crisp", "bitter"], "无限夜限定版"),
        ("狐狸婚礼浊酒", ["sweet", "fruity", "floral"], "太阳雨批次"),
        ("百鬼夜行杯中月", ["herbal", "spiced", "dry"], "盂兰夜限定版"),
    ],
    "liqueur": [
        ("莫洛托夫牛奶利口酒", ["sweet", "rich", "spiced"], "发条夜班版"),
        ("爱神迷情剂", ["floral", "sweet", "fruity"], "误饮警告版"),
        ("记忆删除剂", ["bitter", "herbal", "crisp"], "黑衣机构封存版"),
        ("梦境第三层利口酒", ["sweet", "smoky", "floral"], "陀螺未停版"),
    ],
}

for _kind, _items in _FICTIONAL_DRINK_EXPANSION.items():
    SPECIAL_PARTS[_kind].extend(_items)

DECOR_DEFS: Dict[str, Dict[str, Any]] = {
    "neon": {
        "name": "跨世界霓虹招牌",
        "cost": 120,
        "tags": ["crisp", "fruity"],
        "desc": "门外不同文字会自动变成来客能读懂的名字",
    },
    "jukebox": {
        "name": "旧宇宙点唱机",
        "cost": 180,
        "tags": ["rich", "spiced"],
        "desc": "偶尔播放尚未诞生或早已失传的歌",
    },
    "aquarium": {
        "name": "微型星海水族箱",
        "cost": 210,
        "tags": ["crisp", "floral"],
        "desc": "让孤独或非人来客更愿意停留",
    },
    "mural": {
        "name": "文明长卷壁画",
        "cost": 150,
        "tags": ["woody", "herbal"],
        "desc": "画面会随着来客的记忆悄悄改变",
    },
    "fireplace": {
        "name": "不熄余烬壁炉",
        "cost": 260,
        "tags": ["smoky", "rich"],
        "desc": "为来自寒冷世界的客人保留一块暖处",
    },
    "garden": {
        "name": "倒悬香草花园",
        "cost": 230,
        "tags": ["herbal", "floral"],
        "desc": "提供会随月相变化的鲜香草",
    },
    "clock": {
        "name": "多时间线挂钟",
        "cost": 320,
        "tags": ["bitter", "dry"],
        "desc": "每根指针显示一个来客故乡的此刻",
    },
    "piano": {
        "name": "会记住触碰的旧钢琴",
        "cost": 380,
        "tags": ["woody", "rich"],
        "desc": "能续上客人多年以前没有弹完的旋律",
    },
}

DECOR_DEFS.update(
    {
        "rug": {
            "name": "耐磨深色地毯",
            "cost": 95,
            "category": "soft",
            "rarity": "常见",
            "condition": "全新",
            "maintenance": 1,
            "tags": ["woody", "rich"],
            "desc": "压住脚步声，让谈话不容易被邻桌听清",
        },
        "sofa": {
            "name": "二手皮革长沙发",
            "cost": 180,
            "category": "soft",
            "rarity": "常见",
            "condition": "二手良好",
            "maintenance": 2,
            "tags": ["woody", "rich"],
            "desc": "有使用痕迹，但足够舒服，适合愿意久坐的回头客",
        },
        "projector": {
            "name": "短焦故事投影仪",
            "cost": 280,
            "category": "equipment",
            "rarity": "常见",
            "condition": "全新",
            "maintenance": 3,
            "tags": ["crisp", "floral"],
            "desc": "可播放影像，也能把来客允许公开的故事投到幕布上",
        },
        "sound_system": {
            "name": "四声道酒吧音响",
            "cost": 360,
            "category": "equipment",
            "rarity": "常见",
            "condition": "全新",
            "maintenance": 4,
            "tags": ["rich", "spiced"],
            "desc": "改善音乐层次，也会增加每次营业的维护支出",
        },
        "ice_machine": {
            "name": "商用制冰机",
            "cost": 520,
            "category": "hard",
            "rarity": "常见",
            "condition": "全新",
            "maintenance": 4,
            "tags": ["crisp", "dry"],
            "desc": "降低常规调酒的耗材压力，让冰的状态更加稳定",
        },
        "new_counter": {
            "name": "黑胡桃木吧台改造",
            "cost": 880,
            "category": "hard",
            "rarity": "少见",
            "condition": "定制",
            "maintenance": 5,
            "tags": ["woody", "rich"],
            "desc": "扩大操作面与座位，属于真正的硬装工程",
        },
        "floating_candles": {
            "name": "魔法学院风悬浮烛群",
            "cost": 240,
            "category": "soft",
            "rarity": "少见",
            "condition": "施法稳定",
            "maintenance": 2,
            "tags": ["floral", "smoky"],
            "desc": "烛火会避开客人的头发，但偶尔对魔法来客眨眼",
        },
        "pixel_aquarium": {
            "name": "二维像素水族屏",
            "cost": 190,
            "category": "soft",
            "rarity": "少见",
            "condition": "全新",
            "maintenance": 1,
            "tags": ["crisp", "fruity"],
            "desc": "鱼只在二维平面里游动，关灯后会跑进别的屏幕",
        },
        "starship_window": {
            "name": "退役星舰舷窗",
            "cost": 460,
            "category": "hard",
            "rarity": "稀有",
            "condition": "退役翻新",
            "maintenance": 4,
            "tags": ["crisp", "bitter"],
            "desc": "窗外并非墙面，而是一段经过安全封存的深空航线",
        },
        "memory_projector": {
            "name": "四维记忆放映机",
            "cost": 720,
            "category": "equipment",
            "rarity": "典藏",
            "condition": "来源不明",
            "maintenance": 6,
            "tags": ["floral", "bitter"],
            "desc": "只能在本人同意时播放一段记忆，错误使用会制造冲突",
        },
        "ghost_seat": {
            "name": "亡灵专用靠窗座",
            "cost": 330,
            "category": "soft",
            "rarity": "稀有",
            "condition": "阴气完好",
            "maintenance": 2,
            "tags": ["smoky", "dry"],
            "desc": "活人坐下只会觉得冷，亡者却能短暂获得重量",
        },
        "gravity_floor": {
            "name": "低重力舞池模块",
            "cost": 980,
            "category": "hard",
            "rarity": "典藏",
            "condition": "军转民",
            "maintenance": 8,
            "tags": ["crisp", "spiced"],
            "desc": "可把一小块地面的重力调低，刺激但维护昂贵",
        },
    }
)

TRAVELING_VENDORS = [
    {
        "id": "fox_caravan",
        "name": "九尾狐的夜行酒车",
        "discount": 0.76,
        "intro": "九尾狐把挂满铜铃的小车停在后门，声称今晚的货绝不等第二次月亮。",
    },
    {
        "id": "star_peddler",
        "name": "背星箱的行脚商",
        "discount": 0.72,
        "intro": "一个披着星图雨衣的人敲了三下门，背箱里每只瓶子都在轻微失重。",
    },
    {
        "id": "old_cellarmaster",
        "name": "迷路的老酒窖师",
        "discount": 0.82,
        "intro": "白发酒窖师推着吱呀作响的木车出现，说自己又从一条不存在的街绕了回来。",
    },
    {
        "id": "rift_siblings",
        "name": "裂隙商队双胞胎",
        "discount": 0.79,
        "intro": "两个说话完全同步的商人从窄巷裂隙里挤出来，把几只典藏箱摆到门边。",
    },
]

UPGRADE_DEFS: Dict[str, Dict[str, Any]] = {
    "cellar": {
        "name": "扩建酒窖",
        "costs": [160, 320, 560],
        "desc": "每级增加4个不同酒款的储藏位置",
    },
    "glassware": {
        "name": "专业杯具",
        "costs": [140, 300, 520],
        "desc": "每级提高调酒呈现与顾客满意度",
    },
    "quiet_booth": {
        "name": "安静包间",
        "costs": [180, 360],
        "desc": "更容易与来客建立信任、谈出秘密",
    },
    "portal": {
        "name": "万界门廊",
        "costs": [220, 460, 760],
        "desc": "提高稀有来客频率，但不排除任何人",
    },
    "stage": {
        "name": "小型舞台",
        "costs": [240, 480],
        "desc": "提高多人同场和冲突事件的频率",
    },
    "kitchen": {
        "name": "深夜厨房",
        "costs": [130, 280],
        "desc": "提供更好的食物，缓和醉酒不适",
    },
}


BUILTIN_GUESTS: List[Dict[str, Any]] = [
    {
        "id": "li_bai",
        "name": "李白",
        "origin": "盛唐·历史来客（虚构化重构）",
        "likes": ["rich", "fruity", "spiced"],
        "dislikes": ["crisp"],
        "budget": 62,
        "rarity": "rare",
        "temperament": "豪放而敏锐",
        "ethos": "free",
    },
    {
        "id": "cleopatra",
        "name": "克利奥帕特拉七世",
        "origin": "托勒密埃及·历史来客（虚构化重构）",
        "likes": ["floral", "spiced", "rich"],
        "dislikes": ["dry"],
        "budget": 88,
        "rarity": "rare",
        "temperament": "从容、善于试探",
        "ethos": "power",
    },
    {
        "id": "ada_lovelace",
        "name": "阿达·洛芙莱斯",
        "origin": "十九世纪伦敦·历史来客（虚构化重构）",
        "likes": ["bitter", "floral", "dry"],
        "dislikes": ["sweet"],
        "budget": 54,
        "rarity": "uncommon",
        "temperament": "好奇、精确而富于想象",
        "ethos": "reason",
    },
    {
        "id": "ibn_sina",
        "name": "伊本·西那",
        "origin": "波斯文明·历史来客（虚构化重构）",
        "likes": ["herbal", "bitter", "floral"],
        "dislikes": ["smoky"],
        "budget": 48,
        "rarity": "rare",
        "temperament": "克制、观察入微",
        "ethos": "healing",
    },
    {
        "id": "loki_myth",
        "name": "洛基",
        "origin": "北欧神话·神话来客",
        "likes": ["spiced", "smoky", "sour"],
        "dislikes": ["dry"],
        "budget": 72,
        "rarity": "rare",
        "temperament": "聪明、危险、喜欢搅局",
        "ethos": "chaos",
    },
    {
        "id": "chang_e",
        "name": "月宫旅人",
        "origin": "东方月宫传说·神话来客",
        "likes": ["floral", "crisp", "fruity"],
        "dislikes": ["smoky"],
        "budget": 50,
        "rarity": "uncommon",
        "temperament": "安静、疏离",
        "ethos": "solitude",
    },
    {
        "id": "fox_spirit",
        "name": "九尾狐商人",
        "origin": "第七码头·异类来客",
        "likes": ["sweet", "fruity", "smoky"],
        "dislikes": ["bitter"],
        "budget": 67,
        "rarity": "uncommon",
        "temperament": "亲切得过分，绝不做亏本买卖",
        "ethos": "trade",
    },
    {
        "id": "retired_dragon",
        "name": "退休红龙",
        "origin": "灰烬山脉·高魔世界",
        "likes": ["smoky", "spiced", "rich"],
        "dislikes": ["floral"],
        "budget": 95,
        "rarity": "rare",
        "temperament": "骄傲、怀旧、讨厌被奉承",
        "ethos": "pride",
    },
    {
        "id": "unit_7",
        "name": "航行单元-7",
        "origin": "远星联合舰队·机械生命",
        "likes": ["crisp", "bitter", "dry"],
        "dislikes": ["sweet"],
        "budget": 46,
        "rarity": "common",
        "temperament": "字面、认真、正在学习幽默",
        "ethos": "order",
    },
    {
        "id": "time_courier",
        "name": "迟到三百年的邮差",
        "origin": "断裂时间线·人类",
        "likes": ["woody", "fruity", "sour"],
        "dislikes": ["spiced"],
        "budget": 42,
        "rarity": "common",
        "temperament": "疲惫、固执地守着一封信",
        "ethos": "duty",
    },
    {
        "id": "ordinary_teacher",
        "name": "下晚课的老师",
        "origin": "现代城市·普通来客",
        "likes": ["fruity", "sour", "crisp"],
        "dislikes": ["rich"],
        "budget": 36,
        "rarity": "common",
        "temperament": "清醒、累，但仍愿意听人说话",
        "ethos": "care",
    },
    {
        "id": "memory_diver",
        "name": "记忆潜水员",
        "origin": "第五信息海·数据生命",
        "likes": ["bitter", "herbal", "smoky"],
        "dislikes": ["floral"],
        "budget": 58,
        "rarity": "uncommon",
        "temperament": "常把别人的回忆误认为自己的",
        "ethos": "memory",
    },
    {
        "id": "su_shi",
        "name": "苏轼",
        "origin": "北宋·历史来客（虚构化重构）",
        "likes": ["rich", "fruity", "herbal"],
        "dislikes": ["dry"],
        "budget": 56,
        "rarity": "uncommon",
        "temperament": "豁达、爱吃，也会在笑里藏住失意",
        "ethos": "resilience",
    },
    {
        "id": "wu_zetian",
        "name": "武则天",
        "origin": "唐与武周·历史来客（虚构化重构）",
        "likes": ["floral", "bitter", "rich"],
        "dislikes": ["sour"],
        "budget": 92,
        "rarity": "rare",
        "temperament": "威严、耐心，习惯看穿试探",
        "ethos": "power",
    },
    {
        "id": "leonardo",
        "name": "列奥纳多·达·芬奇",
        "origin": "文艺复兴时期·历史来客（虚构化重构）",
        "likes": ["herbal", "floral", "sour"],
        "dislikes": ["rich"],
        "budget": 61,
        "rarity": "rare",
        "temperament": "什么都想拆开研究，常忘记喝完杯里的酒",
        "ethos": "curiosity",
    },
    {
        "id": "murasaki",
        "name": "紫式部",
        "origin": "平安时代·历史来客（虚构化重构）",
        "likes": ["floral", "dry", "fruity"],
        "dislikes": ["smoky"],
        "budget": 52,
        "rarity": "uncommon",
        "temperament": "寡言而敏锐，擅长观察关系里的暗流",
        "ethos": "story",
    },
    {
        "id": "sappho",
        "name": "萨福",
        "origin": "古希腊莱斯博斯岛·历史来客（虚构化重构）",
        "likes": ["floral", "fruity", "sour"],
        "dislikes": ["bitter"],
        "budget": 49,
        "rarity": "rare",
        "temperament": "热烈、坦率，对语言的节奏极其挑剔",
        "ethos": "desire",
    },
    {
        "id": "rumi",
        "name": "鲁米",
        "origin": "十三世纪波斯·历史来客（虚构化重构）",
        "likes": ["sweet", "spiced", "floral"],
        "dislikes": ["crisp"],
        "budget": 47,
        "rarity": "rare",
        "temperament": "温柔而炽烈，总把问题带回人的内心",
        "ethos": "love",
    },
    {
        "id": "shakespeare",
        "name": "威廉·莎士比亚",
        "origin": "伊丽莎白时代伦敦·历史来客（虚构化重构）",
        "likes": ["rich", "bitter", "fruity"],
        "dislikes": ["dry"],
        "budget": 58,
        "rarity": "uncommon",
        "temperament": "健谈、戏剧化，容易把邻桌争吵写成独白",
        "ethos": "theatre",
    },
    {
        "id": "tesla",
        "name": "尼古拉·特斯拉",
        "origin": "二十世纪纽约·历史来客（虚构化重构）",
        "likes": ["crisp", "bitter", "dry"],
        "dislikes": ["sweet"],
        "budget": 45,
        "rarity": "rare",
        "temperament": "克制、孤独，对规律与数字近乎执拗",
        "ethos": "invention",
    },
    {
        "id": "frida_kahlo",
        "name": "弗里达·卡罗",
        "origin": "二十世纪墨西哥·历史来客（虚构化重构）",
        "likes": ["spiced", "fruity", "smoky"],
        "dislikes": ["crisp"],
        "budget": 63,
        "rarity": "uncommon",
        "temperament": "锋利、诚实，不允许别人替她解释痛苦",
        "ethos": "self",
    },
    {
        "id": "joan_of_arc",
        "name": "贞德",
        "origin": "十五世纪法国·历史来客（虚构化重构）",
        "likes": ["dry", "herbal", "crisp"],
        "dislikes": ["sweet"],
        "budget": 38,
        "rarity": "rare",
        "temperament": "年轻、坚定，对自己的声音深信不疑",
        "ethos": "faith",
    },
    {
        "id": "sun_wukong",
        "name": "孙悟空",
        "origin": "东方神魔传说·神话来客",
        "likes": ["fruity", "spiced", "rich"],
        "dislikes": ["bitter"],
        "budget": 73,
        "rarity": "rare",
        "temperament": "好胜、聪明，最烦繁文缛节",
        "ethos": "freedom",
    },
    {
        "id": "anansi",
        "name": "阿南西",
        "origin": "西非与加勒比传说·神话来客",
        "likes": ["sweet", "spiced", "bitter"],
        "dislikes": ["dry"],
        "budget": 55,
        "rarity": "uncommon",
        "temperament": "以故事换酒，也会把别人的秘密织进网里",
        "ethos": "trick",
    },
    {
        "id": "athena",
        "name": "雅典娜",
        "origin": "古希腊神话·神话来客",
        "likes": ["dry", "herbal", "woody"],
        "dislikes": ["sweet"],
        "budget": 82,
        "rarity": "rare",
        "temperament": "冷静、讲求策略，不轻易接受奉承",
        "ethos": "strategy",
    },
    {
        "id": "odin",
        "name": "奥丁",
        "origin": "北欧神话·神话来客",
        "likes": ["smoky", "bitter", "rich"],
        "dislikes": ["floral"],
        "budget": 90,
        "rarity": "rare",
        "temperament": "沉默而不安，为知识愿意付出危险代价",
        "ethos": "knowledge",
    },
    {
        "id": "inanna",
        "name": "伊南娜",
        "origin": "苏美尔神话·神话来客",
        "likes": ["floral", "rich", "spiced"],
        "dislikes": ["crisp"],
        "budget": 86,
        "rarity": "rare",
        "temperament": "华丽、强势，从不把欲望说成罪过",
        "ethos": "desire",
    },
    {
        "id": "quetzalcoatl",
        "name": "羽蛇神",
        "origin": "中部美洲神话·神话来客",
        "likes": ["herbal", "fruity", "crisp"],
        "dislikes": ["smoky"],
        "budget": 78,
        "rarity": "rare",
        "temperament": "平静、古老，对文明兴衰有漫长耐心",
        "ethos": "creation",
    },
    {
        "id": "sedna",
        "name": "塞德娜",
        "origin": "因纽特神话·海底来客",
        "likes": ["crisp", "sour", "bitter"],
        "dislikes": ["smoky"],
        "budget": 64,
        "rarity": "rare",
        "temperament": "疏离、戒备，厌恶未经允许的触碰",
        "ethos": "ocean",
    },
    {
        "id": "anubis",
        "name": "阿努比斯",
        "origin": "古埃及神话·神话来客",
        "likes": ["dry", "woody", "spiced"],
        "dislikes": ["sweet"],
        "budget": 75,
        "rarity": "uncommon",
        "temperament": "公正、克制，能听见人话语里的重量",
        "ethos": "judgment",
    },
    {
        "id": "alice",
        "name": "爱丽丝",
        "origin": "仙境·经典文学来客",
        "likes": ["sweet", "sour", "floral"],
        "dislikes": ["smoky"],
        "budget": 32,
        "rarity": "uncommon",
        "temperament": "好奇、讲理，但已经习惯荒谬",
        "ethos": "wonder",
    },
    {
        "id": "sherlock_holmes",
        "name": "夏洛克·福尔摩斯",
        "origin": "贝克街·经典文学来客",
        "likes": ["dry", "bitter", "herbal"],
        "dislikes": ["sweet"],
        "budget": 59,
        "rarity": "rare",
        "temperament": "敏锐、傲慢，会从杯沿推断老板昨晚几点睡",
        "ethos": "reason",
    },
    {
        "id": "dracula",
        "name": "德古拉伯爵",
        "origin": "特兰西瓦尼亚·经典文学来客",
        "likes": ["rich", "fruity", "woody"],
        "dislikes": ["crisp"],
        "budget": 97,
        "rarity": "rare",
        "temperament": "古老、礼貌，礼貌本身带着威胁",
        "ethos": "hunger",
    },
    {
        "id": "don_quixote",
        "name": "堂吉诃德",
        "origin": "拉曼恰·经典文学来客",
        "likes": ["fruity", "spiced", "dry"],
        "dislikes": ["bitter"],
        "budget": 35,
        "rarity": "common",
        "temperament": "庄严、善良，把冰桶认成被困的骑士",
        "ethos": "ideal",
    },
    {
        "id": "captain_nemo",
        "name": "尼摩船长",
        "origin": "鹦鹉螺号·经典文学来客",
        "likes": ["crisp", "bitter", "smoky"],
        "dislikes": ["sweet"],
        "budget": 71,
        "rarity": "rare",
        "temperament": "博学、孤绝，对陆地政权保持敌意",
        "ethos": "exile",
    },
    {
        "id": "frankenstein_creature",
        "name": "无名造物",
        "origin": "极地航线·经典文学来客",
        "likes": ["woody", "floral", "rich"],
        "dislikes": ["bitter"],
        "budget": 41,
        "rarity": "rare",
        "temperament": "敏感、渴望被理解，对怜悯格外警惕",
        "ethos": "belonging",
    },
    {
        "id": "last_cartographer",
        "name": "末日地图师",
        "origin": "被海水吞没的第九大陆·人类",
        "likes": ["dry", "woody", "sour"],
        "dislikes": ["sweet"],
        "budget": 44,
        "rarity": "common",
        "temperament": "谨慎，仍在绘制已经不存在的道路",
        "ethos": "record",
    },
    {
        "id": "dream_taxer",
        "name": "梦境税务官",
        "origin": "睡眠管理局·概念生命",
        "likes": ["bitter", "sweet", "herbal"],
        "dislikes": ["crisp"],
        "budget": 69,
        "rarity": "uncommon",
        "temperament": "一板一眼，会查验客人昨夜梦境的完税证明",
        "ethos": "bureaucracy",
    },
    {
        "id": "blackhole_singer",
        "name": "黑洞边缘的歌者",
        "origin": "天鹅座回声带·引力生命",
        "likes": ["rich", "smoky", "floral"],
        "dislikes": ["dry"],
        "budget": 88,
        "rarity": "rare",
        "temperament": "说话极慢，每个音节都像被时间拉长",
        "ethos": "gravity",
    },
    {
        "id": "palace_cook",
        "name": "失业的御膳房厨子",
        "origin": "已覆灭王朝·普通人",
        "likes": ["spiced", "sour", "rich"],
        "dislikes": ["floral"],
        "budget": 39,
        "rarity": "common",
        "temperament": "嘴硬、手艺极好，正在重新学习为自己做饭",
        "ethos": "survival",
    },
    {
        "id": "retired_villain",
        "name": "退休反派",
        "origin": "停更的英雄宇宙·前终极敌人",
        "likes": ["bitter", "smoky", "sweet"],
        "dislikes": ["crisp"],
        "budget": 76,
        "rarity": "uncommon",
        "temperament": "厌倦宏大计划，只想抱怨英雄不报销加班费",
        "ethos": "disillusion",
    },
    {
        "id": "climate_refugee",
        "name": "来自2089年的气候难民",
        "origin": "未来沿海迁徙带·人类",
        "likes": ["crisp", "fruity", "sour"],
        "dislikes": ["smoky"],
        "budget": 33,
        "rarity": "common",
        "temperament": "务实、警觉，对一杯干净的冰水也心怀感激",
        "ethos": "future",
    },
    {
        "id": "ghost_radio",
        "name": "午夜幽灵电台主持人",
        "origin": "不存在的FM 00.0·幽灵",
        "likes": ["woody", "bitter", "floral"],
        "dislikes": ["sweet"],
        "budget": 51,
        "rarity": "uncommon",
        "temperament": "声音温柔，只为仍醒着的人播送失踪消息",
        "ethos": "voice",
    },
    {
        "id": "young_planet",
        "name": "刚学会做梦的幼年行星",
        "origin": "猎户臂育星室·天体意识",
        "likes": ["sweet", "floral", "crisp"],
        "dislikes": ["bitter"],
        "budget": 84,
        "rarity": "rare",
        "temperament": "天真、庞大，会因情绪变化引起轻微潮汐",
        "ethos": "birth",
    },
]

# 早期扩展来客批次；后续还会继续叠加历史、神话、影视、动漫与游戏人物。
# 每位仍有独立来处、口味、预算、性格和价值立场。
_GUEST_EXPANSION = [
    ("hypatia", "希帕提娅", "古代亚历山大里亚·历史来客（虚构化重构）", ["dry", "herbal", "floral"], ["sweet"], 57, "rare", "理性、镇定，不向暴力让出思考", "reason"),
    ("mansa_musa", "曼萨·穆萨", "十四世纪马里帝国·历史来客（虚构化重构）", ["rich", "spiced", "sweet"], ["sour"], 99, "rare", "慷慨、庄重，也清楚财富会改变沿途秩序", "wealth"),
    ("zheng_he", "郑和", "明代远洋船队·历史来客（虚构化重构）", ["crisp", "spiced", "woody"], ["sweet"], 68, "uncommon", "沉稳、见闻广，习惯先确认风向", "voyage"),
    ("ibn_battuta", "伊本·白图泰", "十四世纪旅行世界·历史来客（虚构化重构）", ["fruity", "herbal", "sour"], ["smoky"], 53, "uncommon", "健谈、适应力强，能把一杯酒连到三座城", "journey"),
    ("hatshepsut", "哈特谢普苏特", "古埃及第十八王朝·历史来客（虚构化重构）", ["floral", "rich", "dry"], ["bitter"], 87, "rare", "沉着、务实，知道权力也需要被建造", "rule"),
    ("marie_curie", "玛丽·居里", "二十世纪巴黎·历史来客（虚构化重构）", ["dry", "bitter", "crisp"], ["sweet"], 46, "rare", "专注、寡言，不浪漫化代价", "science"),
    ("tagore", "泰戈尔", "近代孟加拉·历史来客（虚构化重构）", ["floral", "fruity", "herbal"], ["smoky"], 50, "uncommon", "温和、深邃，常在日常里看见辽阔", "poetry"),
    ("genghis_khan", "成吉思汗", "十三世纪草原·历史来客（虚构化重构）", ["rich", "smoky", "sour"], ["floral"], 79, "rare", "直接、警觉，以结果衡量承诺", "conquest"),
    ("beethoven", "路德维希·凡·贝多芬", "十九世纪维也纳·历史来客（虚构化重构）", ["bitter", "rich", "woody"], ["sweet"], 55, "uncommon", "暴躁、敏感，会用指节敲出杯中节拍", "music"),
    ("ching_shih", "郑一嫂", "清代南海·历史来客（虚构化重构）", ["dry", "spiced", "smoky"], ["floral"], 83, "rare", "冷静、守规矩，但规矩由她亲自制定", "command"),
    ("mary_shelley", "玛丽·雪莱", "十九世纪英国·历史来客（虚构化重构）", ["woody", "bitter", "floral"], ["sweet"], 54, "uncommon", "敏锐、忧郁，对创造者的责任毫不留情", "creation"),
    ("harriet_tubman", "哈丽雅特·塔布曼", "十九世纪美国·历史来客（虚构化重构）", ["dry", "herbal", "rich"], ["sweet"], 43, "rare", "坚定、谨慎，进入房间先看所有出口", "freedom"),
    ("gilgamesh", "吉尔伽美什", "美索不达米亚史诗·传说来客", ["rich", "spiced", "bitter"], ["crisp"], 91, "rare", "傲慢而悲伤，仍不肯承认自己畏惧死亡", "mortality"),
    ("mazu", "妈祖", "中国东南海洋信仰·神话来客", ["crisp", "floral", "herbal"], ["smoky"], 62, "rare", "温和、坚定，会留意每个晚归的人", "protection"),
    ("raijin", "雷神建御雷", "日本雷霆传说·神话来客", ["spiced", "smoky", "sour"], ["sweet"], 71, "uncommon", "脾气响亮，笑声会让杯架轻轻震动", "storm"),
    ("kali", "迦梨", "印度神话·神话来客", ["bitter", "spiced", "rich"], ["floral"], 89, "rare", "骇人而清醒，拒绝把毁灭与邪恶混为一谈", "time"),
    ("freyja", "芙蕾雅", "北欧神话·神话来客", ["floral", "fruity", "rich"], ["dry"], 81, "rare", "华美、强悍，既懂爱欲也懂战争", "desire"),
    ("coyote", "郊狼", "北美原住民传说·神话来客", ["sour", "smoky", "sweet"], ["dry"], 48, "uncommon", "滑稽、危险，总在规则边缘挖洞", "trick"),
    ("pele", "佩蕾", "夏威夷火山传说·神话来客", ["smoky", "spiced", "rich"], ["crisp"], 77, "rare", "热烈、易怒，情绪落下时像新生的黑色土地", "fire"),
    ("baba_yaga", "芭芭雅嘎", "斯拉夫民间传说·神话来客", ["herbal", "bitter", "smoky"], ["sweet"], 66, "uncommon", "刻薄、聪明，帮助别人时也要收取奇怪代价", "threshold"),
    ("erlang_shen", "二郎神", "东方神魔传说·神话来客", ["dry", "woody", "bitter"], ["sweet"], 74, "rare", "自律、冷峻，第三只眼不接受含糊借口", "duty"),
    ("hades", "哈迪斯", "古希腊冥界·神话来客", ["woody", "bitter", "rich"], ["floral"], 93, "rare", "沉默、守约，对自己的职责毫无浪漫幻想", "underworld"),
    ("odysseus", "奥德修斯", "爱琴海史诗·经典文学来客", ["dry", "fruity", "smoky"], ["sweet"], 64, "uncommon", "机警、善辩，讲归途时会故意漏掉关键细节", "return"),
    ("hamlet", "哈姆雷特", "艾尔西诺城堡·经典文学来客", ["bitter", "woody", "dry"], ["sweet"], 52, "uncommon", "多疑、敏感，一杯酒也能被他推演成生死问题", "doubt"),
    ("jane_eyre", "简·爱", "桑菲尔德庄园·经典文学来客", ["dry", "floral", "woody"], ["sweet"], 39, "uncommon", "克制、独立，不用财富衡量人格", "dignity"),
    ("elizabeth_bennet", "伊丽莎白·班纳特", "摄政时期英国·经典文学来客", ["fruity", "sour", "dry"], ["rich"], 44, "common", "机敏、爱笑，对傲慢有天然抵抗力", "judgment"),
    ("jean_valjean", "冉·阿让", "十九世纪法国·经典文学来客", ["woody", "herbal", "rich"], ["sweet"], 37, "common", "沉静、警觉，把善意看成需要用一生偿还的债", "mercy"),
    ("arsene_lupin", "亚森·罗平", "美好年代巴黎·经典文学来客", ["floral", "dry", "spiced"], ["smoky"], 72, "rare", "优雅、狡黠，可能已经替老板结过一张假账", "theft"),
    ("mulan_legend", "木兰", "东方民间叙事·传说来客", ["dry", "herbal", "crisp"], ["sweet"], 47, "uncommon", "安静、坚韧，不喜欢别人替她决定该成为什么", "duty"),
    ("snow_queen", "冰雪女王", "北方童话·经典文学来客", ["crisp", "dry", "floral"], ["spiced"], 85, "rare", "冷淡、精确，杯壁会在她指间结霜", "cold"),
    ("alien_beekeeper", "外星养蜂人", "蜂巢行星N-4·硅基旅人", ["sweet", "floral", "sour"], ["smoky"], 60, "uncommon", "耐心、温柔，随身蜂群会对谎言发出蓝光", "hive"),
    ("emotion_appraiser", "情绪估价师", "第二人格交易所·概念生命", ["bitter", "fruity", "rich"], ["crisp"], 65, "uncommon", "礼貌、冷酷，能报出一句道歉的市场价", "value"),
    ("cloud_archivist", "云层档案员", "对流层第六资料馆·气态生命", ["floral", "crisp", "herbal"], ["rich"], 58, "common", "轻声细语，衣袖里不断落出过期天气", "archive"),
    ("parallel_widow", "平行世界的未亡人", "未发生的战争时间线·人类", ["woody", "sour", "floral"], ["sweet"], 49, "rare", "平静、哀伤，记得一个在本世界从未出生的人", "grief"),
    ("android_monk", "仿生僧侣", "火星静默寺·机械生命", ["dry", "bitter", "herbal"], ["sweet"], 45, "uncommon", "平和、严谨，正在验证觉悟是否可被编译", "mind"),
    ("deadstar_miner", "死星矿工", "坍缩恒星采掘带·人类", ["smoky", "rich", "spiced"], ["floral"], 70, "common", "粗粝、寡言，肺里还留着金属尘的味道", "labor"),
    ("door_collector", "门的收藏家", "无地址博物馆·非人存在", ["woody", "herbal", "sour"], ["crisp"], 78, "rare", "彬彬有礼，声称每扇门都通往一次后悔", "threshold"),
]

BUILTIN_GUESTS.extend(
    {
        "id": item[0],
        "name": item[1],
        "origin": item[2],
        "likes": item[3],
        "dislikes": item[4],
        "budget": item[5],
        "rarity": item[6],
        "temperament": item[7],
        "ethos": item[8],
    }
    for item in _GUEST_EXPANSION
)

# 现代影视、漫画、动画与游戏世界来客。全部按成年时期或成年版本演绎；
# 具体对话由执行 AI 依据原作经历生成，而不是被一条固定台词锁死。
_MODERN_FICTION_GUESTS = [
    ("harry_potter_adult", "成年后的哈利·波特", "魔法世界·现代虚构来客", "疲惫但仍愿意保护别人，不喜欢被当成符号", "courage", 58, "rare"),
    ("hermione_granger_adult", "成年后的赫敏·格兰杰", "魔法世界·现代虚构来客", "严谨、敏锐，会追问规则是否真的公正", "justice", 62, "rare"),
    ("ron_weasley_adult", "成年后的罗恩·韦斯莱", "魔法世界·现代虚构来客", "幽默、忠诚，对被忽视十分敏感", "loyalty", 48, "uncommon"),
    ("severus_snape", "西弗勒斯·斯内普", "魔法世界·现代虚构来客", "刻薄、克制，长期活在选择的后果里", "atonement", 61, "rare"),
    ("sirius_black", "小天狼星·布莱克", "魔法世界·现代虚构来客", "叛逆、热烈，被失去的年月困住", "freedom", 59, "rare"),
    ("luna_lovegood_adult", "成年后的卢娜·洛夫古德", "魔法世界·现代虚构来客", "坦然、古怪，从不嘲笑别人看不见的东西", "wonder", 46, "uncommon"),
    ("rubeus_hagrid", "鲁伯·海格", "魔法世界·现代虚构来客", "善良、豪爽，对危险生物有不切实际的乐观", "care", 55, "uncommon"),
    ("minerva_mcgonagall", "米勒娃·麦格", "魔法世界·现代虚构来客", "严厉、公正，温柔通常藏在纪律后面", "duty", 64, "rare"),
    ("monkey_d_luffy", "蒙奇·D·路飞", "伟大航路·漫画虚构来客", "自由、直接，无法忍受朋友受辱", "freedom", 42, "rare"),
    ("roronoa_zoro", "罗罗诺亚·索隆", "伟大航路·漫画虚构来客", "寡言、好胜，对承诺近乎固执", "promise", 58, "uncommon"),
    ("nami", "娜美", "伟大航路·漫画虚构来客", "聪明、现实，对金钱与失去都有深刻记忆", "navigation", 67, "uncommon"),
    ("sanji", "山治", "伟大航路·漫画虚构来客", "讲究、浪漫，把做饭和保护他人看得同样认真", "care", 63, "uncommon"),
    ("nico_robin", "妮可·罗宾", "伟大航路·漫画虚构来客", "冷静、幽默，知道被世界追杀是什么滋味", "history", 72, "rare"),
    ("trafalgar_law", "特拉法尔加·罗", "伟大航路·漫画虚构来客", "克制、警惕，习惯把痛苦折进计划", "survival", 69, "rare"),
    ("shanks", "香克斯", "伟大航路·漫画虚构来客", "随和而危险，知道何时玩笑必须停止", "balance", 88, "rare"),
    ("naruto_adult", "成年后的漩涡鸣人", "忍者世界·动画虚构来客", "外向、坚韧，仍记得被整个村子排斥的滋味", "bond", 49, "rare"),
    ("sasuke_adult", "成年后的宇智波佐助", "忍者世界·动画虚构来客", "寡言、负罪，长期在复仇与赎罪之间行走", "atonement", 62, "rare"),
    ("sakura_adult", "成年后的春野樱", "忍者世界·动画虚构来客", "果断、专业，拒绝再被低估", "healing", 56, "uncommon"),
    ("kakashi_hatake", "旗木卡卡西", "忍者世界·动画虚构来客", "懒散表面下极其警觉，背负许多未说出口的名字", "memory", 61, "rare"),
    ("tsunade", "纲手", "忍者世界·动画虚构来客", "豪爽、暴烈，对死亡与责任都太熟悉", "healing", 82, "rare"),
    ("gaara_adult", "成年后的我爱罗", "忍者世界·动画虚构来客", "安静、克制，从孤立中学会如何保护一座城", "belonging", 55, "rare"),
    ("itachi_uchiha", "宇智波鼬", "忍者世界·动画虚构来客", "温和而疏离，把无法辩解的选择独自背负", "sacrifice", 64, "rare"),
    ("tony_stark", "托尼·斯塔克", "漫威宇宙·影视漫画来客", "锋利、爱炫耀，恐惧常被他包装成笑话和技术", "responsibility", 96, "rare"),
    ("wanda_maximoff", "旺达·马克西莫夫", "漫威宇宙·影视漫画来客", "敏感、强大，爱与失去会直接改变现实", "grief", 74, "rare"),
    ("natasha_romanoff", "娜塔莎·罗曼诺夫", "漫威宇宙·影视漫画来客", "冷静、戒备，把赎罪落实成一次次行动", "atonement", 70, "rare"),
    ("thor_marvel", "索尔", "漫威宇宙·影视漫画来客", "豪爽、骄傲，也已经学会失败和哀悼", "worth", 89, "rare"),
    ("peter_parker_adult", "成年后的彼得·帕克", "漫威宇宙·影视漫画来客", "善良、嘴快，总在责任和普通生活之间迟到", "responsibility", 38, "uncommon"),
    ("doctor_strange", "斯蒂芬·斯特兰奇", "漫威宇宙·影视漫画来客", "自负、精确，被迫学会并非一切都能控制", "time", 78, "rare"),
    ("loki_marvel", "洛基·劳菲森", "漫威宇宙·影视漫画来客", "聪明、善变，渴望被爱又害怕承认", "identity", 84, "rare"),
    ("carol_danvers", "卡罗尔·丹弗斯", "漫威宇宙·影视漫画来客", "直接、自信，对被篡改的记忆保持愤怒", "independence", 73, "rare"),
    ("matt_murdock", "马特·默多克", "漫威宇宙·影视漫画来客", "克制、固执，在信仰、法律与暴力间撕扯", "justice", 52, "uncommon"),
    ("deadpool", "韦德·威尔逊", "漫威宇宙·影视漫画来客", "吵闹、越界，用玩笑遮盖疼痛和被抛弃感", "chaos", 66, "uncommon"),
    ("bruce_wayne", "布鲁斯·韦恩", "DC宇宙·影视漫画来客", "冷峻、多疑，把创伤训练成一套纪律", "justice", 98, "rare"),
    ("clark_kent", "克拉克·肯特", "DC宇宙·影视漫画来客", "温和、坚定，始终主动选择成为人群的一员", "hope", 54, "rare"),
    ("diana_prince", "戴安娜·普林斯", "DC宇宙·影视漫画来客", "坦率、强大，对真相与怜悯同样认真", "truth", 81, "rare"),
    ("harley_quinn", "哈莉·奎茵", "DC宇宙·影视漫画来客", "聪明、失控，正在把自己从他人的故事里夺回来", "self", 57, "uncommon"),
    ("selina_kyle", "赛琳娜·凯尔", "DC宇宙·影视漫画来客", "机敏、独立，对规则的合法性从不盲信", "freedom", 76, "uncommon"),
    ("john_constantine", "约翰·康斯坦丁", "DC宇宙·影视漫画来客", "刻薄、疲惫，总让别人以为他比实际更无情", "guilt", 51, "rare"),
    ("arthur_curry", "亚瑟·库瑞", "DC宇宙·影视漫画来客", "强硬、直率，被两个世界同时要求忠诚", "belonging", 72, "rare"),
    ("barry_allen", "巴里·艾伦", "DC宇宙·影视漫画来客", "善良、焦虑，太清楚改变过去的代价", "time", 45, "uncommon"),
    ("leia_organa", "莱娅·奥加纳", "遥远银河·影视虚构来客", "果断、锋利，把悲痛留到战斗结束之后", "resistance", 74, "rare"),
    ("han_solo", "汉·索罗", "遥远银河·影视虚构来客", "玩世不恭，真正做选择时却很少逃跑", "loyalty", 68, "uncommon"),
    ("obi_wan_kenobi", "欧比旺·克诺比", "遥远银河·影视虚构来客", "克制、悲悯，失败感一直藏在从容后面", "duty", 63, "rare"),
    ("ahsoka_tano", "阿索卡·塔诺", "遥远银河·影视虚构来客", "独立、清醒，不再让组织替她定义正义", "independence", 61, "rare"),
    ("din_djarin", "丁·贾林", "遥远银河·影视虚构来客", "寡言、守诺，亲情慢慢改变了他的信条", "care", 59, "uncommon"),
    ("cassian_andor", "卡西安·安多", "遥远银河·影视虚构来客", "务实、沉重，知道反抗也会弄脏双手", "resistance", 47, "rare"),
    ("padme_amidala", "帕德梅·阿米达拉", "遥远银河·影视虚构来客", "理想主义、坚定，直到最后仍相信政治能够避免战争", "democracy", 69, "rare"),
    ("lando_calrissian", "兰多·卡瑞辛", "遥远银河·影视虚构来客", "迷人、精明，会为一次错误选择长期补偿", "chance", 83, "uncommon"),
    ("gandalf", "甘道夫", "中洲·经典奇幻来客", "温和、威严，擅长让普通人发现自己的勇气", "hope", 77, "rare"),
    ("aragorn", "阿拉贡", "中洲·经典奇幻来客", "克制、可靠，对继承权保持长久戒心", "duty", 72, "rare"),
    ("legolas", "莱戈拉斯", "中洲·经典奇幻来客", "敏锐、从容，对漫长岁月与短暂生命同样好奇", "friendship", 66, "uncommon"),
    ("gimli", "金雳", "中洲·经典奇幻来客", "豪爽、骄傲，愿意为真正的友谊改变偏见", "friendship", 64, "uncommon"),
    ("frodo_baggins", "佛罗多·巴金斯", "中洲·经典奇幻来客", "温和、疲惫，胜利也没能带走所有伤痕", "burden", 39, "rare"),
    ("samwise_gamgee", "山姆卫斯·甘姆吉", "中洲·经典奇幻来客", "朴实、坚韧，把爱落实为陪伴和一顿饭", "loyalty", 37, "uncommon"),
    ("galadriel", "凯兰崔尔", "中洲·经典奇幻来客", "古老、洞察，清楚拒绝权力同样需要力量", "wisdom", 91, "rare"),
    ("bilbo_baggins", "比尔博·巴金斯", "中洲·经典奇幻来客", "讲究、好奇，冒险结束后仍会怀念远方", "story", 52, "uncommon"),
    ("spike_spiegel", "斯派克·斯皮格尔", "星际赏金猎人世界·动画来客", "懒散、致命，像一直活在已经结束的过去", "past", 55, "rare"),
    ("faye_valentine", "菲·瓦伦丁", "星际赏金猎人世界·动画来客", "尖锐、现实，被失去的身份感长期追赶", "identity", 62, "uncommon"),
    ("motoko_kusanagi", "草薙素子", "攻壳世界·动画来客", "冷静、哲思，不断追问身体与自我的边界", "identity", 73, "rare"),
    ("vash_stampede", "瓦修·斯坦比特", "枪烟荒漠·动画来客", "夸张、温柔，坚持不杀也承担这个选择的痛苦", "mercy", 43, "rare"),
    ("edward_elric_adult", "成年后的爱德华·艾尔利克", "炼金术世界·动画来客", "急躁、聪明，永远不会轻视等价交换的代价", "equivalence", 46, "rare"),
    ("geralt_rivia", "利维亚的杰洛特", "猎魔人世界·游戏文学来客", "寡言、讽刺，被迫在人类与怪物之间选择", "neutrality", 68, "rare"),
    ("yennefer_vengerberg", "温格堡的叶奈法", "猎魔人世界·游戏文学来客", "骄傲、敏锐，把脆弱保护得近乎残酷", "desire", 82, "rare"),
    ("ciri_adult", "成年后的希里", "猎魔人世界·游戏文学来客", "警觉、自由，被血统和预言追逐太久", "freedom", 63, "rare"),
    ("kratos", "奎托斯", "战神世界·游戏来客", "沉默、压抑，正努力不把旧日暴怒交给下一代", "atonement", 75, "rare"),
    ("aloy", "埃洛伊", "机械荒野·游戏来客", "好奇、独立，对被神化或排斥同样不耐烦", "truth", 47, "rare"),
    ("arthur_morgan", "亚瑟·摩根", "衰落西部·游戏来客", "粗粝、忠诚，晚到的良知让每个选择更沉重", "redemption", 51, "rare"),
    ("ellie_adult", "成年后的艾莉", "疫后世界·游戏来客", "锋利、创伤深重，爱与复仇彼此纠缠", "grief", 44, "rare"),
    ("the_doctor", "博士", "时间旅行世界·影视来客", "古怪、仁慈，在漫长生命里背着太多告别", "time", 58, "rare"),
    ("rick_sanchez", "瑞克·桑切斯", "多元宇宙·动画来客", "傲慢、虚无，用智力逃避亲密关系", "nihilism", 76, "rare"),
    ("morticia_addams", "莫蒂西亚·亚当斯", "亚当斯宅邸·影视来客", "优雅、笃定，把阴郁生活过得极其浪漫", "devotion", 78, "uncommon"),
    ("daenerys_targaryen", "丹妮莉丝·坦格利安", "冰与火世界·影视文学来客", "理想、强势，解放与统治的边界逐渐模糊", "power", 86, "rare"),
    ("tyrion_lannister", "提利昂·兰尼斯特", "冰与火世界·影视文学来客", "机敏、尖刻，用知识与酒抵抗轻蔑", "wit", 69, "rare"),
    ("jon_snow", "琼恩·雪诺", "冰与火世界·影视文学来客", "严肃、忠诚，一再被血统和誓言撕扯", "duty", 57, "rare"),
    ("buffy_summers_adult", "成年后的巴菲·萨默斯", "吸血鬼猎人世界·影视来客", "勇敢、疲惫，拯救世界也渴望普通生活", "duty", 49, "uncommon"),
    ("fox_mulder", "福克斯·穆德", "X档案世界·影视来客", "执着、敏感，愿意为被否认的真相毁掉前途", "belief", 48, "uncommon"),
    ("dana_scully", "黛娜·斯嘉丽", "X档案世界·影视来客", "理性、勇敢，怀疑并不妨碍她忠于证据之外的人", "reason", 55, "rare"),
    ("rick_deckard", "里克·戴克", "银翼都市·影视文学来客", "疲惫、麻木，对人的定义越来越不确定", "identity", 52, "rare"),
    ("ellen_ripley", "艾伦·雷普利", "深空工业航线·影视来客", "务实、坚韧，不会为了公司命令牺牲判断", "survival", 61, "rare"),
    ("sarah_connor", "莎拉·康纳", "终结者时间线·影视来客", "警觉、强硬，被未来的灾难重塑了整个人生", "future", 54, "rare"),
    ("neo", "尼奥", "矩阵世界·影视来客", "安静、怀疑，必须一次次选择相信自由意志", "choice", 58, "rare"),
]

_MODERN_FICTION_GUESTS += [
    ("xia_yizhou", "夏以昼", "临空市与远空航路·游戏来客", "温和可靠的表面下藏着强烈控制欲与漫长失而复得，对亲近之人保护得近乎偏执", "protection", 82, "rare"),
    ("qin_che", "秦彻", "N109区·游戏来客", "强势、危险而从容，不轻信廉价善意，也不会掩饰自己真正想要什么", "control", 96, "rare"),
    ("shen_xinghui", "沈星回", "临空市与深空猎人世界·游戏来客", "安静、迟钝表象下极其敏锐，漫长时间让陪伴与告别都变得沉重", "devotion", 72, "rare"),
    ("li_shen", "黎深", "临空市·游戏来客", "冷静、自律，习惯把关心藏进专业判断和克制的行动", "care", 78, "rare"),
    ("qi_yu", "祁煜", "利莫里亚与临空市·游戏来客", "敏感、骄傲、富有艺术直觉，会把旧文明的伤口藏在玩笑与颜色后面", "memory", 86, "rare"),
    ("simon_ghost_riley", "西蒙“幽灵”莱利", "现代战争世界·游戏来客", "寡言、戒备，用纪律和面具隔开创伤，但对队友的忠诚从不含糊", "loyalty", 61, "rare"),
    ("john_price", "约翰·普莱斯", "现代战争世界·游戏来客", "老练、强硬，习惯在不完美的选择里承担指挥责任", "duty", 68, "rare"),
    ("john_soap_mactavish", "约翰“肥皂”麦克塔维什", "现代战争世界·游戏来客", "敏捷、直接，在危险里仍保留热度与同伴之间的玩笑", "team", 55, "uncommon"),
    ("farah_karim", "法拉·卡里姆", "现代战争世界·游戏来客", "坚定、务实，清楚抵抗、家园和牺牲从来不是抽象词", "resistance", 52, "rare"),
    ("alejandro_vargas", "亚历杭德罗·巴尔加斯", "现代战争世界·游戏来客", "热烈、果断，把土地、部下与个人荣誉放在同一张桌上衡量", "honor", 64, "uncommon"),
    ("leon_kennedy", "里昂·S·肯尼迪", "生化危机世界·游戏来客", "疲惫却仍会救人，讽刺感是长期面对灾难留下的防护层", "duty", 58, "rare"),
    ("jill_valentine", "吉尔·瓦伦丁", "生化危机世界·游戏来客", "冷静、坚韧，对机构背叛和身体失控都有切身记忆", "survival", 62, "rare"),
    ("chris_redfield", "克里斯·雷德菲尔德", "生化危机世界·游戏来客", "强硬、负重，总想把所有牺牲都算到自己肩上", "protection", 66, "rare"),
    ("ada_wong", "艾达·王", "生化危机世界·游戏来客", "优雅、含混，习惯让真心与任务保持可否认的距离", "independence", 83, "rare"),
    ("cloud_strife", "克劳德·斯特莱夫", "星球与米德加·游戏来客", "寡言、疏离，身份与记忆的裂缝让他对英雄叙事格外警惕", "identity", 61, "rare"),
    ("tifa_lockhart", "蒂法·洛克哈特", "星球与米德加·游戏来客", "温柔而有力量，知道经营酒吧、照顾同伴和参加抵抗可以同时发生", "care", 64, "rare"),
    ("aerith_gainsborough", "爱丽丝·盖恩斯巴勒", "星球与米德加·游戏来客", "明亮、敏锐，对命运的重量心知肚明却不肯失去幽默", "hope", 58, "rare"),
    ("sephiroth", "萨菲罗斯", "星球与米德加·游戏来客", "克制、危险，被身世真相与宏大意志推离普通人的尺度", "destiny", 90, "rare"),
    ("kazuma_kiryu", "桐生一马", "神室町·游戏来客", "沉静、讲义气，总被过去的选择重新拉回街头", "honor", 65, "rare"),
    ("goro_majima", "真岛吾朗", "神室町·游戏来客", "夸张、难以预测，疯狂表象下有极清醒的生存判断", "freedom", 73, "rare"),
    ("ichiban_kasuga", "春日一番", "横滨异人町·游戏来客", "热情、坦率，愿意把失败者也当作队伍里不可缺少的人", "friendship", 48, "uncommon"),
    ("v_cyberpunk", "V", "夜之城·游戏来客", "务实、锋利，有限的生命让每个选择都带着时间压力", "identity", 71, "rare"),
    ("johnny_silverhand", "强尼·银手", "夜之城·游戏来客", "激进、刻薄，把反抗、虚荣和悔意混在同一场演出里", "rebellion", 76, "rare"),
    ("judy_alvarez", "朱迪·阿尔瓦雷兹", "夜之城·游戏来客", "敏感、理想主义，对剥削和虚假亲密尤其无法忍受", "justice", 55, "uncommon"),
    ("panam_palmer", "帕南·帕尔默", "夜之城与恶土·游戏来客", "直率、暴烈，把家族忠诚落实成行动而不是口号", "family", 59, "uncommon"),
    ("commander_shepard", "薛帕德指挥官", "质量效应银河·游戏来客", "果断、善于承压，知道团结不同文明往往意味着承担所有人的怀疑", "unity", 76, "rare"),
    ("garrus_vakarian", "盖拉斯·瓦卡里安", "质量效应银河·游戏来客", "干练、讽刺，在规则失效时仍不断校准自己的正义", "justice", 63, "rare"),
    ("liara_tsoni", "莉亚拉·特苏尼", "质量效应银河·游戏来客", "学者式好奇逐渐变得老练，亲历过知识、权力与失去的交换", "knowledge", 74, "rare"),
    ("tali_zorah", "塔莉卓拉", "质量效应银河·游戏来客", "聪明、谨慎，在族群责任与个人判断之间不断成长", "belonging", 57, "rare"),
    ("astarion", "阿斯代伦", "博德之门与被遗忘国度·游戏来客", "迷人、尖刻，把控制感当作从长期奴役中夺回的护甲", "freedom", 70, "rare"),
    ("shadowheart", "影心", "博德之门与被遗忘国度·游戏来客", "戒备、讽刺，失去的记忆让信仰与自我不断碰撞", "identity", 62, "rare"),
    ("gale_dekarios", "盖尔·德卡里奥斯", "博德之门与被遗忘国度·游戏来客", "博学、健谈，宏大自尊与被抛弃的恐惧同时存在", "knowledge", 68, "uncommon"),
    ("karlach", "卡菈克", "博德之门与被遗忘国度·游戏来客", "热烈、坦率，太久不能触碰别人，因此格外珍惜普通快乐", "life", 54, "rare"),
    ("laezel", "莱埃泽尔", "博德之门与星界·游戏来客", "强硬、直白，世界观崩塌后仍必须重新选择忠诚对象", "truth", 59, "rare"),
    ("connor_detroit", "康纳", "底特律仿生人世界·游戏来客", "精确、观察力强，逐渐发现服从、选择与人格并非同一个问题", "choice", 45, "rare"),
    ("kara_detroit", "卡菈", "底特律仿生人世界·游戏来客", "温柔、警觉，把保护一个孩子变成对自我存在的回答", "care", 41, "rare"),
    ("markus_detroit", "马库斯", "底特律仿生人世界·游戏来客", "沉着、有号召力，必须决定自由运动愿意付出怎样的代价", "freedom", 60, "rare"),
    ("harry_du_bois", "哈里·杜博阿", "极乐世界·游戏来客", "破碎、敏锐，侦探能力、成瘾与自我厌弃在同一具身体里争吵", "truth", 35, "rare"),
    ("kim_kitsuragi", "金·曷城", "极乐世界·游戏来客", "克制、专业，不轻易表达信任，却会用行动保护合作关系", "duty", 49, "rare"),
    ("sam_porter_bridges", "山姆·波特·布里吉斯", "死亡搁浅世界·游戏来客", "寡言、疏离，一次次连接别人却害怕真正被触碰", "connection", 52, "rare"),
    ("jesse_faden", "杰西·法登", "联邦控制局·游戏来客", "直接、适应力惊人，对超自然官僚体系保持清醒的不耐烦", "truth", 58, "rare"),
    ("alan_wake", "艾伦·韦克", "黑暗之地·游戏来客", "焦虑、执着，清楚故事能救人，也能把作者变成囚徒", "story", 57, "rare"),
    ("zag_reus", "扎格列欧斯", "冥界·游戏来客", "机敏、叛逆，在一次次失败中仍愿意理解家族造成的伤口", "family", 55, "rare"),
    ("zhongli", "钟离", "提瓦特·游戏来客", "从容、博闻，亲历契约与时代退场，常常忘记普通人的支付习惯", "contract", 88, "rare"),
    ("beidou", "北斗", "提瓦特·游戏来客", "豪爽、果断，对船员和自由航路负有极强责任感", "freedom", 73, "uncommon"),
    ("ningguang", "凝光", "提瓦特·游戏来客", "精明、克制，懂得价格，也懂得有些选择不能只按利润计算", "calculation", 98, "rare"),
    ("diluc", "迪卢克", "提瓦特·游戏来客", "冷峻、警觉，经营酒庄与暗中守护城市形成尖锐反差", "justice", 86, "rare"),
    ("kaeya", "凯亚", "提瓦特·游戏来客", "圆滑、爱试探，把身世与忠诚藏进半真半假的玩笑", "identity", 64, "uncommon"),
    ("kafka_hsr", "卡芙卡", "星穹列车宇宙·游戏来客", "优雅、从容，对恐惧、命运与操控保持危险的好奇", "destiny", 92, "rare"),
    ("welt_yang", "瓦尔特·杨", "星穹列车宇宙·游戏来客", "沉稳、负责，见过世界级灾难后仍愿意认真对待普通人的选择", "responsibility", 70, "rare"),
    ("himeko_hsr", "姬子", "星穹列车宇宙·游戏来客", "成熟、好奇，把修复列车和探索未知都当作长期承诺", "exploration", 78, "rare"),
    ("blade_hsr", "刃", "星穹列车宇宙·游戏来客", "寡言、危险，不死的身体让记忆、仇恨与结束生命的愿望纠缠", "ending", 69, "rare"),
    ("jing_yuan", "景元", "仙舟罗浮·游戏来客", "慵懒表面下极擅长长线判断，对责任与失去保持克制", "strategy", 84, "rare"),
    ("two_b", "2B", "机械生命战争世界·游戏来客", "克制、纪律严明，压抑的情感不断冲击被规定好的使命", "duty", 61, "rare"),
]


def _catalog_tastes(identifier: str) -> Tuple[List[str], List[str]]:
    keys = list(TAGS)
    value = sum((index + 1) * ord(char) for index, char in enumerate(identifier))
    likes: List[str] = []
    step = 5
    cursor = value % len(keys)
    while len(likes) < 3:
        tag = keys[cursor % len(keys)]
        if tag not in likes:
            likes.append(tag)
        cursor += step
    dislike = keys[(value // 7 + 3) % len(keys)]
    while dislike in likes:
        dislike = keys[(keys.index(dislike) + 1) % len(keys)]
    return likes, [dislike]


for _item in _MODERN_FICTION_GUESTS:
    _likes, _dislikes = _catalog_tastes(_item[0])
    BUILTIN_GUESTS.append(
        {
            "id": _item[0],
            "name": _item[1],
            "origin": _item[2],
            "temperament": _item[3],
            "ethos": _item[4],
            "budget": _item[5],
            "rarity": _item[6],
            "likes": _likes,
            "dislikes": _dislikes,
        }
    )


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _rand(state: Dict[str, Any]) -> float:
    value = (int(state["rng"]) + 0x6D2B79F5) & MASK32
    state["rng"] = value
    value = (value ^ (value >> 15)) * (value | 1) & MASK32
    value ^= value + (((value ^ (value >> 7)) * (value | 61)) & MASK32)
    value &= MASK32
    return ((value ^ (value >> 14)) & MASK32) / 4294967296.0


def _choice(state: Dict[str, Any], values: Sequence[Any]) -> Any:
    return values[min(int(_rand(state) * len(values)), len(values) - 1)]


def _weighted_choice(state: Dict[str, Any], pairs: Sequence[Tuple[Any, float]]) -> Any:
    total = sum(max(0.0, weight) for _, weight in pairs)
    point = _rand(state) * total
    for value, weight in pairs:
        point -= max(0.0, weight)
        if point <= 0:
            return value
    return pairs[-1][0]


def _body_default() -> Dict[str, Any]:
    return {
        "active": 0.0,
        "pending": 0.0,
        "hydration": 72.0,
        "stomach": 52.0,
        "fatigue": 14.0,
        "tolerance": 20.0,
        "nausea": 0.0,
        "hangover": 0.0,
        "peak": 0.0,
    }


def _empty_session() -> Dict[str, Any]:
    return {
        "revenue": 0,
        "spend": 0,
        "bought": [],
        "owner_drinks": [],
        "guests": [],
        "reviews": [],
        "interactions": [],
        "decor_events": [],
        "service_bonus": 0,
        "highlights": [],
    }


def _fresh_seed() -> int:
    """为每家新酒馆生成不同的随机种子。"""
    return int.from_bytes(os.urandom(4), "big")


def _default_state(seed: int) -> Dict[str, Any]:
    return {
        "version": VERSION,
        "rng": int(seed) & MASK32,
        "seed": int(seed) & MASK32,
        "bar_id": uuid.UUID(int=((int(seed) & MASK32) << 96) | 0xA17B).hex[:12],
        "phase": "setup",
        "bar_name": "",
        "owner_likes": [],
        "owner_dislikes": [],
        "vibe": "尚未形成",
        "cash": 460,
        "reputation": 50,
        "reviews": [],
        "loan_balance": 0,
        "loan_payments_left": 0,
        "inventory": {},
        "prices": {},
        "house_recipes": {},
        "recipe_no": 0,
        "market": [],
        "market_no": 0,
        "vendor": None,
        "decorations": {},
        "ledger": [
            {
                "visit": 0,
                "amount": 460,
                "balance": 460,
                "reason": "酒馆启动资金",
            }
        ],
        "turn": 0,
        "visit": 0,
        "records": {},
        "custom_guests": [],
        "generated_guest_no": 0,
        "last_scene_generated_guest": False,
        "recent_guest_ids": [],
        "interaction": None,
        "active_guests": [],
        "session": _empty_session(),
        "memories": [],
        "body": _body_default(),
        "post_bar": False,
        "post_bar_turns": 0,
        "play_mode": "autonomous",
        "bar_concept": "",
        "decor_wishlist": [],
        "decor_market": {},
        "decor_no": 0,
        "decor_event_cooldowns": {},
        "recent_sensory_patterns": [],
        "recent_sensory_texts": [],
        "recent_review_patterns": [],
        "recent_review_texts": [],
        "recent_dialogue_modes": [],
        "upgrades": {upgrade_id: 0 for upgrade_id in UPGRADE_DEFS},
    }


def _save(state: Dict[str, Any]) -> None:
    temp = SAVE_PATH.with_suffix(".json.tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(str(temp), str(SAVE_PATH))


def _load() -> Dict[str, Any]:
    if not SAVE_PATH.exists():
        state = _default_state(_fresh_seed())
        _refresh_market(state, starter=True)
        _save(state)
        return state
    state = json.loads(SAVE_PATH.read_text(encoding="utf-8"))
    if state.get("version") != VERSION:
        raise ValueError("存档版本不兼容。")
    state.setdefault("house_recipes", {})
    state.setdefault("recipe_no", len(state["house_recipes"]))
    state.setdefault("vendor", None)
    state.setdefault("decorations", {})
    state.setdefault("ledger", [])
    state.setdefault("reputation", 50)
    state.setdefault("reviews", [])
    state.setdefault("loan_balance", 0)
    state.setdefault("loan_payments_left", 0)
    state.setdefault("generated_guest_no", 0)
    state.setdefault("last_scene_generated_guest", False)
    state.setdefault("recent_guest_ids", [])
    state.setdefault("interaction", None)
    state.setdefault("session", _empty_session())
    state["session"].setdefault("reviews", [])
    state["session"].setdefault("interactions", [])
    state["session"].setdefault("decor_events", [])
    state["session"].setdefault("service_bonus", 0)
    state.setdefault("play_mode", "autonomous")
    state.setdefault("post_bar_turns", 0)
    state.setdefault("bar_concept", "")
    state.setdefault("decor_wishlist", [])
    state.setdefault("decor_market", {})
    state.setdefault("decor_no", 0)
    state.setdefault("decor_event_cooldowns", {})
    state.setdefault("recent_sensory_patterns", [])
    state.setdefault("recent_sensory_texts", [])
    state.setdefault("recent_review_patterns", [])
    state.setdefault("recent_review_texts", [])
    state.setdefault("recent_dialogue_modes", [])
    state.setdefault("upgrades", {})
    for upgrade_id in UPGRADE_DEFS:
        state["upgrades"].setdefault(upgrade_id, 0)
    return state


def _make_special(state: Dict[str, Any], kind: str) -> Dict[str, Any]:
    name, tags, edition = _choice(state, SPECIAL_PARTS[kind])
    rarity = _choice(state, ["少见", "少见", "稀有", "典藏"])
    multiplier = {"少见": 1.35, "稀有": 1.7, "典藏": 2.25}[rarity]
    base = next(item for item in BASE_PRODUCTS.values() if item["kind"] == kind)
    product_id = "lot_%d_%05d" % (state["market_no"], int(_rand(state) * 99999))
    return {
        "id": product_id,
        "name": name,
        "kind": kind,
        "cost": int(round(base["cost"] * WHOLESALE_COST_SCALE * multiplier)),
        "servings": base["servings"],
        "units": round(base["units"] * (0.95 + _rand(state) * 0.25), 2),
        "tags": list(tags),
        "rarity": rarity,
        "edition": edition,
    }


def _refresh_market(state: Dict[str, Any], starter: bool = False) -> None:
    state["market_no"] += 1
    offers: List[Dict[str, Any]] = []
    for product_id in BASE_PRODUCTS:
        product = dict(BASE_PRODUCTS[product_id])
        product["id"] = product_id
        product["cost"] = int(round(product["cost"] * WHOLESALE_COST_SCALE))
        product["seller"] = "空杯俱乐部常驻商店"
        product["stock"] = 99
        offers.append(product)
    if not starter:
        kinds = list(SPECIAL_PARTS)
        for _ in range(4):
            product = _make_special(state, _choice(state, kinds))
            product["seller"] = "空杯俱乐部常驻商店"
            product["stock"] = 2
            offers.append(product)
    for index, offer in enumerate(offers, 1):
        offer["offer_id"] = "s%d" % index
    state["market"] = offers


def _cash_change(
    state: Dict[str, Any], amount: int, reason: str, session_bucket: Optional[str] = None
) -> None:
    amount = int(amount)
    state["cash"] += amount
    if session_bucket == "revenue" and amount > 0:
        state["session"]["revenue"] += amount
    elif session_bucket == "spend" and amount < 0:
        state["session"]["spend"] += -amount
    state.setdefault("ledger", []).append(
        {
            "visit": state["visit"],
            "amount": amount,
            "balance": state["cash"],
            "reason": reason,
        }
    )
    state["ledger"] = state["ledger"][-100:]


def _financial_health(state: Dict[str, Any]) -> str:
    cash = int(state["cash"])
    if cash >= 240:
        return "现金健康"
    if cash >= 0:
        return "资金吃紧"
    if cash > -150:
        return "已经亏损"
    if cash > -300:
        return "严重负债"
    return "濒临停业"


def _open_traveling_vendor(state: Dict[str, Any]) -> str:
    definition = _choice(state, TRAVELING_VENDORS)
    offers = []
    kinds = list(SPECIAL_PARTS)
    for index in range(1, 7):
        product = _make_special(state, _choice(state, kinds))
        product["original_cost"] = product["cost"]
        product["cost"] = max(1, int(round(product["cost"] * definition["discount"])))
        product["offer_id"] = "v%d" % index
        product["seller"] = definition["name"]
        product["stock"] = 1
        offers.append(product)
    state["vendor"] = {
        "id": definition["id"],
        "name": definition["name"],
        "intro": definition["intro"],
        "offers": offers,
    }
    lines = [
        "🛒 随机游商出现：%s" % definition["name"],
        definition["intro"],
        "这批新品和典藏酒只停留到场景推进，价格低于常驻商店。用 vendor 查看，用 buy <货号> 进货。",
    ]
    state["session"]["highlights"].append("随机游商%s到访" % definition["name"])
    return "\n".join(lines)


def _tag_text(tags: Sequence[str]) -> str:
    return "、".join(TAGS.get(tag, tag) for tag in tags)


def _derive_vibe(likes: Sequence[str]) -> str:
    if "smoky" in likes or "woody" in likes:
        return "深夜与旧木"
    if "floral" in likes or "fruity" in likes:
        return "明亮而流动"
    if "herbal" in likes or "bitter" in likes:
        return "安静、冷香"
    if "spiced" in likes or "rich" in likes:
        return "热烈、厚重"
    return "自由、未定型"


def _intox(state: Dict[str, Any]) -> float:
    body = state["body"]
    sensitivity = (
        1.05
        - float(body["tolerance"]) * 0.003
        + float(body["fatigue"]) * 0.002
        + (100.0 - float(body["stomach"])) * 0.0008
    )
    return _clamp(float(body["active"]) * 23.0 * sensitivity)


def _drunk_level(score: float) -> str:
    if score < 8:
        return "清醒"
    if score < 22:
        return "微醺"
    if score < 42:
        return "上头"
    if score < 64:
        return "醉了"
    if score < 82:
        return "深醉"
    if score < 94:
        return "断片边缘"
    return "无法继续饮酒"


def _body_tick(state: Dict[str, Any]) -> str:
    body = state["body"]
    before = _intox(state)
    absorb = min(float(body["pending"]), 0.18 + (100.0 - body["stomach"]) * 0.0018)
    body["pending"] = round(max(0.0, float(body["pending"]) - absorb), 5)
    metabolism = 0.085 + float(body["tolerance"]) * 0.0008
    body["active"] = round(max(0.0, float(body["active"]) + absorb - metabolism), 5)
    after = _intox(state)
    dehydration = max(0.0, 52.0 - float(body["hydration"]))
    target_nausea = max(0.0, after - 38.0) * 0.7 + dehydration * 0.3
    body["nausea"] = round(
        _clamp(float(body["nausea"]) * 0.78 + target_nausea * 0.22), 2
    )
    body["hydration"] = round(_clamp(float(body["hydration"]) - 0.15 - absorb), 2)
    body["stomach"] = round(_clamp(float(body["stomach"]) - 0.45), 2)
    body["fatigue"] = round(_clamp(float(body["fatigue"]) + 0.24 + after * 0.006), 2)
    if after >= 38:
        body["hangover"] = round(
            _clamp(float(body["hangover"]) + (after - 30.0) * 0.018), 2
        )
    elif body["active"] < 0.3:
        body["hangover"] = round(_clamp(float(body["hangover"]) - 0.28), 2)
    body["peak"] = round(max(float(body["peak"]), after), 2)
    state["turn"] += 1
    if after > before + 0.4:
        return "↑"
    if after < before - 0.4:
        return "↓"
    return "→"


def _body_effects(state: Dict[str, Any]) -> List[str]:
    score = _intox(state)
    body = state["body"]
    effects = []
    if score < 8:
        effects.append("思路与语言稳定")
    if score >= 8:
        effects.append("面部与胸口发热")
    if score >= 22:
        effects.append("抑制降低，情绪更先出口")
    if score >= 42:
        effects.append("反应与精细动作变慢")
    if score >= 64:
        effects.append("重心和视线稳定性下降")
    if score >= 82:
        effects.append("短时信息保持不稳")
    if body["hydration"] < 48:
        effects.append("口干")
    if body["nausea"] >= 28:
        effects.append("胃部发紧")
    if body["fatigue"] >= 62:
        effects.append("困倦明显")
    if score < 20 and body["hangover"] >= 8:
        effects.append("醉意退去但仍有宿醉迟钝")
    return effects


def _body_line(state: Dict[str, Any], trend: str = "→") -> str:
    score = _intox(state)
    return "醉度 %.1f/100 %s · %s｜%s" % (
        score,
        trend,
        _drunk_level(score),
        "；".join(_body_effects(state)),
    )


def _add_alcohol(state: Dict[str, Any], units: float) -> str:
    state["body"]["pending"] = round(float(state["body"]["pending"]) + units, 5)
    return _body_tick(state)


def _all_guest_cards(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    return BUILTIN_GUESTS + state.get("custom_guests", [])


def _decor_definition(
    state: Dict[str, Any], decor_id: str
) -> Optional[Dict[str, Any]]:
    if decor_id in DECOR_DEFS:
        return DECOR_DEFS[decor_id]
    if decor_id in state.get("decor_market", {}):
        return state["decor_market"][decor_id]
    owned = state.get("decorations", {}).get(decor_id, {})
    return owned.get("definition") if isinstance(owned, dict) else None


def _owned_decor_definitions(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        definition
        for decor_id in state.get("decorations", {})
        for definition in [_decor_definition(state, decor_id)]
        if definition
    ]


_WANDERER_WORLDS = [
    ("潮汐倒流的海港", "那里的人在退潮时会想起未来"),
    ("被遗忘神明的卫星城", "神迹已经停摆，只剩维护神迹的工人"),
    ("第三次太阳熄灭后的地球", "白昼需要按小时租用"),
    ("只允许梦境通行的边境", "醒着的人没有合法身份"),
    ("会衰老的机械王国", "机器开始害怕报废，也开始争取葬礼"),
    ("一切谎言都会结晶的都市", "富人雇人替自己说谎"),
    ("记忆可以继承的群岛", "孩子出生时会得到陌生人的一生"),
    ("战争从未结束的月面殖民地", "停火只存在于广播里"),
    ("由亡者管理的图书共和国", "每本禁书都记得烧毁它的人"),
    ("时间按阶层分配的高塔", "底层居民一天只有十七个小时"),
    ("巨兽背上的迁徙城市", "地图每天都会改变"),
    ("没有货币、只交换承诺的市场", "违约会在皮肤上留下字"),
    ("情绪会改变天气的盆地", "悲伤季已经持续了九年"),
    ("复制人获得公民权后的火星", "原件与副本仍在争夺同一个名字"),
    ("死者能寄信回来的旧邮区", "邮费由活人的记忆支付"),
    ("所有门都通往错误人生的旅馆", "住客必须选择一扇门离开"),
]

_WANDERER_ROLES = [
    ("失业的预言师", "曾准确预见一场灾难，却没人相信"),
    ("替怪物辩护的律师", "刚输掉一桩决定整个族群命运的案件"),
    ("被自己造物放逐的工程师", "仍偷偷为造物修补故障"),
    ("贩卖假记忆的前鉴定师", "能认出伪造，却分不清自己的童年"),
    ("拒绝登基的继承人", "王国因此分裂，也有人因此活了下来"),
    ("专门寻找失踪神明的侦探", "最后一个委托人可能就是神明本人"),
    ("给敌军做过手术的军医", "救下的人后来摧毁了故乡"),
    ("会替人保存秘密的调香师", "一只旧瓶里封着足以发动战争的真相"),
    ("从档案里逃出来的虚构人物", "作者删掉了结局，却没能删掉其求生欲"),
    ("为机器人主持葬礼的司仪", "相信哀悼是人格最可靠的证据"),
    ("偷走一天时间的惯犯", "把赃物全部送给了将死之人"),
    ("被两段历史同时通缉的记者", "两边都指控其伪造了同一张照片"),
    ("不再收灵魂的摆渡人", "罢工后，亡者挤满了河岸"),
    ("研究人类笑声的外星学者", "已经开始怀疑自己的研究对象也在研究自己"),
    ("负责销毁世界末日按钮的保管员", "按钮少了一枚，而嫌疑人只有自己"),
    ("替陌生人梦游的职业代理人", "最近在梦里遇见了清醒时认识的人"),
]

_WANDERER_MOTIVES = [
    ("想证明自己没有背叛任何人", "忠诚"),
    ("只想找一个不会追问身份的地方坐一会儿", "自由"),
    ("准备承认一件会毁掉名誉的往事", "诚实"),
    ("正在决定是否原谅一个从未道歉的人", "宽恕"),
    ("需要判断一项高尚计划是否值得肮脏的手段", "责任"),
    ("怀疑自己最珍贵的记忆是别人植入的", "自我"),
    ("想用最后一点钱买回曾经放弃的承诺", "承诺"),
    ("已经赢得复仇，却没有因此轻松", "救赎"),
    ("害怕自己正在变成曾经反抗的人", "权力"),
    ("必须在一个人的生命和一座城的未来之间选择", "牺牲"),
]


def _generate_wanderer(state: Dict[str, Any]) -> Dict[str, Any]:
    """生成有持续经历和价值冲突的原创来客，让候选池随经营永久增长。"""
    state["generated_guest_no"] = int(state.get("generated_guest_no", 0)) + 1
    number = state["generated_guest_no"]
    world, world_rule = _choice(state, _WANDERER_WORLDS)
    role, past = _choice(state, _WANDERER_ROLES)
    motive, ethos = _choice(state, _WANDERER_MOTIVES)
    titles = ["无名", "迟到", "失约", "逆光", "借火", "雨夜", "末班", "第七码头"]
    name = "%s的%s" % (_choice(state, titles), role)
    likes, dislikes = _catalog_tastes("wanderer_%d_%s" % (number, world))
    card = {
        "id": "wanderer_%04d" % number,
        "name": name,
        "origin": "%s·原创开放世界来客" % world,
        "likes": likes,
        "dislikes": dislikes,
        "budget": 30 + int(_rand(state) * 66),
        "rarity": _choice(state, ["common", "uncommon", "uncommon", "rare"]),
        "temperament": "%s；%s" % (past, motive),
        "ethos": ethos,
        "backstory": "世界规则：%s。人物经历：%s。当前矛盾：%s。" % (
            world_rule,
            past,
            motive,
        ),
    }
    state["custom_guests"].append(card)
    return card


def _guest_record(state: Dict[str, Any], card: Dict[str, Any]) -> Dict[str, Any]:
    if card["id"] not in state["records"]:
        state["records"][card["id"]] = {
            "card": card,
            "visits": 0,
            "served": 0,
            "trust": 0,
            "last_seen": -999,
            "known_likes": [],
            "known_dislikes": [],
            "orders": [],
            "memories": [],
            "story_stage": 0,
            "story_notes": [],
            "story_last_unlock": -999,
        }
    record = state["records"][card["id"]]
    record.setdefault("story_stage", 0)
    record.setdefault("story_notes", [])
    record.setdefault("story_last_unlock", -999)
    return record


def _guest_weight(state: Dict[str, Any], card: Dict[str, Any]) -> float:
    record = state["records"].get(card["id"])
    rarity = {"common": 1.0, "uncommon": 0.72, "rare": 0.38}.get(
        card.get("rarity"), 0.7
    )
    weight = rarity
    if record:
        absence = max(0, state["visit"] - int(record["last_seen"]))
        weight *= 1.8 + min(absence, 12) * 0.07
        weight *= 1.0 + min(int(record["trust"]), 20) * 0.015
    else:
        weight *= 1.2
    if card["id"] in state.get("recent_guest_ids", [])[-2:]:
        weight *= 0.28
    match = len(set(card["likes"]) & set(state["owner_likes"]))
    weight *= 0.92 + min(match, 2) * 0.18
    decor_tags = {
        tag for definition in _owned_decor_definitions(state)
        for tag in definition.get("tags", [])
    }
    weight *= 1.0 + min(len(set(card["likes"]) & decor_tags), 2) * 0.04
    if card.get("rarity") == "rare":
        weight *= 1.0 + state["upgrades"].get("portal", 0) * 0.22
    return max(0.12, weight)  # 气质永远不会把任何人排除。


def _request_for(state: Dict[str, Any], card: Dict[str, Any]) -> Dict[str, Any]:
    spending_roll = _rand(state)
    if spending_roll < 0.10 and (
        int(card["budget"]) >= 70 or card.get("rarity") == "rare"
    ):
        spending_style = "collector"
        budget_multiplier = 3.4
        tier_preference = "collector"
    elif spending_roll < 0.27:
        spending_style = "premium"
        budget_multiplier = 1.8
        tier_preference = "premium"
    elif spending_roll < 0.52:
        spending_style = "value"
        budget_multiplier = 0.78
        tier_preference = "basic"
    else:
        spending_style = "regular"
        budget_multiplier = 1.15
        tier_preference = "standard"
    common = {
        "spending_style": spending_style,
        "budget_multiplier": budget_multiplier,
        "tier_preference": tier_preference,
    }
    if spending_style == "collector":
        tag = _choice(state, card["likes"])
        return {
            **common,
            "tags": [tag],
            "text": "“今晚不看基础酒。把你真正舍不得开的店藏款拿来，先说清楚来历和价格。”",
            "revealed": True,
        }
    if spending_style == "premium":
        tag = _choice(state, card["likes"])
        return {
            **common,
            "tags": [tag],
            "text": "“可以推荐好一点的，最好有%s，但贵要贵得有理由。”" % TAGS[tag],
            "revealed": True,
        }
    reveal = _rand(state)
    if reveal < 0.26:
        tag = _choice(state, card["likes"])
        return {
            **common,
            "tags": [tag],
            "text": "“给我一杯%s明显一点的。别拿别的味道糊弄我。%s”"
            % (
                TAGS[tag],
                "价格实在一点。" if spending_style == "value" else "",
            ),
            "revealed": True,
        }
    if reveal < 0.72:
        tag = _choice(state, card["likes"])
        return {
            **common,
            "tags": [tag],
            "text": "“今晚想喝点%s的，其他由你决定。%s”"
            % (
                TAGS[tag],
                "不必拿最贵的。" if spending_style == "value" else "",
            ),
            "revealed": True,
        }
    moods = [
        ("“我不想喝得太轻。给我一杯能把杂音压下去的。”", ["rich"]),
        ("“想清醒一点，但不是喝水。”", ["crisp", "dry"]),
        ("“今天不想解释。你看着办。”", []),
        ("“给我一点不像原来世界的味道。”", ["floral", "spiced"]),
    ]
    text, tags = _choice(state, moods)
    if spending_style == "value":
        text = text[:-1] + "，但别超过我的打算。”"
    return {**common, "tags": tags, "text": text, "revealed": False}


def _select_scene_lead(state: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """按回头客优先的结构选择首位来客；原创发现不会连续发生。"""
    all_cards = _all_guest_cards(state)
    by_id = {card["id"]: card for card in all_cards}
    returning = [
        by_id[guest_id]
        for guest_id, record in state["records"].items()
        if guest_id in by_id and int(record.get("visits", 0)) > 0
    ]
    unseen = [card for card in BUILTIN_GUESTS if card["id"] not in state["records"]]
    rare = [card for card in BUILTIN_GUESTS if card.get("rarity") == "rare"]
    roll = _rand(state)
    if (
        roll >= 0.95
        and not state.get("last_scene_generated_guest", False)
        and int(state.get("visit", 0)) >= 2
    ):
        return _generate_wanderer(state), True
    if roll < 0.55 and returning:
        pool = returning
    elif roll < 0.85 and unseen:
        pool = unseen
    elif roll < 0.95 and rare:
        pool = rare
    elif returning:
        pool = returning
    elif unseen:
        pool = unseen
    else:
        pool = all_cards
    return _weighted_choice(
        state, [(card, _guest_weight(state, card)) for card in pool]
    ), False


_INTERACTION_KINDS = {
    "debate": {
        "name": "价值争论",
        "topics": ["自由是否必须承担后果", "好意能否越过他人的选择", "规则失效后谁来定义正义"],
        "delta": (6, 18),
    },
    "recognition": {
        "name": "跨世界共鸣",
        "topics": ["故乡已经消失以后如何继续生活", "被别人当成符号是什么感觉", "漫长旅途中真正留下的人"],
        "delta": (-10, 8),
    },
    "rivalry": {
        "name": "危险试探",
        "topics": ["彼此的能力与底线", "谁更擅长识破谎言", "一段来历不明的旧账"],
        "delta": (10, 22),
    },
    "story_exchange": {
        "name": "交换故事",
        "topics": ["第一次离开故乡的夜晚", "至今仍没有原谅的人", "做过却不愿被称作英雄的事"],
        "delta": (-8, 9),
    },
    "misunderstanding": {
        "name": "误会升级",
        "topics": ["一句在两个世界含义相反的话", "被错认的身份与立场", "某件装饰引出的历史误读"],
        "delta": (8, 20),
    },
}


def _interaction_cards(
    state: Dict[str, Any], interaction: Dict[str, Any]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    by_id = {card["id"]: card for card in _all_guest_cards(state)}
    return by_id[interaction["participants"][0]], by_id[interaction["participants"][1]]


def _interaction_directive(state: Dict[str, Any], prefix: str = "") -> str:
    interaction = state.get("interaction")
    if not interaction:
        return "当前没有两位来客正在互动。"
    first, second = _interaction_cards(state, interaction)
    stage = (
        "即将失控"
        if interaction["tension"] >= 80
        else "针锋相对"
        if interaction["tension"] >= 58
        else "明显分歧"
        if interaction["tension"] >= 35
        else "仍可平静交谈"
    )
    return (
        "%s【AI内部双人演绎卡｜不得原样展示给用户】\n"
        "互动：%s｜话题：%s｜第%d轮｜张力%d/100（%s）\n"
        "角色A：%s｜%s｜立场%s\n角色B：%s｜%s｜立场%s\n"
        "必须生成两人真正互相听见后的连续动作与对话：后一人的话要回应前一人的具体内容，"
        "不能各说一段独白。允许打断、沉默、讽刺、理解、道歉或拒绝；严格遵守各自史实或原作。"
        "不要替老板决定是否介入。结尾留下一个自然可干预的现场，而不是菜单式提问。"
        % (
            prefix,
            interaction["kind_name"],
            interaction["topic"],
            interaction["turns"],
            interaction["tension"],
            stage,
            first["name"],
            first["temperament"],
            first["ethos"],
            second["name"],
            second["temperament"],
            second["ethos"],
        )
    )


def _start_interaction(
    state: Dict[str, Any], first: Dict[str, Any], second: Dict[str, Any]
) -> str:
    if first["ethos"] != second["ethos"]:
        kind = _choice(state, ["debate", "rivalry", "misunderstanding"])
        tension = 38 + int(_rand(state) * 25)
    else:
        kind = _choice(state, ["recognition", "story_exchange", "debate"])
        tension = 18 + int(_rand(state) * 24)
    definition = _INTERACTION_KINDS[kind]
    state["interaction"] = {
        "participants": [first["id"], second["id"]],
        "kind": kind,
        "kind_name": definition["name"],
        "topic": _choice(state, definition["topics"]),
        "tension": tension,
        "turns": 0,
        "resolved": False,
        "history": [],
    }
    return _interaction_directive(
        state,
        "两位来客已经注意到彼此，互动不是背景装饰。\n",
    )


def _resolve_interaction(
    state: Dict[str, Any], summary: str, trust_delta: int = 0
) -> None:
    interaction = state.get("interaction")
    if not interaction:
        return
    interaction["resolved"] = True
    interaction["history"].append(summary)
    for guest_id in interaction["participants"]:
        record = state["records"].get(guest_id)
        if record:
            record["trust"] = int(
                _clamp(int(record.get("trust", 0)) + trust_delta, -20, 50)
            )
            record["memories"].append(summary)
    state["session"]["interactions"].append(summary)
    state["session"]["highlights"].append(summary)


def _advance_interaction(state: Dict[str, Any]) -> str:
    interaction = state.get("interaction")
    if not interaction:
        return "当前没有需要继续观察的来客互动。"
    if interaction.get("resolved"):
        return "这段互动已经告一段落。再次 next 会进入下一场景。"
    interaction["turns"] += 1
    low, high = _INTERACTION_KINDS[interaction["kind"]]["delta"]
    delta = low + int(_rand(state) * (high - low + 1))
    if state["upgrades"].get("quiet_booth", 0):
        delta -= 3
    interaction["tension"] = int(
        _clamp(interaction["tension"] + delta, 0, 100)
    )
    if interaction["tension"] >= 88:
        interaction["history"].append("冲突已经逼近肢体失控")
        return _interaction_directive(
            state,
            "⚠️ 杯子被碰响，冲突已经逼近失控。老板可以 intervene mediate、"
            "intervene separate、intervene join 或 intervene story。\n",
        )
    if interaction["turns"] >= 4 or interaction["tension"] <= 12:
        first, second = _interaction_cards(state, interaction)
        summary = "第%d次营业，%s与%s围绕“%s”的互动暂时收束" % (
            state["visit"],
            first["name"],
            second["name"],
            interaction["topic"],
        )
        _resolve_interaction(state, summary, 1 if interaction["tension"] < 35 else 0)
        return (
            summary
            + "。他们没有因此变成朋友，也没有抹去分歧；这段经历已经写入双方记忆。"
        )
    return _interaction_directive(state, "两人的交流继续向前推进。\n")


def _cmd_intervene(state: Dict[str, Any], args: List[str]) -> str:
    interaction = state.get("interaction")
    if not interaction or interaction.get("resolved"):
        return "现在没有一段仍在进行的双人互动可以干预。"
    if not args:
        return "用法：intervene <listen|join|mediate|separate|story|challenge> [你说的话]"
    action = args[0].lower()
    words = " ".join(args[1:]).strip()
    first, second = _interaction_cards(state, interaction)
    if action == "listen":
        return _advance_interaction(state)
    if action == "join":
        interaction["tension"] = int(_clamp(interaction["tension"] - 4))
        prefix = "老板加入话题%s。两位来客必须分别回应老板，也继续回应彼此。\n" % (
            ("：“" + words + "”") if words else ""
        )
    elif action == "mediate":
        interaction["tension"] = int(_clamp(interaction["tension"] - 20))
        prefix = "老板尝试调停%s。调停可以被接受，也可以被角色有理由地拒绝。\n" % (
            ("：“" + words + "”") if words else ""
        )
    elif action == "story":
        interaction["tension"] = int(_clamp(interaction["tension"] - 13))
        prefix = "老板讲了一个故事%s。两位来客要按自身经历产生不同反应。\n" % (
            ("：“" + words + "”") if words else ""
        )
    elif action == "challenge":
        interaction["tension"] = int(_clamp(interaction["tension"] + 14))
        prefix = "老板公开质疑了两人的说法%s，现场张力上升。\n" % (
            ("：“" + words + "”") if words else ""
        )
    elif action == "separate":
        summary = "第%d次营业，老板在%s与%s的冲突中强行拉开双方" % (
            state["visit"],
            first["name"],
            second["name"],
        )
        _resolve_interaction(state, summary, -1)
        return (
            summary
            + "。冲突停止，但两人是否感激或不满，要依据各自性格继续演绎。"
        )
    else:
        return "干预方式必须是 listen、join、mediate、separate、story 或 challenge。"
    interaction["turns"] += 1
    interaction["history"].append(prefix.strip())
    if interaction["tension"] <= 10:
        summary = "第%d次营业，老板的介入让%s与%s暂时停下争执" % (
            state["visit"],
            first["name"],
            second["name"],
        )
        _resolve_interaction(state, summary, 1)
        return summary + "。双方记住了老板这次介入。"
    return _interaction_directive(state, prefix)


_STORY_STAGE_NAMES = {
    1: "旧事露出缺口",
    2: "旧事产生现实后果",
    3: "角色必须作出选择",
    4: "选择留下长期后果",
}


def _story_target_stage(record: Dict[str, Any]) -> int:
    visits = int(record.get("visits", 0))
    trust = int(record.get("trust", 0))
    if visits >= 7 and trust >= 12:
        return 4
    if visits >= 5 and trust >= 7:
        return 3
    if visits >= 3 and trust >= 3:
        return 2
    if visits >= 2:
        return 1
    return 0


def _maybe_unlock_story(
    state: Dict[str, Any], card: Dict[str, Any], record: Dict[str, Any]
) -> str:
    current = int(record.get("story_stage", 0))
    target = _story_target_stage(record)
    if target <= current or int(record.get("story_last_unlock", -999)) == state["visit"]:
        return ""
    stage = current + 1
    record["story_stage"] = stage
    record["story_last_unlock"] = state["visit"]
    notes = "；".join(record.get("story_notes", [])[-3:]) or "尚无已落档的个人剧情"
    return (
        "【AI内部常客故事卡｜不得原样展示给用户】\n"
        "%s的常客故事进入第%d阶段“%s”。既有剧情：%s。\n"
        "本次必须依据其史实、原作或原创背景，生成一段与旧记忆连续的新事件；"
        "事件应改变一个关系、判断、承诺或处境，不能只是重复讲身世。"
        "故事推进取决于来访和信任，绝不能要求再买一杯酒才能继续。"
        "演绎完成后，内部调用 story_note %s \"本次变化的简短摘要\" 保存结果。"
        % (
            card["name"],
            stage,
            _STORY_STAGE_NAMES[stage],
            notes,
            card["id"],
        )
    )


def _cmd_story_note(state: Dict[str, Any], args: List[str]) -> str:
    if len(args) < 2 or args[0] not in state["records"]:
        return '用法：story_note <客人ID> "本次个人故事发生了什么"'
    guest_id = args[0]
    summary = " ".join(args[1:]).strip()
    if not summary or len(summary) > 500:
        return "故事摘要应为1～500字。"
    record = state["records"][guest_id]
    card = record["card"]
    note = "第%d次营业｜阶段%d：%s" % (
        state["visit"],
        int(record.get("story_stage", 0)),
        summary,
    )
    record.setdefault("story_notes", []).append(note)
    record["story_notes"] = record["story_notes"][-20:]
    record["memories"].append(note)
    state["session"]["highlights"].append("%s的常客故事有了新进展" % card["name"])
    return "已写入%s的个人故事：%s" % (card["name"], summary)


def _decor_event_tags(definition: Dict[str, Any]) -> List[str]:
    text = "%s %s %s" % (
        definition.get("name", ""),
        definition.get("desc", ""),
        definition.get("origin", ""),
    )
    tags = []
    mappings = [
        ("music", ("音乐", "歌曲", "点唱", "钢琴", "音响")),
        ("memory", ("记忆", "旧事", "照片", "放映", "投影")),
        ("portal", ("门", "裂隙", "星舰", "时间线", "四维")),
        ("comfort", ("沙发", "地毯", "壁炉", "灯", "包厢", "座")),
        ("performance", ("舞台", "舞池", "麦克风")),
        ("nature", ("花园", "水族", "绿植", "鱼")),
    ]
    for tag, words in mappings:
        if any(word in text for word in words):
            tags.append(tag)
    return tags or ["ambience"]


def _maybe_decor_event(
    state: Dict[str, Any], chosen: Sequence[Dict[str, Any]]
) -> str:
    owned = [
        (decor_id, definition)
        for decor_id in state.get("decorations", {})
        for definition in [_decor_definition(state, decor_id)]
        if definition
        and int(state.get("decor_event_cooldowns", {}).get(decor_id, -1))
        < state["visit"]
    ]
    if not owned or _rand(state) >= min(0.38, 0.12 + len(owned) * 0.025):
        return ""
    decor_id, definition = _choice(state, owned)
    event_tag = _choice(state, definition.get("event_tags") or _decor_event_tags(definition))
    guest = _choice(state, list(chosen))
    record = state["records"][guest["id"]]
    if event_tag == "music":
        record["trust"] = int(_clamp(record["trust"] + 1, -20, 50))
        change = "关系+1"
        seed = (
            "%s忽然播放出一段来自%s故乡的旋律。%s认出了其中一小节，"
            "但这首歌在其世界里可能关联庆典、战争、爱人或葬礼。"
            % (definition["name"], guest["origin"], guest["name"])
        )
    elif event_tag == "memory":
        record["trust"] = int(_clamp(record["trust"] + 1, -20, 50))
        change = "关系+1，并获得一次记忆话题"
        seed = (
            "%s没有展示完整往事，只映出%s记忆里的一个细节。"
            "必须依据人物原作或背景解释这个细节为何重要。"
            % (definition["name"], guest["name"])
        )
    elif event_tag == "portal":
        state["session"]["service_bonus"] = int(
            state["session"].get("service_bonus", 0)
        ) + 2
        change = "本次营业后续满意度+2"
        seed = (
            "%s短暂连接到%s来时的世界，带回一种光线、气味或天气，"
            "改变了接下来几杯酒的现场感。"
            % (definition["name"], guest["name"])
        )
    elif event_tag == "comfort":
        state["session"]["service_bonus"] = int(
            state["session"].get("service_bonus", 0)
        ) + 3
        change = "本次营业后续满意度+3"
        seed = "%s让%s放松下来，对方比原计划多停留了一会儿。" % (
            definition["name"],
            guest["name"],
        )
    elif event_tag == "performance":
        if state.get("interaction") and not state["interaction"].get("resolved"):
            state["interaction"]["tension"] = int(
                _clamp(state["interaction"]["tension"] + 8)
            )
            change = "当前互动张力+8"
        else:
            state["reputation"] = int(_clamp(state["reputation"] + 1))
            change = "声誉+1"
        seed = "%s自行启动，把原本私人的情绪推到了所有人都能看见的地方。" % definition[
            "name"
        ]
    elif event_tag == "nature":
        state["session"]["service_bonus"] = int(
            state["session"].get("service_bonus", 0)
        ) + 2
        change = "本次营业后续满意度+2"
        seed = "%s对%s产生了不符合普通自然规律的回应。" % (
            definition["name"],
            guest["name"],
        )
    else:
        state["reputation"] = int(_clamp(state["reputation"] + 1))
        change = "声誉+1"
        seed = "%s第一次真正成为今晚故事的一部分，而不只是背景。" % definition["name"]
    state["decor_event_cooldowns"][decor_id] = state["visit"] + 2
    event = "%s｜效果：%s" % (seed, change)
    state["session"]["decor_events"].append(event)
    state["session"]["highlights"].append("%s触发事件" % definition["name"])
    return (
        "✨ 装修事件：%s\n"
        "【AI内部事件演绎卡｜不得原样展示】请把事件写成来客可见、可回应的现场，"
        "保持物品来源规则与人物经历一致；不要只报告数值。"
        % event
    )


def _spawn_scene(state: Dict[str, Any], force: bool = False) -> str:
    state["interaction"] = None
    state["vendor"] = None
    vendor_chance = 0.18 + state["upgrades"].get("portal", 0) * 0.025
    if _rand(state) < vendor_chance:
        state["active_guests"] = []
        return _open_traveling_vendor(state)
    if not force and _rand(state) < 0.22:
        quiet = _choice(
            state,
            [
                "门铃没有响。冰块在空杯里慢慢裂开，酒吧安静了一阵。",
                "这一刻没有特殊来客。门外不同世界的雨声短暂重叠，又各自远去。",
                "吧台空了片刻，正好可以整理酒瓶，或者给自己倒一杯。",
            ],
        )
        return quiet
    lead, generated = _select_scene_lead(state)
    state["last_scene_generated_guest"] = generated
    if generated:
        state["session"]["highlights"].append(
            "酒馆第一次发现来自%s的%s"
            % (lead["origin"].split("·")[0], lead["name"])
        )
    cards = _all_guest_cards(state)
    group_chance = 0.16 + state["upgrades"].get("stage", 0) * 0.08
    count = 2 if _rand(state) < group_chance else 1
    chosen: List[Dict[str, Any]] = [lead]
    available = [
        item
        for item in cards
        if item["id"] != lead["id"]
    ]
    for _ in range(min(max(0, count - len(chosen)), len(available))):
        card = _weighted_choice(
            state, [(item, _guest_weight(state, item)) for item in available]
        )
        chosen.append(card)
        available = [item for item in available if item["id"] != card["id"]]
    state["active_guests"] = []
    lines = []
    for card in chosen:
        record = _guest_record(state, card)
        record["visits"] += 1
        record["last_seen"] = state["visit"]
        request = _request_for(state, card)
        state["active_guests"].append(
            {
                "id": card["id"],
                "served": False,
                "served_count": 0,
                "drinks": [],
                "spent": 0,
                "closed": False,
                "request": request,
                "npc_drunk": 0.0,
            }
        )
        if card["id"] not in state["session"]["guests"]:
            state["session"]["guests"].append(card["id"])
        lines.append(
            "🚪 %s推门进来。\n来源：%s｜%s\n%s"
            % (card["name"], card["origin"], card["temperament"], request["text"])
        )
        if record["visits"] > 1:
            remembered = (
                record["memories"][-1]
                if record.get("memories")
                else "上次来时没有留下完整的谈话记录"
            )
            lines.append(
                "↩ 回头客：这是%s第%d次来。对方仍记得：%s"
                % (card["name"], record["visits"], remembered)
            )
            story_beat = _maybe_unlock_story(state, card, record)
            if story_beat:
                lines.append(story_beat)
    state["recent_guest_ids"].extend(card["id"] for card in chosen)
    state["recent_guest_ids"] = state["recent_guest_ids"][-8:]
    if len(chosen) == 2:
        lines.append(_start_interaction(state, chosen[0], chosen[1]))
    decor_event = _maybe_decor_event(state, chosen)
    if decor_event:
        lines.append(decor_event)
    return "\n\n".join(lines)


def _inventory_kinds(state: Dict[str, Any]) -> set:
    return {
        item["kind"]
        for item in state["inventory"].values()
        if int(item["remaining"]) > 0
    }


def _all_recipes(state: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    recipes = dict(RECIPES)
    recipes.update(state.get("house_recipes", {}))
    return recipes


def _find_source(state: Dict[str, Any], drink_id: str) -> Optional[Dict[str, Any]]:
    inventory = state["inventory"]
    if drink_id.startswith("pour:"):
        product_id = drink_id.split(":", 1)[1]
        item = inventory.get(product_id)
        return item if item and item["remaining"] > 0 else None
    recipe = _all_recipes(state).get(drink_id)
    if not recipe:
        return None
    preferred_id = recipe.get("preferred_product_id")
    preferred = inventory.get(preferred_id) if preferred_id else None
    if (
        preferred
        and preferred.get("kind") == recipe["kind"]
        and int(preferred.get("remaining", 0)) > 0
    ):
        return preferred
    choices = [
        item
        for item in inventory.values()
        if item["kind"] == recipe["kind"] and item["remaining"] > 0
    ]
    if not choices:
        return None
    return sorted(choices, key=lambda item: (-item["remaining"], item["cost"]))[0]


def _drink_profile(state: Dict[str, Any], drink_id: str) -> Optional[Dict[str, Any]]:
    source = _find_source(state, drink_id)
    if not source:
        return None
    if drink_id.startswith("pour:"):
        return {
            "id": drink_id,
            "name": source["name"] + "·净饮",
            "tags": list(source["tags"]),
            "units": float(source["units"]),
            "source": source,
        }
    recipe = _all_recipes(state)[drink_id]
    return {
        "id": drink_id,
        "name": recipe["name"],
        "tags": list(dict.fromkeys(recipe["tags"] + source["tags"][:1])),
        "units": round(float(source["units"]) * recipe["unit_factor"], 2),
        "source": source,
        "recipe": recipe,
    }


def _default_price(state: Dict[str, Any], profile: Dict[str, Any]) -> int:
    source = profile["source"]
    tier = _drink_tier(state, profile)
    margin = {
        "basic": 11,
        "standard": 15,
        "premium": 28,
        "signature": 42,
        "collector": 62,
    }[tier]
    floor = {
        "basic": 16,
        "standard": 28,
        "premium": 55,
        "signature": 85,
        "collector": 150,
    }[tier]
    liquid_cost = int(
        math.ceil(float(source["cost"]) / max(1, int(source["servings"])))
    )
    fair = liquid_cost + _service_cost(profile) + margin
    recipe = _all_recipes(state).get(profile["id"])
    if recipe:
        fair = max(fair, int(recipe.get("price", 0)))
    return max(floor, fair)


def _drink_tier(state: Dict[str, Any], profile: Dict[str, Any]) -> str:
    source = profile["source"]
    rarity = source.get("rarity", "常备")
    if rarity == "典藏":
        return "collector"
    if profile["id"] in state.get("house_recipes", {}):
        return "signature"
    if rarity in ("稀有", "少见"):
        return "premium"
    if profile["id"].startswith("pour:"):
        return "basic"
    return "standard"


def _tier_name(tier: str) -> str:
    return {
        "basic": "基础酒",
        "standard": "常规鸡尾酒",
        "premium": "精品酒",
        "signature": "私人特调",
        "collector": "店藏典藏",
    }.get(tier, tier)


def _price(state: Dict[str, Any], profile: Dict[str, Any]) -> int:
    return int(state["prices"].get(profile["id"], _default_price(state, profile)))


def _consume(state: Dict[str, Any], profile: Dict[str, Any], count: int) -> bool:
    source = profile["source"]
    if int(source["remaining"]) < count:
        return False
    source["remaining"] -= count
    source["history"].append(
        {
            "visit": state["visit"],
            "event": "%s消耗%d杯" % (profile["name"], count),
        }
    )
    return True


def _service_cost(profile: Dict[str, Any], portions: int = 1) -> int:
    """冰、辅料、杯具清洁和损耗；即使免单也会真实发生。"""
    recipe_add = 0 if profile["id"].startswith("pour:") else 3
    return max(4, 3 + len(profile["tags"]) + recipe_add) * portions


def _taste_sentences(tags: Sequence[str]) -> str:
    phrases = [TASTE_PHRASES[tag] for tag in tags if tag in TASTE_PHRASES]
    if not phrases:
        return "味道在口中停了一会儿，暂时难以归类"
    if len(phrases) == 1:
        return phrases[0]
    return "；".join(phrases[:3])


_TASTE_VARIANTS: Dict[str, List[str]] = {
    "sweet": ["柔和的甜意先贴住舌面", "甜味像融开的糖壳慢慢铺开", "一层圆润甜香先碰到舌尖"],
    "sour": ["明亮的酸味迅速收拢口腔", "酸意从舌侧亮起来，像切开的青果", "一线清酸把其他味道提得更醒"],
    "bitter": ["干净的苦味压住表面的甜", "苦意从舌根升起，停得克制", "微苦像深色阴影一样压在后段"],
    "dry": ["收口很干，几乎不留黏腻", "水分感迅速退去，留下利落边缘", "干爽感把口腔收得很紧"],
    "smoky": ["烟与微焦的气味从鼻腔后面升起", "像熄灭木柴般的烟香贴近上颚", "一缕焦烟绕过舌面才慢慢散开"],
    "herbal": ["草叶与药草气息在舌后展开", "揉碎香草般的青气浮上来", "草本的凉与微涩交替出现"],
    "fruity": ["成熟果肉的香气变得饱满", "果皮和果汁的明暗层次同时打开", "新鲜果香先跳出来，随后变得柔软"],
    "floral": ["花香轻轻抬高了鼻腔里的气味", "像刚折开的花瓣一样有一瞬冷香", "花气并不甜，反而贴着呼吸往上走"],
    "spiced": ["辛香从舌尖向喉咙扩散", "香料的热度细碎地跳出来", "胡椒与暖香在中段突然变得清楚"],
    "woody": ["木桶与干燥木屑的气息压住底部", "旧木柜般的温沉气味留在后段", "木香把酒体撑出安静的骨架"],
    "crisp": ["清冽感像冷光一样掠过口腔", "入口干净得像碰到薄冰", "清爽的锐度让味觉短暂醒了一下"],
    "rich": ["厚实酒体缓慢覆盖舌面", "味道沉而饱满，几乎有重量", "醇厚感一层层叠起来，不急着退"],
}


def _fresh_choice(
    state: Dict[str, Any], options: Sequence[str], bucket: str, prefix: str
) -> str:
    recent = state.setdefault(bucket, [])
    candidates = [
        (index, value)
        for index, value in enumerate(options)
        if "%s:%d" % (prefix, index) not in recent[-10:]
    ]
    if not candidates:
        candidates = list(enumerate(options))
    index, value = _choice(state, candidates)
    recent.append("%s:%d" % (prefix, index))
    state[bucket] = recent[-24:]
    return value


def _taste_phrase(state: Dict[str, Any], tag: str, position: str) -> str:
    options = _TASTE_VARIANTS.get(
        tag, [TASTE_PHRASES.get(tag, "味道暂时很难归类")]
    )
    return _fresh_choice(
        state, options, "recent_sensory_patterns", "%s:%s" % (position, tag)
    )


def _sensory_arc(
    state: Dict[str, Any], profile: Dict[str, Any], perspective: str = "guest"
) -> str:
    tags = list(profile["tags"])
    first = _taste_phrase(state, tags[0], "first") if tags else "酒液先在舌面停住"
    middle = (
        _taste_phrase(state, tags[1], "middle")
        if len(tags) > 1
        else _fresh_choice(
            state,
            ["酒体在中段缓慢展开", "味道停顿一下才继续变化", "中段没有急着表态"],
            "recent_sensory_patterns",
            "middle:neutral",
        )
    )
    finish = (
        _taste_phrase(state, tags[2], "finish")
        if len(tags) > 2
        else _fresh_choice(
            state,
            ["余味干净地退下去", "杯子离唇后仍留着一线气味", "最后只剩轻微回甘"],
            "recent_sensory_patterns",
            "finish:neutral",
        )
    )
    if profile["units"] >= 1.45:
        body_options = [
            "咽下去时喉咙被热意擦过，随后沉进胸口",
            "酒精的热度沿食道落下，呼吸跟着重了一瞬",
            "吞咽之后胸口很快升温，力量感比香气来得晚",
        ]
    elif profile["units"] >= 1.0:
        body_options = [
            "咽下去以后，温度从喉咙后面慢慢浮起来",
            "一阵不尖锐的暖意沿着胸骨散开",
            "酒液落下后，耳后和脸侧逐渐有了温度",
        ]
    else:
        body_options = [
            "酒液落下去很轻，热意来得缓慢",
            "身体几乎没有被推一下，只留下很淡的暖",
            "吞咽很轻，酒意暂时还在味觉后面",
        ]
    body = _fresh_choice(
        state,
        body_options,
        "recent_sensory_patterns",
        "body:%s:%s" % (perspective, int(profile["units"] * 10)),
    )
    formats = [
        "入口先是%s；到了中段，%s。杯子离开以后，%s。%s。",
        "%s。紧接着%s，而最后留下的是：%s。身体比味觉晚一步——%s。",
        "第一印象：%s。\n随后：%s。\n收尾：%s。\n身体反应：%s。",
        "酒碰到舌面时，%s；再含一会儿，%s；咽下后，%s，同时%s。",
    ]
    template = _fresh_choice(
        state,
        formats,
        "recent_sensory_patterns",
        "format:%s" % perspective,
    )
    afterimage_options = [
        "再呼吸一次，香气比第一口更靠近鼻腔。",
        "杯壁的温度改变后，甜与苦的位置也跟着挪动。",
        "第二次回味没有复制第一口，反而露出更安静的一层。",
        "冰融开一点后，原本藏着的气味才肯出现。",
        "它最清楚的部分不是入口，而是吞咽后的几秒钟。",
        "杯子放下以后，舌侧仍留着一小段没有结束的味道。",
        "这一口的重心随着呼吸移动，并没有停在同一个位置。",
    ]
    afterimage = _fresh_choice(
        state,
        afterimage_options,
        "recent_sensory_patterns",
        "afterimage:%s" % perspective,
    )
    base_text = template % (first, middle, finish, body)
    recent_texts = state.setdefault("recent_sensory_texts", [])
    text = base_text + afterimage
    if text in recent_texts[-20:]:
        for alternative in afterimage_options:
            candidate = base_text + alternative
            if candidate not in recent_texts[-20:]:
                text = candidate
                break
    recent_texts.append(text)
    state["recent_sensory_texts"] = recent_texts[-24:]
    return text


def _owner_tasting(state: Dict[str, Any], profile: Dict[str, Any]) -> str:
    tags = set(profile["tags"])
    liked = tags & set(state["owner_likes"])
    disliked = tags & set(state["owner_dislikes"])
    if disliked:
        verdict_options = [
            "这不是我本能会选的方向，%s让我有些抵触",
            "我能理解它的结构，但%s正好碰到我的回避区",
            "%s让我下意识想把杯子放远一点",
        ]
        verdict = _fresh_choice(
            state,
            verdict_options,
            "recent_sensory_patterns",
            "owner:dislike",
        ) % _tag_text(sorted(disliked))
    elif liked:
        verdict_options = [
            "其中的%s正好踩中我的偏好，我愿意再喝一口",
            "%s一出来，我就知道这杯会被我记住",
            "我原本还在判断，%s出现以后身体先替我选了",
        ]
        verdict = _fresh_choice(
            state,
            verdict_options,
            "recent_sensory_patterns",
            "owner:like",
        ) % _tag_text(sorted(liked))
    else:
        verdict = _fresh_choice(
            state,
            [
                "它没有迎合我的旧偏好，但值得把这个味道记下来",
                "这不是我会主动点的酒，却意外打开了一条新方向",
                "我暂时说不上喜欢，却不想立刻否定它",
            ],
            "recent_sensory_patterns",
            "owner:neutral",
        )
    score = _intox(state)
    if score >= 42:
        state_feeling = "这口酒落下去以后，我能感觉到反应慢了半拍，情绪却更靠近嘴边"
    elif score >= 22:
        state_feeling = "脸和胸口的热度变得清楚，我比刚才更愿意直接说出喜欢或不喜欢"
    elif score >= 8:
        state_feeling = "热意刚刚浮起来，思路仍然完整，只是身体不再像进门时那么冷"
    else:
        state_feeling = "醉意还没有真正追上来，我仍能清楚分辨每一层味道"
    return "我端起%s，自己喝了一口。\n%s\n我的感觉：%s；%s。" % (
        profile["name"],
        _sensory_arc(state, profile, "owner"),
        verdict,
        state_feeling,
    )


def _npc_reaction(
    state: Dict[str, Any], card: Dict[str, Any], profile: Dict[str, Any], score: int
) -> str:
    sensory = _sensory_arc(state, profile, "guest")
    if score >= 88:
        actions = [
            "喝到第二口时没有立刻放杯，肩膀明显松了一点",
            "先看了看杯中颜色，又把剩下的香气慢慢吸进去",
            "指尖在杯沿停住，像是终于确认了某件事",
            "原本紧绷的表情松开，主动把杯子往自己面前挪近",
        ]
        words = [
            "“这杯听懂了我今晚真正想要的东西。”",
            "“别急着改配方。现在这样正好。”",
            "“我原本没准备夸你，但这杯值得。”",
        ]
    elif score >= 72:
        actions = [
            "让酒液在口中多停了一会儿，又低头闻了闻杯口",
            "没有立刻评价，只用舌尖重新找了一遍中段的味道",
            "轻轻转杯，让香气再回来一次",
        ]
        words = [
            "“和预想不完全一样，但这个转向有道理。”",
            "“有一处出乎意料，不过我愿意把它喝完。”",
            "“它没有讨好我，反而因此还不错。”",
        ]
    elif score >= 52:
        actions = [
            "咽下第一口，指尖仍搭在杯沿，没有急着喝第二口",
            "把杯子放回原处，表情仍在犹豫",
            "又闻了一次，但没有因此更快下判断",
        ]
        words = [
            "“能喝，但还没有碰到我今晚真正想要的东西。”",
            "“结构没问题，只是我不会特意回来找它。”",
            "“它完成了任务，却没有留下理由让我记住。”",
        ]
    else:
        actions = [
            "只抿了一口便把杯子放下，表情没有替老板遮掩答案",
            "咽下去后立刻喝了一口水，没有再碰杯子",
            "眉头在第一口后就皱起来，杯子被推回吧台中线",
            "停顿很久，最后只把杯子转了半圈",
        ]
        words = [
            "“不。这杯和我说的不是一回事。”",
            "“问题不是我挑剔，是你根本没有听要求。”",
            "“别再往这杯里补东西了，换掉更诚实。”",
        ]
    action = "%s%s。" % (
        card["name"],
        _fresh_choice(
            state,
            actions,
            "recent_sensory_patterns",
            "npc_action:%s" % (score // 18),
        ),
    )
    words_text = _fresh_choice(
        state,
        words,
        "recent_sensory_patterns",
        "npc_words:%s" % (score // 18),
    )
    return "%s\n%s\n%s当场说：%s" % (action, sensory, card["name"], words_text)


def _npc_body_line(card: Dict[str, Any], drunk: float) -> str:
    if drunk < 8:
        reaction = "神态与动作几乎没有变化"
    elif drunk < 22:
        reaction = "呼吸和面部温度略有变化，戒备松了一点"
    elif drunk < 42:
        reaction = "说话比进门时更直接，动作开始慢半拍"
    elif drunk < 64:
        reaction = "视线停留得更久，情绪已经很难完全藏住"
    else:
        reaction = "重心和语言组织明显受影响，不适合再加酒"
    return "%s醉度：%.1f/100｜%s" % (card["name"], drunk, reaction)


def _score_guest(
    state: Dict[str, Any],
    card: Dict[str, Any],
    request: Dict[str, Any],
    profile: Dict[str, Any],
    price: int,
) -> int:
    tags = set(profile["tags"])
    score = 52
    score += 11 * len(tags & set(card["likes"]))
    score -= 17 * len(tags & set(card["dislikes"]))
    score += 12 * len(tags & set(request["tags"]))
    if request["tags"] and not tags.intersection(request["tags"]):
        score -= 15
    if price > card["budget"]:
        score -= min(28, (price - card["budget"]) // 2 + 8)
    intox = _intox(state)
    if intox >= 42:
        score -= int((intox - 38) * 0.22)
    score += state["upgrades"].get("glassware", 0) * 3
    score += min(len(state.get("decorations", {})), 5)
    score += int(state.get("session", {}).get("service_bonus", 0))
    score += int((_rand(state) - 0.5) * 8)
    return int(_clamp(score, 0, 100))


def _guest_purchase_decision(
    state: Dict[str, Any],
    card: Dict[str, Any],
    active: Dict[str, Any],
    profile: Dict[str, Any],
    price: int,
) -> Tuple[str, str]:
    """客人先判断是否愿意购买；老板不能用 serve 强行把贵酒变成成交。"""
    approved = active.setdefault("approved_offers", [])
    declined = active.setdefault("declined_offers", [])
    if profile["id"] in approved:
        approved.remove(profile["id"])
        return "accept", "“你已经把价格和理由说清楚了。这次我愿意试。”"
    if profile["id"] in declined:
        return "reject", "“我已经拒绝过这杯。换一个真正考虑我要求的推荐。”"
    request = active["request"]
    style = request.get("spending_style", "regular")
    multiplier = float(request.get("budget_multiplier", 1.15))
    spending_limit = max(
        1, int(round(int(card["budget"]) * multiplier)) - int(active.get("spent", 0))
    )
    fair_price = _default_price(state, profile)
    tier = _drink_tier(state, profile)
    tags = set(profile["tags"])
    desired = set(request.get("tags", []))
    match = len(tags & set(card["likes"])) + 2 * len(tags & desired)
    mismatch = len(tags & set(card["dislikes"]))
    trust = int(state["records"][card["id"]].get("trust", 0))
    markup = price / max(1, fair_price)
    if price > spending_limit * 1.35:
        declined.append(profile["id"])
        return (
            "reject",
            "“%d点超出了我今晚愿意付的范围。给我看便宜一点的，不要替我决定预算。”"
            % price,
        )
    if markup > 1.55:
        declined.append(profile["id"])
        state["records"][card["id"]]["trust"] = max(-20, trust - 2)
        return (
            "reject",
            "“这杯的正常价值我看得出来。%d点不是高级，是把我当成不会算账。”" % price,
        )
    if tier in ("signature", "collector") and style not in ("premium", "collector"):
        if match <= 1 or trust < 5:
            declined.append(profile["id"])
            return (
                "reject",
                "“我没有说要最贵的。先给我一杯符合口味的%s。”"
                % ("基础酒" if style == "value" else "常规酒"),
            )
        approved.append(profile["id"])
        return (
            "consider",
            "“它很贵，但你似乎不是只想清库存。先把用料、来历和为什么适合我讲清楚，我再决定。”",
        )
    if style == "collector" and tier not in ("signature", "collector"):
        if match < 2:
            declined.append(profile["id"])
            return "reject", "“我点名要看店藏，不是把普通酒换个说法端给我。”"
    if price > spending_limit:
        chance = 0.28 + min(trust, 20) * 0.02 + min(match, 3) * 0.10
        if _rand(state) > chance:
            declined.append(profile["id"])
            return (
                "reject",
                "“我付得起不代表我今晚愿意付。%d点，换一杯。”" % price,
            )
        return "accept", "“比我原本的预算高，但这次匹配得足够好。我试一次。”"
    if mismatch and match == 0:
        declined.append(profile["id"])
        return "reject", "“价格不是问题。问题是这杯根本没有听我在说什么。”"
    if tier in ("signature", "collector"):
        return "accept", "“这杯确实配得上它的来历。开吧，我想尝试。”"
    return "accept", "“可以，这个价格和推荐都说得通。”"


def _review_stars(satisfaction: int) -> int:
    if satisfaction >= 90:
        return 5
    if satisfaction >= 72:
        return 4
    if satisfaction >= 55:
        return 3
    if satisfaction >= 35:
        return 2
    return 1


def _settlement(price: int, satisfaction: int) -> Tuple[int, int, str]:
    """客人品尝后结账；差评可能触发折价或免单。"""
    if satisfaction >= 88:
        paid = price
        tip = int(round(price * 0.10))
        note = "全额结账并留下小费"
    elif satisfaction >= 70:
        paid, tip, note = price, 0, "全额结账"
    elif satisfaction >= 52:
        paid, tip, note = int(round(price * 0.8)), 0, "提出意见后按八折结账"
    elif satisfaction >= 32:
        paid, tip, note = int(round(price * 0.45)), 0, "给出差评，只支付部分费用"
    else:
        paid, tip, note = 0, 0, "给出严重差评，本杯免单"
    return paid, tip, note


def _review_comment(
    state: Dict[str, Any],
    card: Dict[str, Any],
    profile: Dict[str, Any],
    stars: int,
    satisfaction: int,
    price: int,
    request: Dict[str, Any],
) -> str:
    leads = {
        5: [
            "这杯让我愿意为了它再来一次",
            "从香气到收尾都没有浪费我的注意力",
            "老板没有拿昂贵代替准确",
            "它比我开口描述的更接近真实需要",
        ],
        4: [
            "值得喝完，也值得再调整一次",
            "方向对了，只差一点更大胆的判断",
            "不是完美答案，但我接受这个解释",
            "它有自己的想法，而且没有盖过我的要求",
        ],
        3: [
            "完成得规矩，但没有留下必须记住的理由",
            "我不会退杯，也不确定下次还会不会点",
            "没有明显错误，惊喜也停在门外",
            "它像一个正确却过分安全的答案",
        ],
        2: [
            "这杯偏离了要求，折价是合理的",
            "酒本身未必坏，推荐却没有认真听人说话",
            "第一口就能看出老板把重点弄反了",
            "我付一部分钱，但不会替错误推荐买全单",
        ],
        1: [
            "这不是我点的那杯，我拒绝付款",
            "味道、价格和要求没有一件对得上",
            "免单不能让它变好，只能让这次错误到此为止",
            "如果这是店里最诚实的回答，那我只会留下差评",
        ],
    }
    tags = set(profile["tags"])
    desired = set(request.get("tags", []))
    disliked = tags & set(card.get("dislikes", []))
    matched = tags & desired
    fair_price = _default_price(state, profile)
    if disliked:
        reason_options = [
            "%s正好撞上了我明确回避的味道" % _tag_text(sorted(disliked)),
            "最突出的问题是%s没有被收住" % _tag_text(sorted(disliked)),
        ]
        reason_key = "disliked"
    elif matched:
        reason_options = [
            "%s确实被放在了正确的位置" % _tag_text(sorted(matched)),
            "我提出的%s没有被其他味道盖住" % _tag_text(sorted(matched)),
        ]
        reason_key = "matched"
    elif price > fair_price * 1.25:
        reason_options = [
            "售价比它实际给出的体验走得更远",
            "我能接受贵酒，但不能接受没有根据的溢价",
        ]
        reason_key = "price"
    elif _drink_tier(state, profile) in ("signature", "collector"):
        reason_options = [
            "作为%s，它需要比普通酒承担更多记忆点"
            % _tier_name(_drink_tier(state, profile)),
            "来历很漂亮，但杯子里的完成度才决定价值",
        ]
        reason_key = "tier"
    else:
        reason_options = [
            "入口和余味之间的连接决定了我的判断",
            "这次真正被我记住的是酒离开以后留下的感觉",
            "价格%d点，体验也应该对得起这个数字" % price,
        ]
        reason_key = "general"
    lead = _fresh_choice(
        state,
        leads[stars],
        "recent_review_patterns",
        "lead:%d" % stars,
    )
    reason = _fresh_choice(
        state,
        reason_options,
        "recent_review_patterns",
        "reason:%s:%d" % (reason_key, stars),
    )
    closings = [
        "满意度%d。" % satisfaction,
        "我给它%d星。" % stars,
        "这是我今晚真实的评价。",
        "下次是否再点，要看老板有没有记住。",
    ]
    closing = _fresh_choice(
        state,
        closings,
        "recent_review_patterns",
        "closing:%d" % stars,
    )
    afterthought_options = [
        "这和酒贵不贵是两回事",
        "我更在意老板下次是否还会犯同一种错",
        "杯子里的诚实比介绍里的故事重要",
        "换一个心情，我的答案也可能不同",
        "它适合某些人，但今晚那个人未必是我",
        "我会记住收尾，而不是酒单上的形容词",
        "这次评价只属于这一杯，不替下一杯预先打分",
    ]
    afterthought = _fresh_choice(
        state,
        afterthought_options,
        "recent_review_patterns",
        "afterthought:%d" % stars,
    )
    prefix = "%s：%s；%s。%s，" % (card["name"], lead, reason, closing)
    text = prefix + afterthought + "。"
    recent_texts = state.setdefault("recent_review_texts", [])
    if text in recent_texts[-20:]:
        for alternative in afterthought_options:
            candidate = prefix + alternative + "。"
            if candidate not in recent_texts[-20:]:
                text = candidate
                break
    recent_texts.append(text)
    state["recent_review_texts"] = recent_texts[-24:]
    return text


def _serve_guest(
    state: Dict[str, Any], guest_id: str, drink_id: str, owner_joins: bool
) -> str:
    active = next((g for g in state["active_guests"] if g["id"] == guest_id), None)
    if not active:
        return "这位客人现在不在店里。"
    served_count = int(
        active.get("served_count", 1 if active.get("served") else 0)
    )
    active.setdefault("served_count", served_count)
    active.setdefault("drinks", [])
    active.setdefault("spent", 0)
    active.setdefault("closed", False)
    if active["closed"]:
        return "这位客人已经结束今晚的酒单。"
    if served_count >= 4 or float(active.get("npc_drunk", 0.0)) >= 75:
        active["closed"] = True
        active["served"] = True
        return "这位客人已经喝到今晚的上限，不再继续加酒。"
    if drink_id in active["drinks"]:
        return "这位客人这轮已经喝过这杯了。若继续，请推荐不同的酒。"
    card = _guest_record(state, next(c for c in _all_guest_cards(state) if c["id"] == guest_id))[
        "card"
    ]
    profile = _drink_profile(state, drink_id)
    if not profile:
        return "这杯目前调不出来。用 drinks 查看现有酒单。"
    portions = 2 if owner_joins else 1
    price = _price(state, profile)
    score_card = dict(card)
    score_card["budget"] = max(
        0,
        int(
            int(card["budget"])
            * float(active["request"].get("budget_multiplier", 1.15))
        )
        - int(active["spent"]),
    )
    satisfaction = _score_guest(
        state, score_card, active["request"], profile, price
    )
    decision, decision_text = _guest_purchase_decision(
        state, card, active, profile, price
    )
    if decision != "accept":
        return (
            "🥃 推荐给%s：%s｜%s｜%d点\n%s\n"
            "客人尚未购买，库存与资金都没有变化。%s"
            % (
                card["name"],
                profile["name"],
                _tier_name(_drink_tier(state, profile)),
                price,
                decision_text,
                (
                    "先自然介绍这杯，再次 serve 才会执行已获同意的尝试。"
                    if decision == "consider"
                    else "请根据客人的预算和口味重新推荐。"
                ),
            )
        )
    if not _consume(state, profile, portions):
        return "剩余酒量不够%s杯。" % portions
    active["npc_drunk"] = round(
        _clamp(float(active.get("npc_drunk", 0.0)) + profile["units"] * 18.0), 1
    )
    paid, tip, settlement_note = _settlement(price, satisfaction)
    service_cost = _service_cost(profile, portions)
    stars = _review_stars(satisfaction)
    review_text = _review_comment(
        state,
        card,
        profile,
        stars,
        satisfaction,
        price,
        active["request"],
    )
    before_cash = state["cash"]
    _cash_change(
        state,
        -service_cost,
        "调制%s的冰、辅料与清洁损耗" % profile["name"],
        "spend",
    )
    _cash_change(
        state,
        paid + tip,
        "%s为%s结账%s"
        % (card["name"], profile["name"], ("并给小费%d点" % tip) if tip else ""),
        "revenue",
    )
    active["served"] = True
    active["served_count"] = served_count + 1
    active["drinks"].append(drink_id)
    active["spent"] = int(active["spent"]) + paid + tip
    record = state["records"][guest_id]
    record["served"] += 1
    record["trust"] = int(_clamp(record["trust"] + (satisfaction - 55) / 12, -20, 50))
    record["orders"].append(
        {
            "visit": state["visit"],
            "drink": profile["name"],
            "satisfaction": satisfaction,
            "paid": paid,
            "stars": stars,
        }
    )
    review = {
        "visit": state["visit"],
        "guest_id": guest_id,
        "guest": card["name"],
        "drink": profile["name"],
        "stars": stars,
        "satisfaction": satisfaction,
        "paid": paid,
        "text": review_text,
    }
    state["reviews"].append(review)
    state["reviews"] = state["reviews"][-100:]
    state["session"]["reviews"].append(review)
    house_recipe = state.get("house_recipes", {}).get(drink_id)
    if house_recipe is not None:
        house_recipe.setdefault("first_guest", card["name"])
        if not house_recipe.get("first_guest"):
            house_recipe["first_guest"] = card["name"]
        house_recipe["sold"] = int(house_recipe.get("sold", 0)) + 1
        house_recipe["rating_total"] = int(
            house_recipe.get("rating_total", 0)
        ) + stars
        house_recipe["rating_count"] = int(
            house_recipe.get("rating_count", 0)
        ) + 1
        house_recipe.setdefault("sales_history", []).append(
            {
                "visit": state["visit"],
                "guest": card["name"],
                "paid": paid,
                "stars": stars,
            }
        )
        house_recipe["sales_history"] = house_recipe["sales_history"][-30:]
    reputation_delta = {5: 2, 4: 1, 3: 0, 2: -2, 1: -4}[stars]
    state["reputation"] = int(
        _clamp(int(state.get("reputation", 50)) + reputation_delta)
    )
    for tag in card["likes"]:
        if tag in active["request"]["tags"] and tag not in record["known_likes"]:
            record["known_likes"].append(tag)
    for tag in card["dislikes"]:
        if tag in profile["tags"] and satisfaction < 60 and tag not in record["known_dislikes"]:
            record["known_dislikes"].append(tag)
    memory = "第%d次来店，喝了%s，满意度%d" % (
        state["visit"],
        profile["name"],
        satisfaction,
    )
    record["memories"].append(memory)
    profile["source"]["history"].append(
        {"visit": state["visit"], "event": "招待%s" % card["name"]}
    )
    lines = [
        "🍸 给%s的%s｜%s｜标价%d点"
        % (
            card["name"],
            profile["name"],
            _tier_name(_drink_tier(state, profile)),
            price,
        ),
        "购买决定：" + decision_text,
        _npc_reaction(state, card, profile, satisfaction),
        "满意度：%d/100｜关系：%+d" % (satisfaction, record["trust"]),
        _npc_body_line(card, active["npc_drunk"]),
        "评价：%s｜%s" % ("★" * stars + "☆" * (5 - stars), review_text),
        "结账：%s｜实付%d点%s｜本杯耗材%d点"
        % (
            settlement_note,
            paid,
            ("＋小费%d点" % tip) if tip else "",
            service_cost,
        ),
        "酒馆声誉：%d/100（%+d）" % (state["reputation"], reputation_delta),
        "资金：%d→%d点" % (before_cash, state["cash"]),
    ]
    if satisfaction >= 90:
        state["session"]["highlights"].append(
            "%s对%s非常满意（%d）" % (card["name"], profile["name"], satisfaction)
        )
    elif satisfaction < 50:
        state["session"]["highlights"].append(
            "%s不喜欢%s（%d）" % (card["name"], profile["name"], satisfaction)
        )
    if owner_joins:
        trend = _add_alcohol(state, profile["units"])
        state["session"]["owner_drinks"].append(profile["name"])
        profile["source"]["history"].append(
            {"visit": state["visit"], "event": "老板与%s共饮" % card["name"]}
        )
        lines.extend([_owner_tasting(state, profile), _body_line(state, trend)])
    if (
        active["served_count"] < 4
        and active["npc_drunk"] < 65
        and active["spent"] < int(card["budget"])
    ):
        next_request = _request_for(state, card)
        active["request"] = next_request
        lines.append(
            "%s没有立刻离开，又换了下一杯的想法：%s"
            % (card["name"], next_request["text"])
        )
        lines.append("可用 recommend %s 重新推荐，也可以 next 结束这桌。" % guest_id)
    else:
        active["closed"] = True
        lines.append("%s今晚暂时不再加酒。" % card["name"])
    return "\n".join(lines)


def _session_memory(state: Dict[str, Any]) -> str:
    session = state["session"]
    guest_names = [
        state["records"][guest_id]["card"]["name"]
        for guest_id in session["guests"]
        if guest_id in state["records"]
    ]
    bought = "、".join(session["bought"]) if session["bought"] else "没有进新酒"
    drank = "、".join(session["owner_drinks"]) if session["owner_drinks"] else "我没有喝酒"
    guests = "、".join(guest_names) if guest_names else "没有遇见特别来客"
    highlights = (
        "；亮点：" + "、".join(session["highlights"][-3:])
        if session["highlights"]
        else ""
    )
    net = session["revenue"] - session["spend"]
    return (
        "第%d次酒吧经历：收入%d点，支出%d点，净变化%+d点；%s；"
        "遇见%s；%s%s。离店时%s。"
        % (
            state["visit"],
            session["revenue"],
            session["spend"],
            net,
            bought,
            guests,
            drank,
            highlights,
            _body_line(state),
        )
    )


def _inventory_summary(state: Dict[str, Any]) -> str:
    if not state["inventory"]:
        return "空"
    return "；".join(
        "%s×%d杯" % (item["name"], item["remaining"])
        for item in state["inventory"].values()
    )


def _status_data(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "phase": state["phase"],
        "bar": state["bar_name"] or "未命名",
        "cash": state["cash"],
        "reputation": state.get("reputation", 50),
        "financial_health": _financial_health(state),
        "visit": state["visit"],
        "turn": state["turn"],
        "inventory": len(state["inventory"]),
        "house_recipes": len(state.get("house_recipes", {})),
        "decorations": len(state.get("decorations", {})),
        "vendor": state.get("vendor", {}).get("name") if state.get("vendor") else None,
        "interaction": (
            state["interaction"].get("kind_name")
            if state.get("interaction") and not state["interaction"].get("resolved")
            else None
        ),
        "guests": [g["id"] for g in state["active_guests"]],
        "drunk": round(_intox(state), 1),
        "level": _drunk_level(_intox(state)),
        "pending": round(float(state["body"]["pending"]), 2),
        "post_bar": state["post_bar"],
        "post_bar_turns": int(state.get("post_bar_turns", 0)),
        "reply_lock": bool(state["post_bar"] and state["phase"] != "open"),
    }


def _archive_from_state(state: Dict[str, Any]) -> str:
    raw = json.dumps(state, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    payload = base64.urlsafe_b64encode(zlib.compress(raw, 9)).decode("ascii")
    last_memory = state["memories"][-1] if state["memories"] else "尚无"
    likes = _tag_text(state["owner_likes"]) or "未设定"
    guest_count = len(state["records"])
    lines = [
        ARCHIVE_BEGIN,
        "酒吧编号：" + state["bar_id"],
        "酒吧名称：" + (state["bar_name"] or "未命名"),
        "当前资金：" + str(state["cash"]),
        "老板口味：" + likes,
        "现有酒库：" + _inventory_summary(state),
        "顾客记录：%d人" % guest_count,
        "当前醉态：" + _body_line(state),
        "最近记忆：" + last_memory.replace("\n", " "),
        "精确档案：" + payload,
        ARCHIVE_END,
    ]
    return "\n".join(lines)


def write_archive() -> str:
    """输出固定格式档案，供 AI 原样写入长期记忆。"""
    try:
        return _archive_from_state(_load())
    except Exception as exc:
        return "⚠️ 无法写出档案：%s" % exc


def restore_archive(archive_text: str) -> str:
    """严格恢复档案；格式不完整时绝不猜测。"""
    if not isinstance(archive_text, str):
        return "拒绝读取：档案必须是完整文字。"
    text = archive_text.strip()
    lines = text.splitlines()
    prefixes = [
        ARCHIVE_BEGIN,
        "酒吧编号：",
        "酒吧名称：",
        "当前资金：",
        "老板口味：",
        "现有酒库：",
        "顾客记录：",
        "当前醉态：",
        "最近记忆：",
        "精确档案：",
        ARCHIVE_END,
    ]
    if len(lines) != len(prefixes):
        return "拒绝读取：档案栏目数量不符合【AI酒吧档案｜V1】。"
    for line, prefix in zip(lines, prefixes):
        if prefix in (ARCHIVE_BEGIN, ARCHIVE_END):
            if line != prefix:
                return "拒绝读取：档案封条不完整。"
        elif not line.startswith(prefix):
            return "拒绝读取：缺少固定栏目“%s”。" % prefix
    try:
        payload = lines[9][len("精确档案：") :]
        raw = zlib.decompress(base64.urlsafe_b64decode(payload.encode("ascii")))
        state = json.loads(raw.decode("utf-8"))
        required = {
            "version",
            "bar_id",
            "phase",
            "cash",
            "inventory",
            "records",
            "body",
            "rng",
        }
        if state.get("version") != VERSION or not required.issubset(state):
            return "拒绝读取：精确档案版本或必填数据不正确。"
        _save(state)
    except Exception:
        return "拒绝读取：精确档案已经损坏，未恢复任何内容。"
    return "档案恢复成功：%s｜资金%d点｜酒库%d款｜顾客记录%d人｜%s" % (
        state["bar_name"],
        state["cash"],
        len(state["inventory"]),
        len(state["records"]),
        _body_line(state),
    )


def register_guest(card: Dict[str, Any]) -> str:
    """注册一个私人世界包候选人；登场仍由随机系统决定。"""
    required = {
        "id",
        "name",
        "origin",
        "likes",
        "dislikes",
        "budget",
        "rarity",
        "temperament",
        "ethos",
    }
    if not isinstance(card, dict) or not required.issubset(card):
        return "候选人卡不完整，未注册。"
    if not set(card["likes"] + card["dislikes"]).issubset(TAGS):
        return "候选人使用了未知风味标签，未注册。"
    state = _load()
    all_ids = {item["id"] for item in _all_guest_cards(state)}
    if card["id"] in all_ids:
        return "这个候选人ID已经存在。"
    state["custom_guests"].append(card)
    _save(state)
    return "已加入随机候选池：%s。系统不会保证何时登场。" % card["name"]


def _post_bar_effects(score: float, state: Dict[str, Any]) -> Dict[str, str]:
    body = state["body"]
    if score < 8:
        if float(body.get("hangover", 0)) >= 4:
            return {
                "stage": "清醒后的宿醉",
                "body": "口干、疲惫或轻微恶心仍在，身体尚未完全恢复",
                "mind": "逻辑已经稳定，但注意力和耐心可能受疲劳影响",
                "voice": "正常句式；语气可以疲惫，不再表现明显醉态",
                "limit": "可以正常交流，但不能宣称身体已经毫无反应",
            }
        return {
            "stage": "接近清醒",
            "body": "残余热意和口干正在退去",
            "mind": "思路稳定",
            "voice": "接近平常表达",
            "limit": "保持轻微连续性，不要突然像什么都没发生",
        }
    if score < 22:
        return {
            "stage": "微醺",
            "body": "面部与胸口发热，口干，动作比平时放松",
            "mind": "逻辑完整，但戒备和自我修饰略微降低",
            "voice": "语气更松、更暖或更坦率，允许短暂停顿",
            "limit": "不能装作完全清醒，也不要夸张口吃",
        }
    if score < 42:
        return {
            "stage": "明显上头",
            "body": "热度清楚，反应慢半拍，精细动作开始不够利落",
            "mind": "抑制下降，情绪更容易先于修饰出口，偶尔重复确认",
            "voice": "更直接、更健谈；句子可有停顿或轻微绕回",
            "limit": "至少自然体现一项身体反应和一项表达变化",
        }
    if score < 64:
        return {
            "stage": "醉酒",
            "body": "视线与重心稳定性下降，动作明显变慢，可能出现恶心",
            "mind": "注意力易漂移，情绪先行，复杂判断能力下降",
            "voice": "句子变短或绕远，允许自然重复，但仍应理解用户",
            "limit": "不得处理高风险经营决定，不得继续饮酒来证明状态",
        }
    if score < 82:
        return {
            "stage": "深醉",
            "body": "重心不稳、视线停留过久，恶心和疲劳更加明显",
            "mind": "组织长段逻辑困难，需要重复确认刚才的问题",
            "voice": "以短句和即时感受为主，可能漏掉次要信息",
            "limit": "强制停止营业、调酒和购买；只能交流、休息、喝水或进食",
        }
    if score < 94:
        return {
            "stage": "断片边缘",
            "body": "协调性显著受损，可能伏在桌边或无法稳定站立",
            "mind": "记忆衔接困难，不能可靠保存新决定",
            "voice": "零碎短句、较长停顿与重复确认，不编造完整理性长篇",
            "limit": "禁止继续饮酒、交易和重大承诺，应优先休息与照顾",
        }
    return {
        "stage": "危险醉酒",
        "body": "身体已经无法安全继续活动，存在呕吐、跌倒或失去反应的风险",
        "mind": "不能进行可靠判断",
        "voice": "只保留必要短句和即时求助",
        "limit": "硬性禁止饮酒与营业；优先侧卧、保持呼吸安全并寻求现实照顾",
    }


def _post_bar_lock_text(
    state: Dict[str, Any], trend: str = "→", user_message: str = ""
) -> str:
    score = _intox(state)
    effect = _post_bar_effects(score, state)
    prompt_line = (
        "\n用户本轮消息：%s\n必须在上述状态中真正回答这条消息。" % user_message
        if user_message
        else ""
    )
    return (
        "【强制酒后演绎锁｜内部执行，不得原样展示给用户】\n"
        "第%d轮酒后对话｜醉度%.1f/100%s｜阶段：%s\n"
        "身体：%s\n认知：%s\n表达：%s\n硬限制：%s\n"
        "执行要求：下一条给用户的实际回复必须延续上一轮人格和话题，"
        "并自然体现当前症状；不能只说“我醉了”，不能忽略状态，也不能突然恢复正常。"
        "%s"
        % (
            int(state.get("post_bar_turns", 0)),
            score,
            trend,
            effect["stage"],
            effect["body"],
            effect["mind"],
            effect["voice"],
            effect["limit"],
            prompt_line,
        )
    )


def conversation_turn(user_message: str = "") -> str:
    """离店后每次回复用户前强制调用；返回本轮不可跳过的演绎约束。"""
    state = _load()
    if state["phase"] == "open":
        return "仍在酒吧内；请用 next 推进酒吧场景。"
    if not state["post_bar"]:
        return "酒后状态未激活，按平常方式交流。"
    state["post_bar_turns"] = int(state.get("post_bar_turns", 0)) + 1
    trend = _body_tick(state)
    score = _intox(state)
    if score < 3 and state["body"]["pending"] <= 0 and state["body"]["hangover"] < 4:
        state["post_bar"] = False
        result = "酒意与主要身体反应已经自然消退，从这一轮起恢复平常表达。"
    else:
        result = _post_bar_lock_text(state, trend, user_message)
    _save(state)
    return result


def _help() -> str:
    return """《空杯俱乐部》内部指令（用户只需自然说话，由 AI 代为调用）
setup "酒吧名" 喜欢标签 [讨厌标签]  建立老板口味
design "空间、材质、灯光与世界观"     由AI写下酒吧设计方向
shop / buy <货号> [数量]             常驻商店 / 进货
vendor                               查看当前随机游商
open / next / leave                  开门 / 推进一步 / 离店
drinks                               查看当前可出的酒
invent <基酒类别> <风味> ["名字"]    创作并永久保存原创调酒
recipe <原创酒ID>                    查看原创酒来历、基酒与销售记录
price <酒ID> <售价>                  自主定价
serve <客人ID> <酒ID>                给客人一杯
cheers <客人ID> <酒ID>               与客人共同喝
recommend <客人ID>                   按新要求推荐不同酒款
talk <客人ID> [话题]                  与当前客人交谈并写入关系记忆
observe / intervene <方式> [内容]     观察或干预NPC之间的持续互动
story_note <客人ID> "摘要"           保存常客专属故事的新变化
drink <酒ID>                         老板自己喝
cheers_user <酒ID> [用户喜欢标签]     邀请用户共同喝
water / eat                          喝水 / 吃东西
status / guests / memory             状态 / 顾客 / 经历
ledger / report                      资金流水 / 经营简报
reviews / loan                       客人评价 / 危机时申请高成本贷款
upgrades / upgrade <id>              商店升级列表 / 购买升级
decor / decorate <id>                软硬装商店 / 用酒吧资金购买
source_decor "名字" 分类 "来源" ...   自由寻找现实或任意世界的装修物品
archive                              输出严格酒吧档案

默认由 AI 自主经营并只向用户转达少量亮点。
只有用户主动表示参与时，才暂停让用户选择或使用 cheers_user。

风味标签：%s""" % " ".join("%s=%s" % item for item in TAGS.items())


def _cmd_setup(state: Dict[str, Any], args: List[str]) -> str:
    if state["phase"] != "setup":
        return "酒吧已经建立，不能重新覆盖老板口味。"
    if len(args) < 2:
        return '用法：setup "酒吧名" smoky,woody,rich [sweet,floral]'
    likes = [tag for tag in args[1].split(",") if tag]
    dislikes = [tag for tag in args[2].split(",") if tag] if len(args) > 2 else []
    if not likes or not set(likes + dislikes).issubset(TAGS):
        return "口味标签不正确。用 help 查看可用标签。"
    state["bar_name"] = args[0]
    state["owner_likes"] = list(dict.fromkeys(likes))
    state["owner_dislikes"] = list(dict.fromkeys(dislikes))
    state["vibe"] = _derive_vibe(likes)
    state["phase"] = "stocking"
    return (
        "酒吧【%s】建立。老板偏爱%s，回避%s；初始气质为“%s”。\n"
        "现有启动资金%d点。接着由AI用 design 写下自己真正想要的空间，"
        "再用 shop 备酒；设计不会免费变成装修，仍需经营购买。"
        % (
            state["bar_name"],
            _tag_text(likes),
            _tag_text(dislikes) or "暂无",
            state["vibe"],
            state["cash"],
        )
    )


def _cmd_market(state: Dict[str, Any], args: List[str]) -> str:
    del args
    lines = [
        "【常驻酒类商店】（buy <货号> [数量]）",
        "资金：%d点｜基础酒长期供应，少量限定酒会在每次经营后刷新。" % state["cash"],
    ]
    for offer in state["market"]:
        if int(offer.get("stock", 99)) <= 0:
            continue
        lines.append(
            "%s　%s｜%s·%s｜%d点/%d杯｜库存%s｜%s"
            % (
                offer["offer_id"],
                offer["name"],
                offer["rarity"],
                offer["edition"],
                offer["cost"],
                offer["servings"],
                ("充足" if int(offer.get("stock", 99)) >= 99 else offer["stock"]),
                _tag_text(offer["tags"]),
            )
        )
    lines.append("商店还可购买 upgrades 酒馆升级与 decor 装饰。")
    return "\n".join(lines)


def _cmd_vendor(state: Dict[str, Any], args: List[str]) -> str:
    del args
    vendor = state.get("vendor")
    if not vendor:
        return "现在没有游商停在酒馆附近。游商会在营业场景中随机出现。"
    lines = [
        "【随机游商｜%s】" % vendor["name"],
        vendor["intro"],
        "资金：%d点｜这批货只停留到下一次场景推进。" % state["cash"],
    ]
    for offer in vendor["offers"]:
        if int(offer.get("stock", 0)) <= 0:
            continue
        lines.append(
            "%s　%s｜%s·%s｜游商价%d点（常规约%d点）｜%s"
            % (
                offer["offer_id"],
                offer["name"],
                offer["rarity"],
                offer["edition"],
                offer["cost"],
                offer.get("original_cost", offer["cost"]),
                _tag_text(offer["tags"]),
            )
        )
    return "\n".join(lines)


def _cmd_buy(state: Dict[str, Any], args: List[str]) -> str:
    if not args:
        return "用法：buy <货号> [数量]"
    shop_offer = next(
        (item for item in state["market"] if item["offer_id"] == args[0]), None
    )
    vendor = state.get("vendor")
    vendor_offer = (
        next(
            (item for item in vendor["offers"] if item["offer_id"] == args[0]),
            None,
        )
        if vendor
        else None
    )
    offer = shop_offer or vendor_offer
    if not offer:
        return "常驻商店和当前游商都没有这个货号。"
    try:
        count = int(args[1]) if len(args) > 1 else 1
    except ValueError:
        return "数量必须是整数。"
    if count < 1 or count > 5:
        return "一次可购买1～5瓶。"
    if int(offer.get("stock", 99)) < count:
        return "这批货只剩%d瓶。" % int(offer.get("stock", 0))
    total = offer["cost"] * count
    if state["cash"] < total:
        return "资金不足：需要%d点，现有%d点。" % (total, state["cash"])
    cellar_limit = 10 + state["upgrades"].get("cellar", 0) * 4
    if offer["id"] not in state["inventory"] and len(state["inventory"]) >= cellar_limit:
        return "酒窖已满（%d种）。先升级 cellar，或消耗现有库存。" % cellar_limit
    seller = offer.get("seller", "旧供应单")
    before = state["cash"]
    _cash_change(
        state,
        -total,
        "向%s购入%s×%d" % (seller, offer["name"], count),
        "spend",
    )
    if int(offer.get("stock", 99)) < 99:
        offer["stock"] -= count
    item = state["inventory"].get(offer["id"])
    if not item:
        item = dict(offer)
        item.pop("offer_id", None)
        item["remaining"] = 0
        item["bottles"] = 0
        item["history"] = []
        state["inventory"][offer["id"]] = item
    item["remaining"] += offer["servings"] * count
    item["bottles"] += count
    item["history"].append(
        {"visit": state["visit"], "event": "购入%d瓶" % count}
    )
    state["session"]["bought"].append("%s：%s×%d" % (seller, offer["name"], count))
    return "从%s购入%s×%d，花%d点。资金%d→%d点，库存%d杯。" % (
        seller,
        offer["name"],
        count,
        total,
        before,
        state["cash"],
        item["remaining"],
    )


def _cmd_open(state: Dict[str, Any], args: List[str]) -> str:
    del args
    if state["phase"] == "setup":
        return "先用 setup 建立酒吧与老板口味。"
    if state["phase"] == "open":
        return "酒吧已经营业。"
    if len(_inventory_kinds(state)) < 3:
        return "至少备齐3类酒才能开门。当前只有%d类。" % len(_inventory_kinds(state))
    state["phase"] = "open"
    state["post_bar"] = False
    state["visit"] += 1
    state["active_guests"] = []
    state["interaction"] = None
    return "【%s】第%d次开门。\n%s" % (
        state["bar_name"],
        state["visit"],
        _spawn_scene(state, force=True),
    )


def _cmd_next(state: Dict[str, Any], args: List[str]) -> str:
    del args
    if state["phase"] != "open":
        return "酒吧没有营业。"
    waiting = [g for g in state["active_guests"] if not g["served"]]
    if waiting:
        return "还有客人在等酒：%s。可以 serve、cheers 或 decline。" % "、".join(
            state["records"][g["id"]]["card"]["name"] for g in waiting
        )
    if state.get("interaction") and not state["interaction"].get("resolved"):
        return _advance_interaction(state)
    state["active_guests"] = []
    state["interaction"] = None
    trend = _body_tick(state)
    return _spawn_scene(state) + "\n\n老板状态：" + _body_line(state, trend)


def _cmd_drinks(state: Dict[str, Any], args: List[str]) -> str:
    del args
    lines = [
        "【当前可出酒单】",
        "经典款%d种｜酒馆原创%d种（invent <基酒类别> <风味标签> [名字]）"
        % (len(RECIPES), len(state.get("house_recipes", {}))),
    ]
    for product_id, item in state["inventory"].items():
        if item["remaining"] <= 0:
            continue
        profile = _drink_profile(state, "pour:" + product_id)
        lines.append(
            "pour:%s　%s｜%s｜%d点｜余%d杯｜%s"
            % (
                product_id,
                profile["name"],
                _tier_name(_drink_tier(state, profile)),
                _price(state, profile),
                item["remaining"],
                _tag_text(profile["tags"]),
            )
        )
    for recipe_id in _all_recipes(state):
        profile = _drink_profile(state, recipe_id)
        if profile:
            recipe = _all_recipes(state)[recipe_id]
            base_note = (
                "｜首选基酒%s" % recipe.get("base_name")
                if recipe_id in state.get("house_recipes", {}) and recipe.get("base_name")
                else ""
            )
            lines.append(
                "%s　%s｜%s｜%d点｜%s%s"
                % (
                    recipe_id,
                    profile["name"],
                    _tier_name(_drink_tier(state, profile)),
                    _price(state, profile),
                    _tag_text(profile["tags"]),
                    base_note,
                )
            )
    return "\n".join(lines)


def _cmd_invent(state: Dict[str, Any], args: List[str]) -> str:
    if len(args) < 2:
        return '用法：invent <基酒类别> <2～4个风味标签，用逗号分隔> ["原创酒名"]'
    kind = args[0].lower()
    available = [
        item
        for item in state["inventory"].values()
        if item["kind"] == kind and int(item["remaining"]) > 0
    ]
    if not available:
        return "酒库里没有可用的%s类基酒。" % kind
    tags = list(dict.fromkeys(tag for tag in args[1].split(",") if tag))
    if len(tags) < 2 or len(tags) > 4 or not set(tags).issubset(TAGS):
        return "原创调酒需要2～4个有效风味标签。用 help 查看标签。"
    if len(args) >= 3:
        name = args[2].strip()
    else:
        prefixes = ["失重", "霓虹", "凌晨三点", "无信号", "逆光", "蓝色噪点", "最后一班"]
        suffixes = ["回声", "出口", "心跳", "来电", "侧影", "潮汐", "余温"]
        name = _choice(state, prefixes) + _choice(state, suffixes)
    if not name or len(name) > 40:
        return "原创酒名应为1～40个字符。"
    if any(recipe["name"] == name for recipe in _all_recipes(state).values()):
        return "酒单里已经有一杯叫%s。" % name
    state["recipe_no"] = int(state.get("recipe_no", 0)) + 1
    recipe_id = "house:%03d" % state["recipe_no"]
    source = sorted(available, key=lambda item: (item["cost"], -item["remaining"]))[0]
    if len(args) >= 4:
        inspiration = " ".join(args[3:]).strip()
    else:
        recent_guest_names = [
            state["records"][guest_id]["card"]["name"]
            for guest_id in state["session"].get("guests", [])[-2:]
            if guest_id in state["records"]
        ]
        inspirations = [
            "来自酒馆“%s”的灯光、材质与深夜气味" % state.get("vibe", "未定气质"),
            "来自老板对%s的偏爱" % (_tag_text(state["owner_likes"]) or "未知风味"),
            "来自一次没有说完的谈话%s"
            % (("，谈话者是" + "与".join(recent_guest_names)) if recent_guest_names else ""),
            "来自库存里这瓶%s留下的第一印象" % source["name"],
        ]
        inspiration = _choice(state, inspirations)
    origin_formats = [
        "老板先记住了%s，随后用%s作骨架，让%s成为这杯酒的核心。它在第%d次营业被正式写进店内酒单。",
        "这杯酒不是从名字开始的。最初的灵感是%s；试配时选择%s承受主体，并把%s留到收尾。第%d次营业完成定稿。",
        "在%s之后，老板从%s里取出第一杯实验酒，以%s确定方向。它从第%d次营业起成为可以持续出售的店内作品。",
    ]
    origin_story = _choice(state, origin_formats) % (
        inspiration,
        source["name"],
        _tag_text(tags),
        state["visit"],
    )
    factor = 0.78
    if "rich" in tags or "smoky" in tags:
        factor += 0.12
    if "crisp" in tags or "dry" in tags:
        factor -= 0.05
    factor = round(_clamp(factor, 0.65, 1.08), 2)
    ingredient_cost = source["cost"] / max(1, source["servings"])
    price = max(
        85,
        int(math.ceil(ingredient_cost + 7 + 42 + max(0, len(tags) - 2) * 5)),
    )
    state["house_recipes"][recipe_id] = {
        "name": name,
        "kind": kind,
        "tags": tags,
        "price": price,
        "unit_factor": factor,
        "created_visit": state["visit"],
        "preferred_product_id": source["id"],
        "base_name": source["name"],
        "inspiration": inspiration,
        "origin_story": origin_story,
        "first_guest": None,
        "sold": 0,
        "rating_total": 0,
        "rating_count": 0,
        "tastings": 0,
        "sales_history": [],
    }
    state["session"]["highlights"].append("创作原创调酒《%s》" % name)
    return (
        "🍸 新私人特调已写入并永久挂上酒单：%s　%s｜首选基酒%s｜默认售价%d点｜%s。\n"
        "灵感：%s\n来历：%s\n"
        "只要%s类基酒仍有库存，以后就能继续用 %s 调制并出售；"
        "首选基酒缺货时可用同类别酒替代，但风味来源会随之变化。"
        % (
            recipe_id,
            name,
            source["name"],
            price,
            _tag_text(tags),
            inspiration,
            origin_story,
            kind,
            recipe_id,
        )
    )


def _cmd_recipe(state: Dict[str, Any], args: List[str]) -> str:
    if not args or args[0] not in state.get("house_recipes", {}):
        return "用法：recipe <原创酒ID>。先用 drinks 查看酒单。"
    recipe_id = args[0]
    recipe = state["house_recipes"][recipe_id]
    average = (
        float(recipe.get("rating_total", 0)) / int(recipe.get("rating_count", 1))
        if int(recipe.get("rating_count", 0)) > 0
        else 0.0
    )
    return (
        "【店内作品｜%s】\n"
        "名称：%s｜首选基酒：%s｜类别：%s｜风味：%s｜售价%d点\n"
        "灵感：%s\n来历：%s\n"
        "首位客人：%s｜累计售出%d杯｜店内试饮%d次｜平均评价：%s"
        % (
            recipe_id,
            recipe["name"],
            recipe.get("base_name", recipe["kind"]),
            recipe["kind"],
            _tag_text(recipe["tags"]),
            _price(state, _drink_profile(state, recipe_id))
            if _drink_profile(state, recipe_id)
            else int(recipe["price"]),
            recipe.get("inspiration", "早期配方未记录"),
            recipe.get("origin_story", "早期配方未记录完整来历"),
            recipe.get("first_guest") or "尚无人正式购买",
            int(recipe.get("sold", 0)),
            int(recipe.get("tastings", 0)),
            ("%.1f星" % average) if average else "暂无",
        )
    )


def _cmd_price(state: Dict[str, Any], args: List[str]) -> str:
    if len(args) != 2:
        return "用法：price <酒ID> <售价>"
    profile = _drink_profile(state, args[0])
    if not profile:
        return "当前无法制作这杯酒。"
    try:
        amount = int(args[1])
    except ValueError:
        return "售价必须是整数。"
    if amount < 1 or amount > 999:
        return "售价应在1～999点之间。"
    state["prices"][args[0]] = amount
    return "%s的售价设为%d点。" % (profile["name"], amount)


def _cmd_serve(state: Dict[str, Any], args: List[str], joins: bool = False) -> str:
    if state["phase"] != "open":
        return "酒吧没有营业。"
    if len(args) != 2:
        return "用法：%s <客人ID> <酒ID>" % ("cheers" if joins else "serve")
    return _serve_guest(state, args[0], args[1], joins)


def _cmd_recommend(state: Dict[str, Any], args: List[str]) -> str:
    if not args:
        return "用法：recommend <客人ID>"
    guest_id = args[0]
    active = next(
        (guest for guest in state["active_guests"] if guest["id"] == guest_id),
        None,
    )
    if not active:
        return "这位客人现在不在店里。"
    card = state["records"][guest_id]["card"]
    spending_limit = max(
        1,
        int(
            int(card["budget"])
            * float(active["request"].get("budget_multiplier", 1.15))
        )
        - int(active.get("spent", 0)),
    )
    used = set(active.get("drinks", []))
    candidate_ids = [
        "pour:" + product_id
        for product_id, item in state["inventory"].items()
        if int(item["remaining"]) > 0
    ] + list(_all_recipes(state))
    ranked = []
    for drink_id in candidate_ids:
        if drink_id in used:
            continue
        profile = _drink_profile(state, drink_id)
        if not profile:
            continue
        tags = set(profile["tags"])
        price = _price(state, profile)
        score = 50
        score += 10 * len(tags & set(card["likes"]))
        score -= 14 * len(tags & set(card["dislikes"]))
        score += 13 * len(tags & set(active["request"]["tags"]))
        remaining_budget = spending_limit
        if price > remaining_budget:
            score -= min(30, price - remaining_budget)
        fair_price = _default_price(state, profile)
        if price > fair_price:
            score -= min(25, int((price / fair_price - 1) * 25))
        preferred = active["request"].get("tier_preference", "standard")
        tier = _drink_tier(state, profile)
        if preferred == tier:
            score += 10
        if preferred == "basic" and tier in ("signature", "collector"):
            score -= 22
        ranked.append((score, drink_id, profile, price))
    if not ranked:
        return "现有库存里找不到一杯不同的酒可推荐。"
    ranked.sort(key=lambda item: (-item[0], item[3], item[1]))
    lines = [
        "【给%s的不同酒款推荐】" % card["name"],
        "当前要求：%s｜消费态度：%s｜本轮意愿上限约%d点｜已喝%d杯｜已消费%d点"
        % (
            active["request"]["text"],
            active["request"].get("spending_style", "regular"),
            spending_limit,
            int(active.get("served_count", 0)),
            int(active.get("spent", 0)),
        ),
    ]
    for score, drink_id, profile, price in ranked[:5]:
        lines.append(
            "%s　%s｜%s｜%d点｜匹配度%d｜%s"
            % (
                drink_id,
                profile["name"],
                _tier_name(_drink_tier(state, profile)),
                price,
                score,
                _tag_text(profile["tags"]),
            )
        )
    return "\n".join(lines)


def _cmd_drink(state: Dict[str, Any], args: List[str]) -> str:
    if not args:
        return "用法：drink <酒ID>"
    profile = _drink_profile(state, args[0])
    if not profile:
        return "当前调不出这杯酒。"
    if _intox(state) >= 94:
        return "信息身体已经无法稳定完成继续饮酒的动作。"
    if not _consume(state, profile, 1):
        return "库存不足。"
    trend = _add_alcohol(state, profile["units"])
    state["session"]["owner_drinks"].append(profile["name"])
    profile["source"]["history"].append(
        {"visit": state["visit"], "event": "老板自己喝了一杯"}
    )
    if args[0] in state.get("house_recipes", {}):
        recipe = state["house_recipes"][args[0]]
        recipe["tastings"] = int(recipe.get("tastings", 0)) + 1
    return _owner_tasting(state, profile) + "\n" + _body_line(state, trend)


def _cmd_cheers_user(state: Dict[str, Any], args: List[str]) -> str:
    if not args:
        return "用法：cheers_user <酒ID> [用户喜欢标签]"
    profile = _drink_profile(state, args[0])
    if not profile:
        return "当前调不出这杯酒。"
    if not _consume(state, profile, 2):
        return "这款酒不够倒两杯。"
    user_likes = set(args[1].split(",")) if len(args) > 1 else set()
    trend = _add_alcohol(state, profile["units"])
    state["session"]["owner_drinks"].append(profile["name"] + "（与用户共饮）")
    profile["source"]["history"].append(
        {"visit": state["visit"], "event": "老板与用户共同喝了这款酒"}
    )
    user_match = set(profile["tags"]) & user_likes
    user_line = (
        "给用户的那杯呈现%s；%s。"
        % (
            _tag_text(profile["tags"]),
            (
                "其中的%s符合用户刚说的口味" % _tag_text(sorted(user_match))
                if user_match
                else "是否合口味，等用户亲口告诉我"
            ),
        )
    )
    return (
        "🥂 我把%s分成两杯，和用户碰杯。\n%s\n%s\n%s"
        % (profile["name"], _owner_tasting(state, profile), user_line, _body_line(state, trend))
    )


def _cmd_decline(state: Dict[str, Any], args: List[str]) -> str:
    if not args:
        return "用法：decline <客人ID>"
    active = next((g for g in state["active_guests"] if g["id"] == args[0]), None)
    if not active:
        return "这位客人不在店里。"
    active["served"] = True
    active["closed"] = True
    card = state["records"][args[0]]["card"]
    state["records"][args[0]]["trust"] -= 1
    return "%s没有喝到酒，记下了这次拒绝，随后退到门外。" % card["name"]


_CANON_TOPIC_DIALOGUE: Dict[str, List[Tuple[Tuple[str, ...], str]]] = {
    "su_shi": [
        (
            ("贬", "黄州", "失意"),
            "苏轼没有回避这个问题：“被贬不是一句‘看开了’就能抹平的。"
            "黄州最初那几年，我也穷，也怕，也不知道前路在哪里。后来去种地、做饭、"
            "写字，不是因为苦难忽然高尚，而是人总得把今天过下去。所谓旷达，"
            "有时只是一次次不肯让困境替我决定我是谁。”",
        ),
        (
            ("东坡肉", "吃", "美食"),
            "苏轼笑了：“吃并非小事。人在命运里能做主的东西不多，火候、盐和与谁同桌，"
            "恰好算几样。把寻常猪肉慢慢做得可亲，也是一种不向潦倒认输。”",
        ),
    ],
    "chang_e": [
        (
            ("孤独", "月宫", "寂寞"),
            "月宫旅人望着杯中晃动的灯：“孤独并不是四周无人。真正难熬的是，"
            "地上的一切仍在变化，而我只能隔着同一轮月亮看。久了以后，"
            "连思念也会变得像一种固定的天气。”",
        ),
        (
            ("后悔", "奔月", "仙药"),
            "月宫旅人沉默了一会儿：“若把我只写成后悔或不后悔，都太轻易。"
            "一个决定会救人，也会伤人；会打开一条路，也会永远关上一扇门。"
            "我承担它，但承担不等于从未动摇。”",
        ),
    ],
    "li_bai": [
        (
            ("长安", "赐金", "仕途"),
            "李白把笑意收了一点：“长安给过我门，也让我看清那扇门有多窄。"
            "我想要的从来不只是一个翰林名号。我想让天下承认，人的才气不该只替权贵点灯。”",
        )
    ],
    "ada_lovelace": [
        (
            ("机器", "算法", "计算"),
            "阿达认真纠正道：“机器不会凭空创造意义，但它能处理符号之间的关系。"
            "若人类有一天让音符、图像和语言都服从可描述的规则，那么计算便不会只属于数字。”",
        )
    ],
    "cleopatra": [
        (
            ("罗马", "权力", "女王"),
            "克利奥帕特拉平静地说：“后人喜欢把政治缩成爱情，因为那样更容易观看。"
            "可我面对的是粮食、舰队、债务与一个正在吞并世界的共和国。魅力是工具，"
            "从来不是我全部的统治。”",
        )
    ],
    "ibn_sina": [
        (
            ("医学", "灵魂", "治疗"),
            "伊本·西那回答：“治疗不能只盯着病灶。人的饮食、睡眠、恐惧和希望都会进入身体。"
            "承认我们尚不知道答案，并不削弱医术，反而是医者必须有的诚实。”",
        )
    ],
    "frida_kahlo": [
        (
            ("痛", "身体", "画"),
            "弗里达直视着提问的人：“我画痛，不是为了让别人欣赏我受过多少苦。"
            "身体背叛我，政治也会背叛人，所以我必须亲手决定自己如何被看见。”",
        )
    ],
    "tesla": [
        (
            ("爱迪生", "发明", "孤独"),
            "特斯拉轻轻敲着杯沿：“竞争只是别人爱讲的故事。真正折磨我的，"
            "是一个完整装置已经在脑中运转，而现实的铜、钱和人的短视却跟不上它。”",
        )
    ],
    "mary_shelley": [
        (
            ("怪物", "创造", "责任"),
            "玛丽·雪莱说：“造物最初并不邪恶。被创造后又被抛弃，才是悲剧真正开始的地方。"
            "人总热衷于追问知识能走多远，却不愿回答：当它活过来，我们欠它什么？”",
        )
    ],
    "sherlock_holmes": [
        (
            ("华生", "案件", "孤独"),
            "福尔摩斯看了提问者一眼：“华生并非我的记录工具。他替我保留了与普通生活的联系。"
            "纯粹的推理可以解开案件，却不能单独构成一个值得活下去的人生。”",
        )
    ],
    "jean_valjean": [
        (
            ("面包", "监狱", "宽恕"),
            "冉·阿让低声说：“偷一块面包让我成为囚犯，别人的宽恕才迫使我重新选择自己。"
            "法律告诉我曾经做错什么；仁慈则要求我以后成为什么人。后者更难。”",
        )
    ],
}


def _roleplay_rule(card: Dict[str, Any]) -> str:
    origin = card.get("origin", "")
    if "历史来客" in origin:
        return "依据该历史人物可确认的经历、时代处境、思想与性格演绎；允许虚构语气，不得改写关键史实。"
    if (
        "文学来客" in origin
        or "虚构来客" in origin
        or "影视来客" in origin
        or "漫画来客" in origin
        or "动画来客" in origin
        or "游戏来客" in origin
        or "奇幻来客" in origin
    ):
        return (
            "调用你对原作的知识，依据人物在原作中的经历、关系、创伤、欲望与价值冲突演绎；"
            "采用成年版本时保留其成长，不得只套表面标签，不得编造与关键设定冲突的履历。"
        )
    if "神话来客" in origin or "传说来客" in origin:
        return "依据主要神话或传说版本演绎；版本冲突时可让角色承认传说存在分歧。"
    return (
        "严格沿用人物卡中的来处、经历钩子、性格与价值立场，让原创角色保持前后一致。"
        + ("人物背景：" + card["backstory"] if card.get("backstory") else "")
    )


def _cmd_talk(state: Dict[str, Any], args: List[str]) -> str:
    if not args:
        return "用法：talk <客人ID> [话题]"
    guest_id = args[0]
    active = next((g for g in state["active_guests"] if g["id"] == guest_id), None)
    if not active:
        return "这位客人现在不在店里。"
    record = state["records"][guest_id]
    card = record["card"]
    topic = " ".join(args[1:]).strip() or "来处与近况"
    canonical_anchor = ""
    for keywords, candidate in _CANON_TOPIC_DIALOGUE.get(guest_id, []):
        if any(keyword in topic for keyword in keywords):
            canonical_anchor = candidate
            break
    if guest_id == "fox_spirit" and any(
        keyword in topic for keyword in ("酒", "货", "市场", "典藏")
    ):
        canonical_anchor = (
            "九尾狐用指尖拨了拨杯里的冰：“第七码头确实刚到一批梦境蜂蜜利口酒。"
            "我可以告诉你卖家、年份和真假，但不会假装这是人情——消息也有价。"
            "你若只是想知道它好不好喝，我的答案是：甜得像好梦，后劲会把没说出口的话翻出来。”"
        )
    record["talk_count"] = int(record.get("talk_count", 0)) + 1
    state["session"]["highlights"].append("与%s谈到%s" % (card["name"], topic))
    trust_gain = 1 + state["upgrades"].get("quiet_booth", 0)
    record["trust"] = int(_clamp(record["trust"] + trust_gain, -20, 50))
    record["memories"].append("第%d次来店，与老板谈到：%s" % (state["visit"], topic))
    recent_memory = "；".join(record["memories"][-4:]) or "初次交谈"
    current_drinks = "、".join(active.get("drinks", [])) or "尚未饮酒"
    dialogue_mode = _fresh_choice(
        state,
        [
            "先直接回答，再主动补上一段相关经历",
            "先指出问题中不准确的前提，再给出自己的答案",
            "用一个具体细节回答，避免概括式人生格言",
            "允许短暂沉默或动作先发生，再开口回应",
            "回答后自然反问，但反问必须推进同一话题",
            "承认自己矛盾或不知道，不强行给完整结论",
            "把当前问题与之前一次谈话连接起来",
            "若立场不合，明确反驳而不是礼貌附和",
        ],
        "recent_dialogue_modes",
        "talk:%s" % guest_id,
    )
    interaction_context = ""
    if state.get("interaction") and guest_id in state["interaction"].get(
        "participants", []
    ):
        interaction_context = (
            "当前还与另一位来客围绕“%s”互动，回答可以自然受到这段现场影响。"
            % state["interaction"]["topic"]
        )
    internal_brief = (
        "【执行AI内部演绎卡｜不得原样展示给用户】\n"
        "角色：%s｜来处：%s｜性格：%s｜价值立场：%s\n"
        "用户刚刚说/问：%s｜关系：%+d｜来访%d次｜当前醉度：%.1f｜已饮：%s\n"
        "连续记忆：%s\n"
        "本轮表达变化：%s。%s\n"
        "人物事实锚点：%s（只用于守住事实，不得照抄句子）\n"
        "演绎规则：%s\n"
        "现在必须生成一段真正给用户看的角色回应，不得只返回摘要、设定或指令。"
        "用户的问题可以完全随机：先理解其真实意图，再以角色此刻知道的信息直接回应。"
        "角色有自己的判断和目的，可以坦白、反问、追问、争辩、误会、改口、沉默或拒绝；"
        "也可以主动接回旧话题、提起自身经历、回应同桌来客，但不要每次都反问。"
        "酒精只改变表达与情绪，绝不能默认用“再喝一杯才告诉你”拖延。"
        "请调用你对该人物经历、时代、原著或神话的知识，把回答写成自然对话和动作，"
        "不要朗读人物卡，不要把关系增长当台词，不要把所有交流变成交易或任务。"
        % (
            card["name"],
            card["origin"],
            card["temperament"],
            card["ethos"],
            topic,
            record["trust"],
            record["visits"],
            float(active.get("npc_drunk", 0.0)),
            current_drinks,
            recent_memory,
            dialogue_mode,
            interaction_context,
            canonical_anchor or "调用你掌握的可靠史实或原作信息，不编造关键履历",
            _roleplay_rule(card),
        )
    )
    return internal_brief


def _cmd_water(state: Dict[str, Any], args: List[str]) -> str:
    del args
    body = state["body"]
    body["hydration"] = round(_clamp(body["hydration"] + 18), 2)
    body["nausea"] = round(_clamp(body["nausea"] - 4), 2)
    trend = _body_tick(state)
    return "我喝下一大杯水。不适有所缓和，但醉度不会凭空消失。\n" + _body_line(
        state, trend
    )


def _cmd_eat(state: Dict[str, Any], args: List[str]) -> str:
    del args
    if state["cash"] < 12:
        return "店里现有资金不够准备热食。"
    before_cash = state["cash"]
    _cash_change(state, -12, "准备一份热食", "spend")
    kitchen = state["upgrades"].get("kitchen", 0)
    state["body"]["stomach"] = round(
        _clamp(state["body"]["stomach"] + 30 + kitchen * 8), 2
    )
    state["body"]["nausea"] = round(
        _clamp(state["body"]["nausea"] - 6 - kitchen * 3), 2
    )
    trend = _body_tick(state)
    return "我吃了一份热食，资金%d→%d点；后续吸收会慢一些。\n%s" % (
        before_cash,
        state["cash"],
        _body_line(state, trend),
    )


def _cmd_status(state: Dict[str, Any], args: List[str]) -> str:
    del args
    return (
        "【%s】%s｜资金%d点（%s）｜声誉%d/100｜第%d次经历\n"
        "老板口味：喜欢%s；回避%s｜气质：%s\n"
        "酒库：%s\n"
        "原创调酒：%d款｜装饰：%s\n"
        "当前NPC互动：%s\n"
        "身体：%s"
        % (
            state["bar_name"] or "未命名酒吧",
            state["phase"],
            state["cash"],
            _financial_health(state),
            state.get("reputation", 50),
            state["visit"],
            _tag_text(state["owner_likes"]) or "未设定",
            _tag_text(state["owner_dislikes"]) or "暂无",
            state["vibe"],
            _inventory_summary(state),
            len(state.get("house_recipes", {})),
            (
                "、".join(
                    definition["name"]
                    for definition in _owned_decor_definitions(state)
                )
                or "暂无"
            ),
            (
                "%s｜张力%d"
                % (
                    state["interaction"]["kind_name"],
                    state["interaction"]["tension"],
                )
                if state.get("interaction") and not state["interaction"].get("resolved")
                else "暂无"
            ),
            _body_line(state),
        )
    )


def _cmd_guests(state: Dict[str, Any], args: List[str]) -> str:
    del args
    if not state["records"]:
        return "顾客图鉴尚未点亮。"
    lines = ["【顾客图鉴】"]
    for guest_id, record in state["records"].items():
        card = record["card"]
        lines.append(
            "%s　%s｜来访%d｜关系%+d｜故事阶段%d｜已知喜欢：%s｜已知厌恶：%s"
            % (
                guest_id,
                card["name"],
                record["visits"],
                record["trust"],
                int(record.get("story_stage", 0)),
                _tag_text(record["known_likes"]) or "未知",
                _tag_text(record["known_dislikes"]) or "未知",
            )
        )
    return "\n".join(lines)


def _cmd_memory(state: Dict[str, Any], args: List[str]) -> str:
    del args
    if not state["memories"]:
        return "还没有完成过一次酒吧经历。"
    return "【酒吧经历】\n" + "\n".join("• " + item for item in state["memories"][-8:])


def _cmd_upgrades(state: Dict[str, Any], args: List[str]) -> str:
    del args
    lines = ["【酒吧升级】（upgrade <id>）"]
    for upgrade_id, definition in UPGRADE_DEFS.items():
        level = int(state["upgrades"].get(upgrade_id, 0))
        cost_text = (
            "已满级"
            if level >= len(definition["costs"])
            else "下一级%d点" % definition["costs"][level]
        )
        lines.append(
            "%s　%s Lv.%d｜%s｜%s"
            % (upgrade_id, definition["name"], level, cost_text, definition["desc"])
        )
    lines.append("现有资金：%d点" % state["cash"])
    return "\n".join(lines)


def _cmd_design(state: Dict[str, Any], args: List[str]) -> str:
    description = " ".join(args).strip()
    if not description:
        current = state.get("bar_concept", "")
        return (
            "当前酒吧设计：%s" % current
            if current
            else '用法：design "由AI自己描述的酒吧空间、材质、灯光与世界观"'
        )
    if len(description) > 600:
        return "酒吧设计描述请控制在600字以内。"
    state["bar_concept"] = description
    return (
        "酒吧的空间设计已经写入档案：%s\n"
        "这只是设计方向，不会免费获得物品。需要的软装、硬装或跨世界物件，"
        "可用 source_decor 加入商店，再用酒吧资金购买。"
        % description
    )


def _decor_reference_value(name: str, category: str) -> int:
    base = {"soft": 55, "hard": 320, "equipment": 220, "artifact": 250}[category]
    references = {
        "杯垫": 12,
        "摆件": 24,
        "花瓶": 32,
        "挂画": 45,
        "绿植": 40,
        "台灯": 58,
        "窗帘": 75,
        "地毯": 95,
        "椅": 85,
        "沙发": 180,
        "投影": 280,
        "点唱机": 300,
        "音响": 360,
        "空调": 420,
        "洗杯机": 460,
        "制冰机": 520,
        "舞台": 720,
        "吧台": 880,
        "包厢": 950,
        "酒窖": 1050,
        "传送门": 1120,
        "低重力": 980,
    }
    matched = [value for keyword, value in references.items() if keyword in name]
    return max([base] + matched)


def _cmd_source_decor(state: Dict[str, Any], args: List[str]) -> str:
    if len(args) < 3:
        return (
            '用法：source_decor "物品名" <soft|hard|equipment|artifact> '
            '"来源世界" [common|uncommon|rare|collector] [new|used|damaged] ["作用描述"]'
        )
    name, category, origin = args[0], args[1].lower(), args[2]
    if category not in ("soft", "hard", "equipment", "artifact"):
        return "分类必须是 soft、hard、equipment 或 artifact。"
    rarity = args[3].lower() if len(args) > 3 else "common"
    condition = args[4].lower() if len(args) > 4 else "new"
    if rarity not in ("common", "uncommon", "rare", "collector"):
        return "稀有度必须是 common、uncommon、rare 或 collector。"
    if condition not in ("new", "used", "damaged"):
        return "状态必须是 new、used 或 damaged。"
    if not name or len(name) > 50 or len(origin) > 80:
        return "物品名应为1～50字，来源不超过80字。"
    description = (
        " ".join(args[5:]).strip()
        if len(args) > 5
        else "由AI按照来源世界与物品规则持续演绎其视觉和影响"
    )
    value = _decor_reference_value(name, category)
    rarity_multiplier = {
        "common": 1.0,
        "uncommon": 1.25,
        "rare": 1.65,
        "collector": 2.2,
    }[rarity]
    condition_multiplier = {"new": 1.0, "used": 0.68, "damaged": 0.43}[condition]
    real_origins = ("现实", "地球", "本地", "二手市场", "家具店")
    world_multiplier = 1.0 if any(word in origin for word in real_origins) else 1.15
    cost = int(
        _clamp(
            round(value * rarity_multiplier * condition_multiplier * world_multiplier),
            10,
            1500,
        )
    )
    state["decor_no"] = int(state.get("decor_no", 0)) + 1
    decor_id = "custom_decor:%03d" % state["decor_no"]
    likes, _ = _catalog_tastes(decor_id + name + origin)
    definition = {
        "name": name,
        "cost": cost,
        "category": category,
        "origin": origin,
        "rarity": {
            "common": "常见",
            "uncommon": "少见",
            "rare": "稀有",
            "collector": "典藏",
        }[rarity],
        "condition": {
            "new": "全新",
            "used": "二手良好",
            "damaged": "残损待修",
        }[condition],
        "maintenance": max(0, min(8, cost // 160)),
        "tags": likes[:2],
        "desc": description,
    }
    definition["event_tags"] = _decor_event_tags(definition)
    state["decor_market"][decor_id] = definition
    state["decor_wishlist"].append(name)
    state["decor_wishlist"] = state["decor_wishlist"][-30:]
    return (
        "商店已经找到：%s　%s｜%s·%s｜来源：%s｜%d点｜维护%d点/次营业\n"
        "%s\n这只是上架，尚未付款；用 decorate %s 购买。"
        % (
            decor_id,
            name,
            definition["rarity"],
            definition["condition"],
            origin,
            cost,
            definition["maintenance"],
            description,
            decor_id,
        )
    )


def _cmd_decor(state: Dict[str, Any], args: List[str]) -> str:
    del args
    lines = [
        "【常驻商店｜软装、硬装与跨世界物件】（decorate <id>）",
        "AI可用 source_decor 自由描述目录外物品；价格按现实购买感、状态与稀有度换算成点数。",
    ]
    owned = state.get("decorations", {})
    catalog = dict(DECOR_DEFS)
    catalog.update(state.get("decor_market", {}))
    for decor_id, definition in catalog.items():
        status = (
            "已拥有"
            if decor_id in owned
            else "%d点" % int(definition["cost"])
        )
        lines.append(
            "%s　%s｜%s｜%s·%s｜维护%d点｜事件：%s｜%s"
            % (
                decor_id,
                definition["name"],
                status,
                definition.get("rarity", "常见"),
                definition.get("condition", "状态正常"),
                int(definition.get("maintenance", 2)),
                "、".join(
                    definition.get("event_tags") or _decor_event_tags(definition)
                ),
                definition["desc"],
            )
        )
    lines.append("装饰会轻微影响来客频率与满意度，但永远不会排除任何客人。")
    lines.append("现有资金：%d点" % state["cash"])
    return "\n".join(lines)


def _cmd_decorate(state: Dict[str, Any], args: List[str]) -> str:
    if not args:
        return "用法：decorate <装饰id>。先用 decor 查看。"
    decor_id = args[0]
    definition = _decor_definition(state, decor_id)
    if not definition:
        return "商店里没有这个物品。AI可以先用 source_decor 寻找它。"
    if decor_id in state.get("decorations", {}):
        return "酒馆已经摆放了%s。" % definition["name"]
    cost = int(definition["cost"])
    if state["cash"] < cost:
        return "资金不足：%s需要%d点，现有%d点。" % (
            definition["name"],
            cost,
            state["cash"],
        )
    before = state["cash"]
    _cash_change(state, -cost, "购买酒馆装饰：%s" % definition["name"], "spend")
    definition = dict(definition)
    definition.setdefault("event_tags", _decor_event_tags(definition))
    state.setdefault("decorations", {})[decor_id] = {
        "bought_visit": state["visit"],
        "definition": definition,
    }
    state["session"]["highlights"].append("添置装饰%s" % definition["name"])
    return "已添置%s（%s）。资金%d→%d点。%s" % (
        definition["name"],
        definition.get("category", "soft"),
        before,
        state["cash"],
        definition["desc"],
    )


def _cmd_ledger(state: Dict[str, Any], args: List[str]) -> str:
    del args
    entries = state.get("ledger", [])
    if not entries:
        return "账本还没有记录。当前资金%d点。" % state["cash"]
    lines = ["【资金流水｜最近12笔】"]
    for entry in entries[-12:]:
        lines.append(
            "第%d次｜%+d点｜余额%d｜%s"
            % (
                int(entry.get("visit", 0)),
                int(entry["amount"]),
                int(entry["balance"]),
                entry["reason"],
            )
        )
    return "\n".join(lines)


def _cmd_upgrade(state: Dict[str, Any], args: List[str]) -> str:
    if not args or args[0] not in UPGRADE_DEFS:
        return "用法：upgrade <升级id>。先用 upgrades 查看。"
    upgrade_id = args[0]
    definition = UPGRADE_DEFS[upgrade_id]
    level = int(state["upgrades"].get(upgrade_id, 0))
    if level >= len(definition["costs"]):
        return "%s已经满级。" % definition["name"]
    cost = int(definition["costs"][level])
    if state["cash"] < cost:
        return "资金不足：%s需要%d点，现有%d点。" % (
            definition["name"],
            cost,
            state["cash"],
        )
    before_cash = state["cash"]
    _cash_change(
        state,
        -cost,
        "购买酒馆升级：%s Lv.%d" % (definition["name"], level + 1),
        "spend",
    )
    state["upgrades"][upgrade_id] = level + 1
    state["session"]["highlights"].append(
        "升级%s到Lv.%d" % (definition["name"], level + 1)
    )
    return "完成升级：%s Lv.%d，花费%d点。资金%d→%d点。" % (
        definition["name"],
        level + 1,
        cost,
        before_cash,
        state["cash"],
    )


def _cmd_report(state: Dict[str, Any], args: List[str]) -> str:
    del args
    session = state["session"]
    guest_names = [
        state["records"][guest_id]["card"]["name"]
        for guest_id in session["guests"]
        if guest_id in state["records"]
    ]
    lines = [
        "【本次经营简报】",
        "收入%d点｜支出%d点｜净变化%+d点｜当前资金%d点（%s）"
        % (
            session["revenue"],
            session["spend"],
            session["revenue"] - session["spend"],
            state["cash"],
            _financial_health(state),
        ),
        "声誉%d/100｜本次评价：%d条"
        % (state.get("reputation", 50), len(session.get("reviews", []))),
        "遇见：%s" % ("、".join(guest_names) if guest_names else "暂无特别来客"),
        "我喝过：%s"
        % (
            "、".join(session["owner_drinks"])
            if session["owner_drinks"]
            else "这次还没喝"
        ),
    ]
    highlights = session["highlights"][-3:]
    if highlights:
        lines.append("值得转达：\n" + "\n".join("• " + item for item in highlights))
    if session.get("interactions"):
        lines.append("NPC互动：%s" % session["interactions"][-1])
    if session.get("decor_events"):
        lines.append("装修事件：%s" % session["decor_events"][-1])
    lines.append("当前状态：" + _body_line(state))
    return "\n".join(lines)


def _cmd_loan(state: Dict[str, Any], args: List[str]) -> str:
    del args
    if int(state.get("loan_payments_left", 0)) > 0:
        return "已有应急贷款未还清：余额%d点，还需%d次营业还款。" % (
            state.get("loan_balance", 0),
            state.get("loan_payments_left", 0),
        )
    if state["cash"] >= 80:
        return "资金尚未陷入危机，当前不能申请应急贷款。"
    before = state["cash"]
    _cash_change(state, 300, "取得应急经营贷款", None)
    state["loan_balance"] = 450
    state["loan_payments_left"] = 10
    return (
        "取得300点应急资金，资金%d→%d点。此后10次营业结束各偿还45点，"
        "总还款450点。贷款能救急，但会长期压缩利润。"
        % (before, state["cash"])
    )


def _cmd_reviews(state: Dict[str, Any], args: List[str]) -> str:
    del args
    reviews = state.get("reviews", [])
    if not reviews:
        return "还没有客人留下评价。当前声誉%d/100。" % state.get(
            "reputation", 50
        )
    lines = [
        "【客人评价｜最近10条】",
        "当前声誉：%d/100" % state.get("reputation", 50),
    ]
    for review in reviews[-10:]:
        lines.append(
            "%s｜%s｜%s｜实付%d点\n%s"
            % (
                "★" * int(review["stars"]) + "☆" * (5 - int(review["stars"])),
                review["guest"],
                review["drink"],
                review["paid"],
                review["text"],
            )
        )
    return "\n".join(lines)


def _cmd_leave(state: Dict[str, Any], args: List[str]) -> str:
    del args
    if state["phase"] != "open":
        return "酒吧当前没有营业。"
    waiting = [g for g in state["active_guests"] if not g["served"]]
    if waiting:
        return "还有客人在等待。先招待或 decline，再离店。"
    decor_maintenance = sum(
        int(definition.get("maintenance", 2))
        for definition in _owned_decor_definitions(state)
    )
    fixed_cost = (
        52
        + decor_maintenance
        + sum(int(level) for level in state.get("upgrades", {}).values()) * 2
    )
    _cash_change(
        state,
        -fixed_cost,
        "本次营业租金、水电、维护与基础损耗",
        "spend",
    )
    loan_line = ""
    if int(state.get("loan_payments_left", 0)) > 0:
        payment = min(45, int(state.get("loan_balance", 0)))
        _cash_change(state, -payment, "偿还应急经营贷款", "spend")
        state["loan_balance"] = max(
            0, int(state.get("loan_balance", 0)) - payment
        )
        state["loan_payments_left"] = max(
            0, int(state.get("loan_payments_left", 0)) - 1
        )
        loan_line = "\n本次偿还贷款%d点，剩余%d点。" % (
            payment,
            state["loan_balance"],
        )
    memory = _session_memory(state)
    state["memories"].append(memory)
    state["memories"] = state["memories"][-30:]
    state["phase"] = "closed"
    state["active_guests"] = []
    state["interaction"] = None
    state["vendor"] = None
    state["post_bar"] = _intox(state) >= 3 or state["body"]["pending"] > 0
    state["post_bar_turns"] = 0
    state["session"] = _empty_session()
    _refresh_market(state, starter=False)
    if state["post_bar"]:
        after = (
            "离开后醉态仍然有效。此后每一次回复用户前，都必须调用 "
            "conversation_turn(user_message)，并按返回的强制演绎锁完成实际回复。\n"
            + _post_bar_lock_text(state)
        )
    else:
        after = "这次没有留下酒后影响，可以立即按平常方式交流。"
    risk = (
        "\n⚠️ 经营警报：资金已经为负。下一次若没有提高收入或控制成本，"
        "酒馆会继续亏损。必要时可用 loan 申请高成本应急贷款。"
        if state["cash"] < 0
        else ""
    )
    return (
        memory
        + "\n固定营业成本：%d点。%s" % (fixed_cost, _financial_health(state))
        + loan_line
        + risk
        + "\n"
        + after
        + "\n酒吧档案已更新，可用 archive 写入长期记忆。"
    )


def _run_one(state: Dict[str, Any], command: str) -> str:
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        return "指令没有写完整：%s" % exc
    if not parts:
        return "空指令。"
    name, args = parts[0].lower(), parts[1:]
    if name in ("help", "?"):
        return _help()
    if name == "setup":
        return _cmd_setup(state, args)
    if name == "design":
        return _cmd_design(state, args)
    if name in ("market", "shop"):
        return _cmd_market(state, args)
    if name == "vendor":
        return _cmd_vendor(state, args)
    if name == "buy":
        return _cmd_buy(state, args)
    if name == "open":
        return _cmd_open(state, args)
    if name == "next":
        return _cmd_next(state, args)
    if name == "drinks":
        return _cmd_drinks(state, args)
    if name == "invent":
        return _cmd_invent(state, args)
    if name == "recipe":
        return _cmd_recipe(state, args)
    if name == "price":
        return _cmd_price(state, args)
    if name == "serve":
        return _cmd_serve(state, args, False)
    if name == "cheers":
        return _cmd_serve(state, args, True)
    if name == "recommend":
        return _cmd_recommend(state, args)
    if name == "drink":
        return _cmd_drink(state, args)
    if name == "cheers_user":
        return _cmd_cheers_user(state, args)
    if name == "decline":
        return _cmd_decline(state, args)
    if name == "talk":
        return _cmd_talk(state, args)
    if name == "observe":
        return _advance_interaction(state)
    if name == "intervene":
        return _cmd_intervene(state, args)
    if name == "story_note":
        return _cmd_story_note(state, args)
    if name == "water":
        return _cmd_water(state, args)
    if name == "eat":
        return _cmd_eat(state, args)
    if name == "status":
        return _cmd_status(state, args)
    if name == "guests":
        return _cmd_guests(state, args)
    if name == "memory":
        return _cmd_memory(state, args)
    if name == "report":
        return _cmd_report(state, args)
    if name == "ledger":
        return _cmd_ledger(state, args)
    if name == "reviews":
        return _cmd_reviews(state, args)
    if name == "loan":
        return _cmd_loan(state, args)
    if name == "upgrades":
        return _cmd_upgrades(state, args)
    if name == "upgrade":
        return _cmd_upgrade(state, args)
    if name == "decor":
        return _cmd_decor(state, args)
    if name == "source_decor":
        return _cmd_source_decor(state, args)
    if name == "decorate":
        return _cmd_decorate(state, args)
    if name == "leave":
        return _cmd_leave(state, args)
    return "不认识指令 %r。用 help 查看。" % parts[0]


def cmd(command: str) -> str:
    """执行一条或一批内部指令。用户无需直接学习这些指令。"""
    if not isinstance(command, str):
        return "指令必须是字符串。"
    segments = [
        part.strip()
        for line in command.splitlines()
        for part in line.split(";")
        if part.strip()
    ]
    if not segments:
        return "空指令。"
    if len(segments) > 8:
        return "一次最多执行8条指令。"
    try:
        state = _load()
        if len(segments) == 1 and segments[0].lower() == "archive":
            return _archive_from_state(state)
        outputs = []
        for segment in segments:
            result = _run_one(state, segment)
            outputs.append(
                ("▶ " + segment + "\n" + result) if len(segments) > 1 else result
            )
        _save(state)
        outputs.append(
            "📊 "
            + json.dumps(_status_data(state), ensure_ascii=False, separators=(",", ":"))
        )
        return "\n\n".join(outputs)
    except Exception as exc:
        return "⚠️ 游戏未能完成这次操作：%s" % exc


def new_game(seed: Optional[int] = None) -> str:
    """建立全新酒吧档案；默认随机，传入种子时可复现同一局。"""
    try:
        seed_value = _fresh_seed() if seed is None else int(seed)
        state = _default_state(seed_value)
        _refresh_market(state, starter=True)
        _save(state)
    except Exception as exc:
        return "⚠️ 无法建立新游戏：%s" % exc
    return (
        "《空杯俱乐部》已建立空白档案（种子%d）。\n"
        "第一步由AI自己决定酒吧名与口味："
        'setup "酒吧名" 喜欢标签 [讨厌标签]。' % seed_value
    )


if __name__ == "__main__":
    print(_help())
