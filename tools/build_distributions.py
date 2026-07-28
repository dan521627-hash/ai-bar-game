"""从完整版生成真正独立的轻量运行版与可选角色扩展卡。"""

from __future__ import annotations

import importlib.util
import pprint
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FULL_PATH = ROOT / "bar_game.py"
LITE_PATH = ROOT / "bar_game_lite.py"
PACK_PATH = ROOT / "bar_character_pack.py"

SAMPLE_IDS = {
    "li_bai",
    "cleopatra",
    "ada_lovelace",
    "ibn_sina",
    "loki_myth",
    "chang_e",
    "fox_spirit",
    "unit_7",
    "ordinary_teacher",
    "su_shi",
    "wu_zetian",
    "sun_wukong",
    "athena",
    "alice",
    "sherlock_holmes",
    "mulan_legend",
    "alien_beekeeper",
    "harry_potter_adult",
    "monkey_d_luffy",
    "naruto_adult",
    "tony_stark",
    "zhang_chulan",
    "frieren",
    "zhongli",
}


def _load_full_module():
    spec = importlib.util.spec_from_file_location("bar_game_distribution_source", FULL_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法读取完整版。")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _render_cards(cards):
    return pprint.pformat(cards, width=100, sort_dicts=False)


def build() -> None:
    module = _load_full_module()
    all_cards = list(module.BUILTIN_GUESTS)
    samples = [card for card in all_cards if card["id"] in SAMPLE_IDS]
    expansion = [card for card in all_cards if card["id"] not in SAMPLE_IDS]
    if len(samples) != len(SAMPLE_IDS):
        missing = sorted(SAMPLE_IDS - {card["id"] for card in samples})
        raise RuntimeError("轻量示例人物缺失：" + "、".join(missing))

    source = FULL_PATH.read_text(encoding="utf-8")
    catalog_start = source.index("BUILTIN_GUESTS: List[Dict[str, Any]] = [")
    catalog_end = source.index("\ndef _clamp(", catalog_start)
    lite_catalog = """BUILTIN_GUESTS: List[Dict[str, Any]] = %s


def _catalog_tastes(identifier: str) -> Tuple[List[str], List[str]]:
    keys = list(TAGS)
    value = sum((index + 1) * ord(char) for index, char in enumerate(identifier))
    likes: List[str] = []
    cursor = value %% len(keys)
    while len(likes) < 3:
        tag = keys[cursor %% len(keys)]
        if tag not in likes:
            likes.append(tag)
        cursor += 5
    dislike = keys[(value // 7 + 3) %% len(keys)]
    while dislike in likes:
        dislike = keys[(keys.index(dislike) + 1) %% len(keys)]
    return likes, [dislike]

""" % _render_cards(samples)
    lite_source = source[:catalog_start] + lite_catalog + source[catalog_end + 1 :]
    lite_source = lite_source.replace(
        "《空杯俱乐部》：给 AI 玩的零依赖文字酒吧游戏。",
        "《空杯俱乐部》轻量运行版：离线完整玩法、24位示例人物与 AI 动态扩展。",
        1,
    )
    main_marker = '\nif __name__ == "__main__":\n    print(_help())\n'
    start_block = '''

def start() -> str:
    """兼容旧轻量启动方式；本文件已经自带全部轻量核心，无需联网。"""
    return (
        "《空杯俱乐部》离线轻量版已就绪：完整经营玩法、24位示例人物、"
        "AI动态人物创建均可用。新酒馆调用 new_game()；"
        "想补齐预置人物时再运行 bar_character_pack.py。"
    )


if __name__ == "__main__":
    print(start())
    print(_help())
'''
    if main_marker not in lite_source:
        raise RuntimeError("找不到轻量版主入口。")
    lite_source = lite_source.replace(main_marker, start_block, 1)
    LITE_PATH.write_text(lite_source, encoding="utf-8", newline="\n")

    pack_source = '''"""《空杯俱乐部》角色扩展卡。

可选文件：与 bar_game_lite.py 放在同一文件夹后运行本文件，
即可把完整版人物池补入当前酒馆。它不会覆盖存档，也不会建立重复人物卡。
"""

from __future__ import annotations

CHARACTER_CARDS = %s


def install() -> str:
    import bar_game_lite as game

    status = game.start()
    if not callable(getattr(game, "register_guests", None)):
        return status
    return status + "\\n" + game.register_guests(CHARACTER_CARDS)


if __name__ == "__main__":
    print(install())
''' % _render_cards(expansion)
    PACK_PATH.write_text(pack_source, encoding="utf-8", newline="\n")
    print(
        "generated full=%d lite=%d pack=%d"
        % (len(all_cards), len(samples), len(expansion))
    )


if __name__ == "__main__":
    build()
