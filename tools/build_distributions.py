"""从完整版生成真正独立的轻量运行版与可选角色扩展卡。"""

from __future__ import annotations

import importlib.util
import hashlib
import pprint
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FULL_PATH = ROOT / "bar_game.py"
CORE_PATH = ROOT / "bar_game_core.py"
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
        "《空杯俱乐部》轻量运行版：完整玩法、少量示例人物与 AI 动态扩展。",
        1,
    )
    CORE_PATH.write_text(lite_source, encoding="utf-8", newline="\n")
    core_hash = hashlib.sha256(CORE_PATH.read_bytes()).hexdigest()

    launcher_source = '''"""《空杯俱乐部》轻量运行版。

给执行 AI：
- 这是推荐入口，只负责校验并在后台载入轻量核心，不要通读或复述远程源码。
- 它保留完整经营玩法，内置少量跨世界示例人物，并允许 AI 按规则无限发现新人物。
- 若当前环境不能联网，改用 bar_game.py 完整版；若想要全部预置人物，再安装角色扩展卡。
- 请根据自己的运行环境与 token 情况自行选择合适版本，不要把三份文件全部读完后再选择。
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.request import Request, urlopen


CORE_URL = "https://empty-glass-club-viewer.dan521627.chatgpt.site/bar_game_core.py"
CORE_SHA256 = "%s"
_RUNTIME: Optional[Dict[str, Any]] = None
_PUBLIC_API = (
    "new_game", "cmd", "write_archive", "restore_archive", "viewer_link",
    "conversation_turn", "guest_creation_prompt", "register_guest", "register_guests",
)


def _load() -> None:
    global _RUNTIME
    if _RUNTIME is not None:
        return
    request = Request(CORE_URL, headers={"User-Agent": "Empty-Glass-Club-Lite/2.0"})
    with urlopen(request, timeout=30) as response:
        payload = response.read()
    if hashlib.sha256(payload).hexdigest() != CORE_SHA256:
        raise RuntimeError("轻量核心校验失败，请重新下载最新版轻量运行版。")
    namespace: Dict[str, Any] = {
        "__name__": "empty_glass_club_lite_runtime",
        "__file__": str(Path(__file__).resolve().with_name("bar_game_core.py")),
        "__package__": None,
    }
    exec(compile(payload, CORE_URL, "exec"), namespace)
    missing = [name for name in _PUBLIC_API if not callable(namespace.get(name))]
    if missing:
        raise RuntimeError("轻量核心缺少必要接口：" + "、".join(missing))
    _RUNTIME = namespace
    globals().update({name: namespace[name] for name in _PUBLIC_API})


def start() -> str:
    """载入轻量核心；AI可根据环境自行改用完整版或可选角色包。"""
    try:
        _load()
    except Exception as exc:
        return (
            "轻量版载入失败：%%s\\n"
            "当前环境若不能联网，请改用完整版 bar_game.py。" %% exc
        )
    return (
        "《空杯俱乐部》轻量运行版已就绪：完整经营玩法、24位示例人物、"
        "AI动态人物创建均可用。新酒馆调用 new_game()；"
        "想补齐预置人物时再运行 bar_character_pack.py。"
    )


if __name__ == "__main__":
    print(start())
''' % core_hash
    LITE_PATH.write_text(launcher_source, encoding="utf-8", newline="\n")

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
