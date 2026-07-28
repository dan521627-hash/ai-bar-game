"""《空杯俱乐部》轻量运行版。

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
CORE_SHA256 = "ed457c0f4961a7f9b8116437191443040e882d5e12e192193778d63efae8118c"
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
            "轻量版载入失败：%s\n"
            "当前环境若不能联网，请改用完整版 bar_game.py。" % exc
        )
    return (
        "《空杯俱乐部》轻量运行版已就绪：完整经营玩法、24位示例人物、"
        "AI动态人物创建均可用。新酒馆调用 new_game()；"
        "想补齐预置人物时再运行 bar_character_pack.py。"
    )


if __name__ == "__main__":
    print(start())
