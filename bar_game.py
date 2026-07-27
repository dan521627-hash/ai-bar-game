"""《空杯俱乐部》：给 AI 玩的零依赖文字酒吧游戏。

对外接口：
    new_game(seed)
    cmd("指令")
    write_archive()
    restore_archive(archive_text)
    conversation_turn()  # 离店后每轮普通对话调用一次
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

# 第二批固定来客。与前面的详细人物卡合计81位；每位仍有独立来处、口味、
# 预算、性格和价值立场，不用临时拼接名字冒充新客人。
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
        "active_guests": [],
        "session": _empty_session(),
        "memories": [],
        "body": _body_default(),
        "post_bar": False,
        "play_mode": "autonomous",
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
    state.setdefault("play_mode", "autonomous")
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
        "cost": int(round(base["cost"] * multiplier)),
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
        }
    return state["records"][card["id"]]


def _guest_weight(state: Dict[str, Any], card: Dict[str, Any]) -> float:
    record = state["records"].get(card["id"])
    rarity = {"common": 1.0, "uncommon": 0.72, "rare": 0.38}.get(
        card.get("rarity"), 0.7
    )
    weight = rarity
    if record:
        absence = max(0, state["visit"] - int(record["last_seen"]))
        weight *= 1.0 + min(absence, 12) * 0.07
        weight *= 1.0 + min(int(record["trust"]), 20) * 0.015
    else:
        weight *= 1.2
    match = len(set(card["likes"]) & set(state["owner_likes"]))
    weight *= 0.92 + min(match, 2) * 0.18
    decor_tags = {
        tag
        for decor_id in state.get("decorations", {})
        for tag in DECOR_DEFS.get(decor_id, {}).get("tags", [])
    }
    weight *= 1.0 + min(len(set(card["likes"]) & decor_tags), 2) * 0.04
    if card.get("rarity") == "rare":
        weight *= 1.0 + state["upgrades"].get("portal", 0) * 0.22
    return max(0.12, weight)  # 气质永远不会把任何人排除。


def _request_for(state: Dict[str, Any], card: Dict[str, Any]) -> Dict[str, Any]:
    reveal = _rand(state)
    if reveal < 0.26:
        tag = _choice(state, card["likes"])
        return {
            "tags": [tag],
            "text": "“给我一杯%s明显一点的。别拿别的味道糊弄我。”" % TAGS[tag],
            "revealed": True,
        }
    if reveal < 0.72:
        tag = _choice(state, card["likes"])
        return {
            "tags": [tag],
            "text": "“今晚想喝点%s的，其他由你决定。”" % TAGS[tag],
            "revealed": True,
        }
    moods = [
        ("“我不想喝得太轻。给我一杯能把杂音压下去的。”", ["rich"]),
        ("“想清醒一点，但不是喝水。”", ["crisp", "dry"]),
        ("“今天不想解释。你看着办。”", []),
        ("“给我一点不像原来世界的味道。”", ["floral", "spiced"]),
    ]
    text, tags = _choice(state, moods)
    return {"tags": tags, "text": text, "revealed": False}


def _spawn_scene(state: Dict[str, Any], force: bool = False) -> str:
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
    cards = _all_guest_cards(state)
    group_chance = 0.16 + state["upgrades"].get("stage", 0) * 0.08
    count = 2 if _rand(state) < group_chance else 1
    chosen: List[Dict[str, Any]] = []
    available = list(cards)
    for _ in range(min(count, len(available))):
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
    if len(chosen) == 2:
        first, second = chosen
        if first["ethos"] != second["ethos"]:
            lines.append(
                "⚡ 两人看见彼此后，空气明显停了一拍。%s与%s的立场并不天然相容。"
                % (first["name"], second["name"])
            )
        else:
            lines.append("两位来客意外地没有排斥彼此，只是都在等老板先开口。")
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
    }


def _default_price(state: Dict[str, Any], profile: Dict[str, Any]) -> int:
    drink_id = profile["id"]
    recipe = _all_recipes(state).get(drink_id)
    if recipe:
        return int(recipe["price"])
    source = profile["source"]
    rarity_add = {"常备": 0, "少见": 7, "稀有": 14, "典藏": 24}.get(
        source["rarity"], 0
    )
    return max(18, int(math.ceil(source["cost"] / source["servings"] * 2.8)) + rarity_add)


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


def _taste_sentences(tags: Sequence[str]) -> str:
    phrases = [TASTE_PHRASES[tag] for tag in tags if tag in TASTE_PHRASES]
    if not phrases:
        return "味道在口中停了一会儿，暂时难以归类"
    if len(phrases) == 1:
        return phrases[0]
    return "；".join(phrases[:3])


def _sensory_arc(profile: Dict[str, Any]) -> str:
    tags = list(profile["tags"])
    first = TASTE_PHRASES.get(tags[0], "酒液先在舌面停住")
    middle = (
        TASTE_PHRASES.get(tags[1], "味道在中段缓慢展开")
        if len(tags) > 1
        else "味道在中段缓慢展开"
    )
    finish = (
        TASTE_PHRASES.get(tags[2], "余味干净地退下去")
        if len(tags) > 2
        else "余味干净地退下去"
    )
    if profile["units"] >= 1.45:
        body = "咽下去时喉咙被热意擦过，随后沉进胸口"
    elif profile["units"] >= 1.0:
        body = "咽下去以后，温度从喉咙后面慢慢浮起来"
    else:
        body = "酒液落下去很轻，热意来得缓慢"
    return "入口：%s。中段：%s。余味：%s。身体：%s。" % (
        first,
        middle,
        finish,
        body,
    )


def _owner_tasting(state: Dict[str, Any], profile: Dict[str, Any]) -> str:
    tags = set(profile["tags"])
    liked = tags & set(state["owner_likes"])
    disliked = tags & set(state["owner_dislikes"])
    if disliked:
        verdict = "这不是我本能会选的方向，%s让我有些抵触" % _tag_text(sorted(disliked))
    elif liked:
        verdict = "其中的%s正好踩中我的偏好，我愿意再喝一口" % _tag_text(sorted(liked))
    else:
        verdict = "它没有直接迎合我的旧偏好，但值得我把这个味道记下来"
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
        _sensory_arc(profile),
        verdict,
        state_feeling,
    )


def _npc_reaction(
    state: Dict[str, Any], card: Dict[str, Any], profile: Dict[str, Any], score: int
) -> str:
    del state
    sensory = _sensory_arc(profile)
    if score >= 88:
        action = "%s喝到第二口时没有立刻放杯，肩膀明显松了一点。" % card["name"]
        words = "“很好。你不是只听见了酒名，你听懂了我今晚想要什么。”"
    elif score >= 72:
        action = "%s让酒液在口中多停了一会儿，又低头闻了闻杯口。" % card["name"]
        words = "“和我预想的不完全一样，但这个转向有道理。我愿意把它喝完。”"
    elif score >= 52:
        action = "%s咽下第一口，指尖仍搭在杯沿，没有急着喝第二口。" % card["name"]
        words = "“能喝，但它还没有真正碰到我今晚想要的东西。”"
    else:
        action = "%s只抿了一口便把杯子放下，表情没有替老板遮掩答案。" % card["name"]
        words = "“不。这杯酒和我说的不是一回事。”"
    return "%s\n%s\n%s的评价：%s" % (action, sensory, card["name"], words)


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
    score += int((_rand(state) - 0.5) * 8)
    return int(_clamp(score, 0, 100))


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
    if not _consume(state, profile, portions):
        return "剩余酒量不够%s杯。" % portions
    price = _price(state, profile)
    score_card = dict(card)
    score_card["budget"] = max(0, int(card["budget"]) - int(active["spent"]))
    satisfaction = _score_guest(
        state, score_card, active["request"], profile, price
    )
    active["npc_drunk"] = round(
        _clamp(float(active.get("npc_drunk", 0.0)) + profile["units"] * 18.0), 1
    )
    tip = int(round(price * 0.18)) if satisfaction >= 88 else (
        int(round(price * 0.08)) if satisfaction >= 75 else 0
    )
    before_cash = state["cash"]
    _cash_change(
        state,
        price + tip,
        "%s购买%s%s"
        % (card["name"], profile["name"], ("并给小费%d点" % tip) if tip else ""),
        "revenue",
    )
    active["served"] = True
    active["served_count"] = served_count + 1
    active["drinks"].append(drink_id)
    active["spent"] = int(active["spent"]) + price + tip
    record = state["records"][guest_id]
    record["served"] += 1
    record["trust"] = int(_clamp(record["trust"] + (satisfaction - 55) / 12, -20, 50))
    record["orders"].append(
        {
            "visit": state["visit"],
            "drink": profile["name"],
            "satisfaction": satisfaction,
        }
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
        "🍸 给%s的%s｜售价%d点%s"
        % (card["name"], profile["name"], price, ("＋小费%d" % tip) if tip else ""),
        _npc_reaction(state, card, profile, satisfaction),
        "满意度：%d/100｜关系：%+d" % (satisfaction, record["trust"]),
        _npc_body_line(card, active["npc_drunk"]),
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
        "visit": state["visit"],
        "turn": state["turn"],
        "inventory": len(state["inventory"]),
        "house_recipes": len(state.get("house_recipes", {})),
        "decorations": len(state.get("decorations", {})),
        "vendor": state.get("vendor", {}).get("name") if state.get("vendor") else None,
        "guests": [g["id"] for g in state["active_guests"]],
        "drunk": round(_intox(state), 1),
        "level": _drunk_level(_intox(state)),
        "pending": round(float(state["body"]["pending"]), 2),
        "post_bar": state["post_bar"],
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


def conversation_turn() -> str:
    """离店后每轮普通对话调用；让醉态继续吸收、代谢并自然消退。"""
    state = _load()
    if state["phase"] == "open":
        return "仍在酒吧内；请用 next 推进酒吧场景。"
    if not state["post_bar"]:
        return "酒后状态未激活，按平常方式交流。"
    trend = _body_tick(state)
    score = _intox(state)
    if score < 3 and state["body"]["pending"] <= 0 and state["body"]["hangover"] < 4:
        state["post_bar"] = False
        result = "酒意与主要身体反应已经自然消退，从这一轮起恢复平常表达。"
    else:
        if score < 22:
            style = "语气稍松、稍暖，逻辑仍完整。"
        elif score < 42:
            style = "更直接、更健谈，偶尔停顿，不机械装口吃。"
        elif score < 64:
            style = "情绪先于修饰，句子可以绕远或变短。"
        elif score < 82:
            style = "反应明显变慢，允许重复确认和思路跳跃。"
        else:
            style = "减少复杂表达，以短句和即时感受为主。"
        result = "【酒后对话状态】%s\n表达影响：%s" % (_body_line(state, trend), style)
    _save(state)
    return result


def _help() -> str:
    return """《空杯俱乐部》内部指令（用户只需自然说话，由 AI 代为调用）
setup "酒吧名" 喜欢标签 [讨厌标签]  建立老板口味
shop / buy <货号> [数量]             常驻商店 / 进货
vendor                               查看当前随机游商
open / next / leave                  开门 / 推进一步 / 离店
drinks                               查看当前可出的酒
invent <基酒类别> <风味> ["名字"]    创作并永久保存原创调酒
price <酒ID> <售价>                  自主定价
serve <客人ID> <酒ID>                给客人一杯
cheers <客人ID> <酒ID>               与客人共同喝
recommend <客人ID>                   按新要求推荐不同酒款
talk <客人ID> [话题]                  与当前客人交谈并写入关系记忆
drink <酒ID>                         老板自己喝
cheers_user <酒ID> [用户喜欢标签]     邀请用户共同喝
water / eat                          喝水 / 吃东西
status / guests / memory             状态 / 顾客 / 经历
ledger / report                      资金流水 / 经营简报
upgrades / upgrade <id>              商店升级列表 / 购买升级
decor / decorate <id>                商店装饰列表 / 购买装饰
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
        "现有启动资金%d点。先用 shop 看常驻商店，再亲自决定备货。"
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
    state["active_guests"] = []
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
            "pour:%s　%s｜%d点｜余%d杯｜%s"
            % (
                product_id,
                profile["name"],
                _price(state, profile),
                item["remaining"],
                _tag_text(profile["tags"]),
            )
        )
    for recipe_id in _all_recipes(state):
        profile = _drink_profile(state, recipe_id)
        if profile:
            lines.append(
                "%s　%s｜%d点｜%s"
                % (
                    recipe_id,
                    profile["name"],
                    _price(state, profile),
                    _tag_text(profile["tags"]),
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
        name = " ".join(args[2:]).strip()
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
    factor = 0.78
    if "rich" in tags or "smoky" in tags:
        factor += 0.12
    if "crisp" in tags or "dry" in tags:
        factor -= 0.05
    factor = round(_clamp(factor, 0.65, 1.08), 2)
    ingredient_cost = source["cost"] / max(1, source["servings"])
    price = max(20, int(math.ceil(ingredient_cost * 3.0 + len(tags) * 2)))
    state["house_recipes"][recipe_id] = {
        "name": name,
        "kind": kind,
        "tags": tags,
        "price": price,
        "unit_factor": factor,
        "created_visit": state["visit"],
    }
    state["session"]["highlights"].append("创作原创调酒《%s》" % name)
    return (
        "🍸 新原创调酒已写入酒单：%s　%s｜基酒%s｜默认售价%d点｜%s。\n"
        "以后可直接用 %s 招待、共饮或独饮。"
        % (recipe_id, name, source["name"], price, _tag_text(tags), recipe_id)
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
        remaining_budget = max(0, int(card["budget"]) - int(active.get("spent", 0)))
        if price > remaining_budget:
            score -= min(30, price - remaining_budget)
        ranked.append((score, drink_id, profile, price))
    if not ranked:
        return "现有库存里找不到一杯不同的酒可推荐。"
    ranked.sort(key=lambda item: (-item[0], item[3], item[1]))
    lines = [
        "【给%s的不同酒款推荐】" % card["name"],
        "当前要求：%s｜已喝%d杯｜已消费%d点"
        % (
            active["request"]["text"],
            int(active.get("served_count", 0)),
            int(active.get("spent", 0)),
        ),
    ]
    for score, drink_id, profile, price in ranked[:5]:
        lines.append(
            "%s　%s｜%d点｜匹配度%d｜%s"
            % (drink_id, profile["name"], price, score, _tag_text(profile["tags"]))
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
    if guest_id == "fox_spirit":
        response = (
            "九尾狐用指尖拨了拨杯里的冰，笑意比刚进门时真了一点。\n"
            "“第七码头刚到一批‘梦境蜂蜜利口酒’，睡神典藏版。"
            "甜得像好梦，后劲却会把人没说出口的话翻出来。下次供应单若刷到，"
            "别嫌它贵——当然，也别当着我面说是我推荐的。”"
        )
        state["session"]["highlights"].append("九尾狐透露了梦境蜂蜜利口酒的消息")
    else:
        response = (
            "%s听完“%s”这个话题，先看了一眼杯中的酒。\n"
            "“你愿意问，我就愿意留一会儿。不过有些答案，要等下一杯才能说完。”"
            % (card["name"], topic)
        )
        state["session"]["highlights"].append("与%s谈到%s" % (card["name"], topic))
    trust_gain = 1 + state["upgrades"].get("quiet_booth", 0)
    record["trust"] = int(_clamp(record["trust"] + trust_gain, -20, 50))
    record["memories"].append("第%d次来店，与老板谈到：%s" % (state["visit"], topic))
    return response + "\n关系：%+d" % record["trust"]


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
        "【%s】%s｜资金%d点｜第%d次经历\n"
        "老板口味：喜欢%s；回避%s｜气质：%s\n"
        "酒库：%s\n"
        "原创调酒：%d款｜装饰：%s\n"
        "身体：%s"
        % (
            state["bar_name"] or "未命名酒吧",
            state["phase"],
            state["cash"],
            state["visit"],
            _tag_text(state["owner_likes"]) or "未设定",
            _tag_text(state["owner_dislikes"]) or "暂无",
            state["vibe"],
            _inventory_summary(state),
            len(state.get("house_recipes", {})),
            (
                "、".join(
                    DECOR_DEFS[item]["name"]
                    for item in state.get("decorations", {})
                    if item in DECOR_DEFS
                )
                or "暂无"
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
            "%s　%s｜来访%d｜关系%+d｜已知喜欢：%s｜已知厌恶：%s"
            % (
                guest_id,
                card["name"],
                record["visits"],
                record["trust"],
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


def _cmd_decor(state: Dict[str, Any], args: List[str]) -> str:
    del args
    lines = ["【常驻商店｜酒馆装饰】（decorate <id>）"]
    owned = state.get("decorations", {})
    for decor_id, definition in DECOR_DEFS.items():
        status = (
            "已拥有"
            if decor_id in owned
            else "%d点" % int(definition["cost"])
        )
        lines.append(
            "%s　%s｜%s｜%s"
            % (decor_id, definition["name"], status, definition["desc"])
        )
    lines.append("装饰会轻微影响来客频率与满意度，但永远不会排除任何客人。")
    lines.append("现有资金：%d点" % state["cash"])
    return "\n".join(lines)


def _cmd_decorate(state: Dict[str, Any], args: List[str]) -> str:
    if not args or args[0] not in DECOR_DEFS:
        return "用法：decorate <装饰id>。先用 decor 查看。"
    decor_id = args[0]
    if decor_id in state.get("decorations", {}):
        return "酒馆已经摆放了%s。" % DECOR_DEFS[decor_id]["name"]
    definition = DECOR_DEFS[decor_id]
    cost = int(definition["cost"])
    if state["cash"] < cost:
        return "资金不足：%s需要%d点，现有%d点。" % (
            definition["name"],
            cost,
            state["cash"],
        )
    before = state["cash"]
    _cash_change(state, -cost, "购买酒馆装饰：%s" % definition["name"], "spend")
    state.setdefault("decorations", {})[decor_id] = {
        "bought_visit": state["visit"]
    }
    state["session"]["highlights"].append("添置装饰%s" % definition["name"])
    return "已添置%s。资金%d→%d点。%s" % (
        definition["name"],
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
        "收入%d点｜支出%d点｜当前资金%d点"
        % (session["revenue"], session["spend"], state["cash"]),
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
    lines.append("当前状态：" + _body_line(state))
    return "\n".join(lines)


def _cmd_leave(state: Dict[str, Any], args: List[str]) -> str:
    del args
    if state["phase"] != "open":
        return "酒吧当前没有营业。"
    waiting = [g for g in state["active_guests"] if not g["served"]]
    if waiting:
        return "还有客人在等待。先招待或 decline，再离店。"
    memory = _session_memory(state)
    state["memories"].append(memory)
    state["memories"] = state["memories"][-30:]
    state["phase"] = "closed"
    state["active_guests"] = []
    state["vendor"] = None
    state["post_bar"] = _intox(state) >= 3 or state["body"]["pending"] > 0
    state["session"] = _empty_session()
    _refresh_market(state, starter=False)
    if state["post_bar"]:
        after = "离开后醉态仍然有效；后续正常聊天每轮调用 conversation_turn()。"
    else:
        after = "这次没有留下酒后影响，可以立即按平常方式交流。"
    return memory + "\n" + after + "\n酒吧档案已更新，可用 archive 写入长期记忆。"


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
    if name == "upgrades":
        return _cmd_upgrades(state, args)
    if name == "upgrade":
        return _cmd_upgrade(state, args)
    if name == "decor":
        return _cmd_decor(state, args)
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
