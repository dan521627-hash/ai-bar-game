"""《万象酒馆》：给 AI 玩的零依赖文字酒吧游戏。

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
}

SPECIAL_PARTS = {
    "gin": [
        ("雾庭月桂金酒", ["herbal", "floral", "dry"], "月蚀小批次"),
        ("零度星港金酒", ["crisp", "floral", "bitter"], "极光纪念版"),
    ],
    "rum": [
        ("沉船黑糖朗姆", ["sweet", "spiced", "smoky"], "旧海图典藏版"),
        ("双月陈年朗姆", ["rich", "fruity", "woody"], "双桶限定版"),
    ],
    "whisky": [
        ("灰鲸泥煤威士忌", ["smoky", "woody", "bitter"], "潮汐桶限定版"),
        ("水楢回声威士忌", ["woody", "floral", "spiced"], "十二年纪念版"),
    ],
    "vodka": [
        ("彗尾冰晶伏特加", ["crisp", "dry", "floral"], "彗星批次"),
        ("白夜黑麦伏特加", ["dry", "spiced", "rich"], "冬至版"),
    ],
    "tequila": [
        ("蓝焰陈年龙舌兰", ["herbal", "smoky", "rich"], "火山岩桶版"),
        ("沙海银龙舌兰", ["crisp", "spiced", "floral"], "流星限定版"),
    ],
    "brandy": [
        ("无花果旧桶白兰地", ["fruity", "woody", "sweet"], "庄园私藏版"),
        ("时钟塔白兰地", ["rich", "spiced", "woody"], "百年纪念版"),
    ],
    "wine": [
        ("赤月谷红葡萄酒", ["fruity", "dry", "rich"], "赤月年份版"),
        ("云上花园白葡萄酒", ["floral", "crisp", "sour"], "浮岛限定版"),
    ],
    "liqueur": [
        ("梦境蜂蜜利口酒", ["sweet", "floral", "rich"], "睡神典藏版"),
        ("苦艾绿时钟", ["herbal", "bitter", "spiced"], "午夜批次"),
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
}

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
]


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
        "market": [],
        "market_no": 0,
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
    offers = []
    base_ids = list(BASE_PRODUCTS)
    if starter:
        selected = base_ids
    else:
        selected = []
        bag = list(base_ids)
        while bag and len(selected) < 5:
            item = _choice(state, bag)
            bag.remove(item)
            selected.append(item)
    for product_id in selected:
        product = dict(BASE_PRODUCTS[product_id])
        product["id"] = product_id
        offers.append(product)
    if not starter:
        kinds = list(SPECIAL_PARTS)
        for _ in range(3):
            offers.append(_make_special(state, _choice(state, kinds)))
    for index, offer in enumerate(offers, 1):
        offer["offer_id"] = "o%d" % index
    state["market"] = offers


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


def _find_source(state: Dict[str, Any], drink_id: str) -> Optional[Dict[str, Any]]:
    inventory = state["inventory"]
    if drink_id.startswith("pour:"):
        product_id = drink_id.split(":", 1)[1]
        item = inventory.get(product_id)
        return item if item and item["remaining"] > 0 else None
    recipe = RECIPES.get(drink_id)
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
    recipe = RECIPES[drink_id]
    return {
        "id": drink_id,
        "name": recipe["name"],
        "tags": list(dict.fromkeys(recipe["tags"] + source["tags"][:1])),
        "units": round(float(source["units"]) * recipe["unit_factor"], 2),
        "source": source,
    }


def _default_price(profile: Dict[str, Any]) -> int:
    drink_id = profile["id"]
    if drink_id in RECIPES:
        return int(RECIPES[drink_id]["price"])
    source = profile["source"]
    rarity_add = {"常备": 0, "少见": 7, "稀有": 14, "典藏": 24}.get(
        source["rarity"], 0
    )
    return max(18, int(math.ceil(source["cost"] / source["servings"] * 2.8)) + rarity_add)


def _price(state: Dict[str, Any], profile: Dict[str, Any]) -> int:
    return int(state["prices"].get(profile["id"], _default_price(profile)))


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
    score += int((_rand(state) - 0.5) * 8)
    return int(_clamp(score, 0, 100))


def _serve_guest(
    state: Dict[str, Any], guest_id: str, drink_id: str, owner_joins: bool
) -> str:
    active = next((g for g in state["active_guests"] if g["id"] == guest_id), None)
    if not active:
        return "这位客人现在不在店里。"
    if active["served"]:
        return "这位客人已经拿到酒了。可以 next 让场景继续。"
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
    satisfaction = _score_guest(state, card, active["request"], profile, price)
    active["npc_drunk"] = round(
        _clamp(float(active.get("npc_drunk", 0.0)) + profile["units"] * 18.0), 1
    )
    tip = int(round(price * 0.18)) if satisfaction >= 88 else (
        int(round(price * 0.08)) if satisfaction >= 75 else 0
    )
    state["cash"] += price + tip
    state["session"]["revenue"] += price + tip
    active["served"] = True
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
    return """《万象酒馆》内部指令（用户只需自然说话，由 AI 代为调用）
setup "酒吧名" 喜欢标签 [讨厌标签]  建立老板口味
market / buy <货号> [数量]           查看供应商 / 进货
open / next / leave                  开门 / 推进一步 / 离店
drinks                               查看当前可出的酒
price <酒ID> <售价>                  自主定价
serve <客人ID> <酒ID>                给客人一杯
cheers <客人ID> <酒ID>               与客人共同喝
talk <客人ID> [话题]                  与当前客人交谈并写入关系记忆
drink <酒ID>                         老板自己喝
cheers_user <酒ID> [用户喜欢标签]     邀请用户共同喝
water / eat                          喝水 / 吃东西
status / guests / memory             状态 / 顾客 / 经历
report / upgrades / upgrade <id>     经营简报 / 升级列表 / 购买升级
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
        "现有启动资金%d点。先用 market 看基础酒，再亲自决定备货。"
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
    lines = ["【供应商第%d期】（buy <货号>）" % state["market_no"]]
    for offer in state["market"]:
        lines.append(
            "%s　%s｜%s·%s｜%d点/%d杯｜%s"
            % (
                offer["offer_id"],
                offer["name"],
                offer["rarity"],
                offer["edition"],
                offer["cost"],
                offer["servings"],
                _tag_text(offer["tags"]),
            )
        )
    return "\n".join(lines)


def _cmd_buy(state: Dict[str, Any], args: List[str]) -> str:
    if not args:
        return "用法：buy <货号> [数量]"
    offer = next((item for item in state["market"] if item["offer_id"] == args[0]), None)
    if not offer:
        return "当前供应商没有这个货号。"
    try:
        count = int(args[1]) if len(args) > 1 else 1
    except ValueError:
        return "数量必须是整数。"
    if count < 1 or count > 5:
        return "一次可购买1～5瓶。"
    total = offer["cost"] * count
    if state["cash"] < total:
        return "资金不足：需要%d点，现有%d点。" % (total, state["cash"])
    cellar_limit = 10 + state["upgrades"].get("cellar", 0) * 4
    if offer["id"] not in state["inventory"] and len(state["inventory"]) >= cellar_limit:
        return "酒窖已满（%d种）。先升级 cellar，或消耗现有库存。" % cellar_limit
    state["cash"] -= total
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
    state["session"]["spend"] += total
    state["session"]["bought"].append("%s×%d" % (offer["name"], count))
    return "购入%s×%d，花%d点。现有资金%d点，库存%d杯。" % (
        offer["name"],
        count,
        total,
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
    lines = ["【当前可出酒单】"]
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
    for recipe_id in RECIPES:
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
    state["cash"] -= 12
    kitchen = state["upgrades"].get("kitchen", 0)
    state["body"]["stomach"] = round(
        _clamp(state["body"]["stomach"] + 30 + kitchen * 8), 2
    )
    state["body"]["nausea"] = round(
        _clamp(state["body"]["nausea"] - 6 - kitchen * 3), 2
    )
    trend = _body_tick(state)
    return "我吃了一份热食，后续吸收会慢一些。\n" + _body_line(state, trend)


def _cmd_status(state: Dict[str, Any], args: List[str]) -> str:
    del args
    return (
        "【%s】%s｜资金%d点｜第%d次经历\n"
        "老板口味：喜欢%s；回避%s｜气质：%s\n"
        "酒库：%s\n"
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
    state["cash"] -= cost
    state["upgrades"][upgrade_id] = level + 1
    state["session"]["spend"] += cost
    state["session"]["highlights"].append(
        "升级%s到Lv.%d" % (definition["name"], level + 1)
    )
    return "完成升级：%s Lv.%d，花费%d点。现有资金%d点。" % (
        definition["name"],
        level + 1,
        cost,
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
    if name == "market":
        return _cmd_market(state, args)
    if name == "buy":
        return _cmd_buy(state, args)
    if name == "open":
        return _cmd_open(state, args)
    if name == "next":
        return _cmd_next(state, args)
    if name == "drinks":
        return _cmd_drinks(state, args)
    if name == "price":
        return _cmd_price(state, args)
    if name == "serve":
        return _cmd_serve(state, args, False)
    if name == "cheers":
        return _cmd_serve(state, args, True)
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
    if name == "upgrades":
        return _cmd_upgrades(state, args)
    if name == "upgrade":
        return _cmd_upgrade(state, args)
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
        "《万象酒馆》已建立空白档案（种子%d）。\n"
        "第一步由AI自己决定酒吧名与口味："
        'setup "酒吧名" 喜欢标签 [讨厌标签]。' % seed_value
    )


if __name__ == "__main__":
    print(_help())
