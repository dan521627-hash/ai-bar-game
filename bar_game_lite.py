"""《空杯俱乐部》生成式轻量版：只负责确定性数值，不负责讲故事。

AI 必须同时阅读 LIGHT_RULEBOOK.md；人物格式参考 LIGHT_EXAMPLE_CARDS.md。
本文件不包含角色、对白、酒单、商店、装修或剧情数据，也不访问网络。
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import zlib
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


VERSION = 1
SAVE_PATH = Path(__file__).with_name("bar_lite_save.json")
ARCHIVE_BEGIN = "【空杯轻量数值档案｜V1】"
ARCHIVE_END = "【数值档案结束】"
VIEWER_BASE_URL = "https://empty-glass-club-viewer.dan521627.chatgpt.site"
KINDS = {
    "beer",
    "wine",
    "sparkling",
    "sake",
    "gin",
    "vodka",
    "rum",
    "tequila",
    "whisky",
    "brandy",
    "liqueur",
    "baijiu",
    "nonalcoholic",
    "fantasy",
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _safe_id(value: str) -> str:
    result = re.sub(r"[^a-z0-9_:-]", "_", str(value).strip().lower()).strip("_")
    if not result or len(result) > 64:
        raise ValueError("ID必须是1～64位英文字母、数字、下划线、冒号或短横线。")
    return result


def _fresh_seed() -> int:
    return int.from_bytes(os.urandom(4), "big")


def _default_state(
    seed: int,
    cash: int = 460,
    owner_tolerance: float = 52,
    owner_absorption: float = 1.0,
) -> Dict[str, Any]:
    return {
        "version": VERSION,
        "seed": int(seed) & 0xFFFFFFFF,
        "rng": int(seed) & 0xFFFFFFFF,
        "turn": 0,
        "shift": 0,
        "cash": int(cash),
        "reputation": 50,
        "products": {},
        "recipes": {},
        "people": {
            "owner": {
                "tolerance": _clamp(owner_tolerance, 5, 95),
                "absorption": _clamp(owner_absorption, 0.5, 1.5),
                "intox": 0.0,
                "peak": 0.0,
                "units": 0.0,
            }
        },
        "ledger": [
            {
                "turn": 0,
                "amount": int(cash),
                "balance": int(cash),
                "reason": "启动资金",
                "kind": "capital",
            }
        ],
        "reviews": [],
        "cooldowns": {},
        "session": {
            "revenue": 0,
            "spend": 0,
            "served": 0,
            "owner_drinks": 0,
            "owner_self_loss": 0.0,
        },
    }


def _save(state: Dict[str, Any]) -> None:
    SAVE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _load() -> Dict[str, Any]:
    if not SAVE_PATH.exists():
        state = _default_state(_fresh_seed())
        _save(state)
        return state
    state = json.loads(SAVE_PATH.read_text(encoding="utf-8"))
    if state.get("version") != VERSION:
        raise ValueError("轻量数值存档版本不兼容。")
    return state


def _rand(state: Dict[str, Any]) -> float:
    value = (int(state["rng"]) * 1664525 + 1013904223) & 0xFFFFFFFF
    state["rng"] = value
    return value / 4294967296.0


def _money(
    state: Dict[str, Any], amount: int, reason: str, kind: str
) -> Dict[str, Any]:
    amount = int(amount)
    state["cash"] = int(state["cash"]) + amount
    state["ledger"].append(
        {
            "turn": int(state["turn"]),
            "amount": amount,
            "balance": int(state["cash"]),
            "reason": str(reason)[:160],
            "kind": kind,
        }
    )
    state["ledger"] = state["ledger"][-300:]
    if amount > 0:
        state["session"]["revenue"] += amount
    elif amount < 0:
        state["session"]["spend"] += -amount
    return {"cash": state["cash"], "change": amount, "reason": reason}


def new_game(
    seed: Optional[int] = None,
    cash: int = 460,
    owner_tolerance: float = 52,
    owner_absorption: float = 1.0,
) -> Dict[str, Any]:
    """建立纯数值档案；酒馆名称、人物和世界观由 AI 自己决定。"""
    seed_value = _fresh_seed() if seed is None else int(seed)
    state = _default_state(
        seed_value,
        cash=cash,
        owner_tolerance=owner_tolerance,
        owner_absorption=owner_absorption,
    )
    _save(state)
    return summary()


def summary() -> Dict[str, Any]:
    state = _load()
    return {
        "cash": state["cash"],
        "reputation": state["reputation"],
        "turn": state["turn"],
        "shift": state["shift"],
        "products": len(state["products"]),
        "recipes": len(state["recipes"]),
        "owner": dict(state["people"]["owner"]),
        "session": dict(state["session"]),
    }


def define_product(
    product_id: str,
    name: str,
    kind: str,
    bottle_ml: float,
    abv: float,
    bottle_cost: int,
) -> Dict[str, Any]:
    """AI创造商品后登记其数值；这里不判断品牌、来历或文案。"""
    state = _load()
    product_id = _safe_id(product_id)
    kind = str(kind).strip().lower()
    if kind not in KINDS:
        raise ValueError("未知酒类。可用种类：" + " ".join(sorted(KINDS)))
    bottle_ml = _clamp(bottle_ml, 50, 5000)
    abv = _clamp(abv, 0, 96)
    bottle_cost = int(_clamp(bottle_cost, 1, 1_000_000))
    existing_stock = float(state["products"].get(product_id, {}).get("stock_ml", 0))
    state["products"][product_id] = {
        "id": product_id,
        "name": str(name).strip()[:80] or product_id,
        "kind": kind,
        "bottle_ml": round(bottle_ml, 2),
        "abv": round(abv, 2),
        "bottle_cost": bottle_cost,
        "cost_per_ml": round(bottle_cost / bottle_ml, 6),
        "stock_ml": round(existing_stock, 2),
    }
    _save(state)
    return dict(state["products"][product_id])


def purchase(
    product_id: str,
    bottles: int = 1,
    total_cost: Optional[int] = None,
) -> Dict[str, Any]:
    """购入库存并真实扣款；允许资金变负以保留经营风险。"""
    state = _load()
    product_id = _safe_id(product_id)
    if product_id not in state["products"]:
        raise KeyError("商品尚未define_product。")
    bottles = int(_clamp(bottles, 1, 999))
    product = state["products"][product_id]
    cost = (
        int(total_cost)
        if total_cost is not None
        else int(product["bottle_cost"]) * bottles
    )
    if cost < 0:
        raise ValueError("进货成本不能为负数。")
    product["stock_ml"] = round(
        float(product["stock_ml"]) + float(product["bottle_ml"]) * bottles,
        2,
    )
    result = _money(state, -cost, "进货：" + product["name"], "stock")
    _save(state)
    return {**result, "product": product_id, "stock_ml": product["stock_ml"]}


def _normalize_components(
    state: Dict[str, Any], components: Dict[str, float]
) -> Dict[str, float]:
    if not isinstance(components, dict) or not components:
        raise ValueError("配方至少需要一种库存商品。")
    normalized: Dict[str, float] = {}
    for raw_id, raw_ml in components.items():
        product_id = _safe_id(raw_id)
        if product_id not in state["products"]:
            raise KeyError("配方引用了未登记商品：" + product_id)
        ml = _clamp(raw_ml, 0.5, 1000)
        normalized[product_id] = round(ml, 2)
    return normalized


def _recipe_profile(
    state: Dict[str, Any],
    components: Dict[str, float],
    dilution_ml: float,
) -> Dict[str, float]:
    dilution_ml = _clamp(dilution_ml, 0, 2000)
    liquid_ml = sum(components.values())
    pure_ml = sum(
        ml * float(state["products"][product_id]["abv"]) / 100
        for product_id, ml in components.items()
    )
    volume_ml = liquid_ml + dilution_ml
    abv = 0.0 if volume_ml <= 0 else pure_ml / volume_ml * 100
    ingredient_cost = sum(
        ml * float(state["products"][product_id]["cost_per_ml"])
        for product_id, ml in components.items()
    )
    return {
        "volume_ml": round(volume_ml, 1),
        "pure_alcohol_ml": round(pure_ml, 2),
        "abv": round(abv, 2),
        "alcohol_units": round(pure_ml / 10, 2),
        "ingredient_cost": round(ingredient_cost, 2),
    }


def define_recipe(
    recipe_id: str,
    name: str,
    components: Dict[str, float],
    dilution_ml: float,
    price: int,
) -> Dict[str, Any]:
    """登记AI原创或现实酒款；灵感、味道和故事留在AI记忆中。"""
    state = _load()
    recipe_id = _safe_id(recipe_id)
    normalized = _normalize_components(state, components)
    price = int(_clamp(price, 0, 1_000_000))
    profile = _recipe_profile(state, normalized, dilution_ml)
    state["recipes"][recipe_id] = {
        "id": recipe_id,
        "name": str(name).strip()[:100] or recipe_id,
        "components": normalized,
        "dilution_ml": round(_clamp(dilution_ml, 0, 2000), 2),
        "price": price,
        **profile,
    }
    _save(state)
    return dict(state["recipes"][recipe_id])


def recipe_profile(recipe_id: str) -> Dict[str, Any]:
    state = _load()
    recipe_id = _safe_id(recipe_id)
    if recipe_id not in state["recipes"]:
        raise KeyError("没有这张配方。")
    recipe = state["recipes"][recipe_id]
    current = _recipe_profile(
        state,
        dict(recipe["components"]),
        float(recipe["dilution_ml"]),
    )
    return {**recipe, **current}


def _consume(
    state: Dict[str, Any],
    recipe: Dict[str, Any],
    portions: int,
) -> float:
    portions = int(_clamp(portions, 1, 50))
    for product_id, ml in recipe["components"].items():
        required = float(ml) * portions
        if float(state["products"][product_id]["stock_ml"]) + 1e-9 < required:
            raise ValueError("库存不足：" + state["products"][product_id]["name"])
    cost = 0.0
    for product_id, ml in recipe["components"].items():
        product = state["products"][product_id]
        required = float(ml) * portions
        product["stock_ml"] = round(float(product["stock_ml"]) - required, 2)
        cost += required * float(product["cost_per_ml"])
    return round(cost, 2)


def register_person(
    person_id: str,
    tolerance: float = 50,
    absorption: float = 1.0,
) -> Dict[str, Any]:
    """只登记酒精相关数值，不保存人物姓名、台词或剧情。"""
    state = _load()
    person_id = _safe_id(person_id)
    previous = state["people"].get(person_id, {})
    state["people"][person_id] = {
        "tolerance": round(_clamp(tolerance, 5, 95), 2),
        "absorption": round(_clamp(absorption, 0.5, 1.5), 3),
        "intox": float(previous.get("intox", 0)),
        "peak": float(previous.get("peak", 0)),
        "units": float(previous.get("units", 0)),
    }
    _save(state)
    return dict(state["people"][person_id])


def _add_alcohol(
    state: Dict[str, Any],
    person_id: str,
    alcohol_units: float,
) -> Dict[str, Any]:
    if person_id not in state["people"]:
        state["people"][person_id] = {
            "tolerance": 50.0,
            "absorption": 1.0,
            "intox": 0.0,
            "peak": 0.0,
            "units": 0.0,
        }
    person = state["people"][person_id]
    tolerance = float(person["tolerance"])
    absorption = float(person["absorption"])
    sensitivity = _clamp((1.24 - tolerance / 130) * absorption, 0.25, 1.45)
    gain = float(alcohol_units) * 13.0 * sensitivity
    person["intox"] = round(_clamp(float(person["intox"]) + gain, 0, 100), 2)
    person["peak"] = max(float(person["peak"]), float(person["intox"]))
    person["units"] = round(float(person["units"]) + float(alcohol_units), 2)
    return {
        "person_id": person_id,
        "gain": round(gain, 2),
        "intox": person["intox"],
        "stage": intox_stage(person["intox"]),
    }


def serve(
    person_id: str,
    recipe_id: str,
    price: Optional[int] = None,
    tip: int = 0,
    portions: int = 1,
) -> Dict[str, Any]:
    """扣客人实际喝掉的库存、入账，并计算其醉度。"""
    state = _load()
    person_id = _safe_id(person_id)
    recipe_id = _safe_id(recipe_id)
    if recipe_id not in state["recipes"]:
        raise KeyError("没有这张配方。")
    recipe = state["recipes"][recipe_id]
    portions = int(_clamp(portions, 1, 50))
    cost = _consume(state, recipe, portions)
    unit_price = int(recipe["price"] if price is None else price)
    if unit_price < 0 or int(tip) < 0:
        raise ValueError("售价和小费不能为负数。")
    received = unit_price * portions + int(tip)
    _money(state, received, "售出：" + recipe["name"], "sale")
    state["session"]["served"] += portions
    intox = _add_alcohol(
        state,
        person_id,
        float(recipe["alcohol_units"]) * portions,
    )
    _save(state)
    return {
        "received": received,
        "allocated_ingredient_cost": cost,
        "gross_margin": round(received - cost, 2),
        "cash": state["cash"],
        "intox": intox,
    }


def owner_drink(recipe_id: str, portions: int = 1) -> Dict[str, Any]:
    """老板自饮真实扣库存，不产生收入，并单列损耗。"""
    state = _load()
    recipe_id = _safe_id(recipe_id)
    if recipe_id not in state["recipes"]:
        raise KeyError("没有这张配方。")
    recipe = state["recipes"][recipe_id]
    portions = int(_clamp(portions, 1, 20))
    cost = _consume(state, recipe, portions)
    state["session"]["owner_drinks"] += portions
    state["session"]["owner_self_loss"] = round(
        float(state["session"]["owner_self_loss"]) + cost,
        2,
    )
    intox = _add_alcohol(
        state,
        "owner",
        float(recipe["alcohol_units"]) * portions,
    )
    _save(state)
    return {"inventory_loss": cost, "intox": intox}


def score_drink(
    taste_hits: int,
    dislike_hits: int,
    request_hits: int,
    price: int,
    budget: int,
    attempts: int = 0,
    service_bonus: int = 0,
) -> Dict[str, int]:
    """AI判断语义命中数量；脚本只把输入转换为统一评分。"""
    score = 52
    score += int(taste_hits) * 10
    score -= int(dislike_hits) * 18
    score += int(request_hits) * 14
    score += min(max(int(attempts), 0), 2) * 3
    score += int(service_bonus)
    if int(price) > int(budget):
        score -= min(32, 8 + (int(price) - int(budget)) // 3)
    score = int(_clamp(score, 0, 100))
    return {"score": score, "stars": stars(score)}


def stars(score: float) -> int:
    score = _clamp(score, 0, 100)
    if score >= 88:
        return 5
    if score >= 72:
        return 4
    if score >= 55:
        return 3
    if score >= 38:
        return 2
    return 1


def record_review(
    person_id: str,
    recipe_id: str,
    score: int,
    paid: int,
) -> Dict[str, Any]:
    """只保存评分数字；评价文字由AI写进自己的记忆图鉴。"""
    state = _load()
    review = {
        "turn": int(state["turn"]),
        "person_id": _safe_id(person_id),
        "recipe_id": _safe_id(recipe_id),
        "score": int(_clamp(score, 0, 100)),
        "stars": stars(score),
        "paid": max(0, int(paid)),
    }
    state["reviews"].append(review)
    state["reviews"] = state["reviews"][-200:]
    reputation_delta = {1: -4, 2: -2, 3: 0, 4: 1, 5: 2}[review["stars"]]
    state["reputation"] = int(
        _clamp(int(state["reputation"]) + reputation_delta, 0, 100)
    )
    _save(state)
    return {**review, "reputation": state["reputation"]}


def intox_stage(value: float) -> str:
    value = _clamp(value, 0, 100)
    if value < 8:
        return "清醒"
    if value < 22:
        return "暖意"
    if value < 42:
        return "微醺"
    if value < 64:
        return "醉酒"
    return "重醉"


def advance_turn(
    turns: int = 1,
    person_ids: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """推进对话或场景回合，并让醉度逐轮自然消退。"""
    state = _load()
    turns = int(_clamp(turns, 1, 100))
    selected = (
        [_safe_id(value) for value in person_ids]
        if person_ids is not None
        else list(state["people"])
    )
    state["turn"] += turns
    people_result = {}
    for person_id in selected:
        if person_id not in state["people"]:
            continue
        person = state["people"][person_id]
        decay = (2.2 + float(person["tolerance"]) * 0.024) * turns
        person["intox"] = round(
            _clamp(float(person["intox"]) - decay, 0, 100),
            2,
        )
        people_result[person_id] = {
            "intox": person["intox"],
            "stage": intox_stage(person["intox"]),
            "decay": round(decay, 2),
        }
    _save(state)
    return {"turn": state["turn"], "people": people_result}


def conversation_turn(person_id: str = "owner") -> Dict[str, Any]:
    """离店后每轮调用一次；规则书决定AI如何把阶段演成语言与动作。"""
    result = advance_turn(1, [person_id])
    return result["people"].get(
        _safe_id(person_id),
        {"intox": 0.0, "stage": "清醒", "decay": 0.0},
    )


def roll_event(
    event_key: str,
    chance: float,
    cooldown_turns: int = 0,
    modifier: float = 0.0,
) -> Dict[str, Any]:
    """只决定事件是否触发；事件内容及演绎由AI负责。"""
    state = _load()
    event_key = _safe_id(event_key)
    current_turn = int(state["turn"])
    ready_turn = int(state["cooldowns"].get(event_key, -1))
    if current_turn < ready_turn:
        return {
            "triggered": False,
            "reason": "cooldown",
            "ready_turn": ready_turn,
        }
    final_chance = _clamp(float(chance) + float(modifier), 0, 1)
    roll = _rand(state)
    triggered = roll < final_chance
    if triggered and int(cooldown_turns) > 0:
        state["cooldowns"][event_key] = current_turn + int(cooldown_turns)
    _save(state)
    return {
        "triggered": triggered,
        "roll": round(roll, 5),
        "chance": round(final_chance, 5),
        "ready_turn": state["cooldowns"].get(event_key, current_turn),
    }


def spend(amount: int, reason: str) -> Dict[str, Any]:
    state = _load()
    amount = max(0, int(amount))
    result = _money(state, -amount, reason, "spend")
    _save(state)
    return result


def earn(amount: int, reason: str) -> Dict[str, Any]:
    state = _load()
    amount = max(0, int(amount))
    result = _money(state, amount, reason, "income")
    _save(state)
    return result


def close_shift(fixed_cost: int = 52) -> Dict[str, Any]:
    """结算一次营业；故事总结由AI另写，数值报告由这里生成。"""
    state = _load()
    before = dict(state["session"])
    _money(state, -max(0, int(fixed_cost)), "固定营业成本", "fixed_cost")
    state["shift"] += 1
    result = {
        "shift": state["shift"],
        "cash": state["cash"],
        "reputation": state["reputation"],
        "revenue": before["revenue"],
        "spend_before_fixed_cost": before["spend"],
        "fixed_cost": max(0, int(fixed_cost)),
        "served": before["served"],
        "owner_drinks": before["owner_drinks"],
        "owner_self_loss": before["owner_self_loss"],
        "profit_before_inventory_accounting": (
            before["revenue"] - before["spend"] - max(0, int(fixed_cost))
        ),
    }
    state["session"] = {
        "revenue": 0,
        "spend": 0,
        "served": 0,
        "owner_drinks": 0,
        "owner_self_loss": 0.0,
    }
    _save(state)
    return result


def export_archive() -> str:
    """导出严格数值档案；AI的叙事记忆应按规则书另附在后面。"""
    state = _load()
    raw = json.dumps(
        state,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    checksum = hashlib.sha256(raw).hexdigest()
    payload = base64.urlsafe_b64encode(zlib.compress(raw, 9)).decode("ascii")
    return "\n".join([ARCHIVE_BEGIN, "sha256=" + checksum, payload, ARCHIVE_END])


def restore_archive(archive_text: str) -> Dict[str, Any]:
    lines = [line.strip() for line in str(archive_text).splitlines() if line.strip()]
    if (
        len(lines) != 4
        or lines[0] != ARCHIVE_BEGIN
        or lines[-1] != ARCHIVE_END
        or not lines[1].startswith("sha256=")
    ):
        raise ValueError("拒绝读取：数值档案格式不正确。")
    raw = zlib.decompress(base64.urlsafe_b64decode(lines[2].encode("ascii")))
    if hashlib.sha256(raw).hexdigest() != lines[1].split("=", 1)[1]:
        raise ValueError("拒绝读取：数值档案校验失败。")
    state = json.loads(raw.decode("utf-8"))
    required = {
        "version",
        "cash",
        "products",
        "recipes",
        "people",
        "ledger",
        "rng",
    }
    if state.get("version") != VERSION or not required.issubset(state):
        raise ValueError("拒绝读取：数值档案缺少必要字段。")
    _save(state)
    return summary()


def viewer_link(snapshot: Optional[Dict[str, Any]] = None) -> str:
    """把AI提供的精简叙事快照与真实数值合成只读观察链接。"""
    state = _load()
    view = dict(snapshot or {})
    view.update(
        {
            "v": 1,
            "cash": state["cash"],
            "reputation": state["reputation"],
            "updated_turn": state["turn"],
            "owner_intox": state["people"]["owner"]["intox"],
            "owner_level": intox_stage(state["people"]["owner"]["intox"]),
            "owner_self_servings": state["session"]["owner_drinks"],
            "owner_self_loss": state["session"]["owner_self_loss"],
            "inventory": [
                {
                    "name": product["name"],
                    "remaining": round(float(product["stock_ml"]), 1),
                    "edition": product["kind"],
                }
                for product in state["products"].values()
                if float(product["stock_ml"]) > 0
            ][:12],
            "inventory_count": sum(
                float(product["stock_ml"]) > 0
                for product in state["products"].values()
            ),
        }
    )
    raw = json.dumps(view, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    payload = base64.urlsafe_b64encode(zlib.compress(raw, 9)).decode("ascii")
    return VIEWER_BASE_URL + "/#bar=" + payload.rstrip("=")


def start() -> str:
    return (
        "生成式轻量版数值层已就绪。请先阅读 LIGHT_RULEBOOK.md 和 "
        "LIGHT_EXAMPLE_CARDS.md，再调用 new_game()。本脚本不会生成剧情。"
    )


if __name__ == "__main__":
    print(start())
