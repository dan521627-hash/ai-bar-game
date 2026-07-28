"""《空杯俱乐部》低 token 启动器。

给 AI 的执行约定：
1. 不要通读、复述或自行改写完整版源码。
2. 首次运行先调用 start()，把它返回的两个选项原样交给用户。
3. 只有用户作出选择后，才调用 start("light") 或 start("full")。
4. 加载成功后，玩法与完整版完全相同；新酒馆调用 new_game()。

light：只在 Python 内存中载入完整游戏，推荐，少占 AI 上下文。
full：同时在本地保存一份完整源码，适合需要离线复用或检查源码的环境。
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.request import Request, urlopen


GAME_URL = "https://empty-glass-club-viewer.dan521627.chatgpt.site/bar_game.py"
GAME_SHA256 = "b51e5c717d9f5b6adce6a2c21ae9ae8e45e0878d24c0a385fc03fdecceeb089c"
FULL_FILENAME = "bar_game_full.py"

CHOICE_PROMPT = """开始前请让用户选择：

1. 轻量模式（推荐）
   完整玩法与全部内容都会保留，但 AI 不需要通读庞大源码，通常更省 token。
   首次载入需要当前 Python 环境能够联网。

2. 完整模式
   玩法相同，同时保存完整源码，适合离线复用、源码检查或不能长期联网的环境。
   首次载入仍需联网；也可以直接下载完整版文件。

请不要替用户选择。用户回答后，调用 start("light") 或 start("full")。"""

_RUNTIME: Optional[Dict[str, Any]] = None
_PUBLIC_API = (
    "new_game",
    "cmd",
    "write_archive",
    "restore_archive",
    "viewer_link",
    "conversation_turn",
    "register_guest",
)


def _download_game() -> bytes:
    request = Request(
        GAME_URL,
        headers={"User-Agent": "Empty-Glass-Club-Lite/1.0"},
    )
    with urlopen(request, timeout=30) as response:
        payload = response.read()

    actual_hash = hashlib.sha256(payload).hexdigest()
    if actual_hash != GAME_SHA256:
        raise RuntimeError(
            "完整版校验失败，为保护存档已停止运行。请从酒馆网页重新下载最新版启动器。"
        )
    return payload


def _install_runtime(save_full_source: bool) -> None:
    global _RUNTIME
    if _RUNTIME is not None:
        return

    payload = _download_game()
    launcher_path = Path(__file__).resolve()
    engine_path = launcher_path.with_name(FULL_FILENAME if save_full_source else "bar_game.py")
    if save_full_source:
        engine_path.write_bytes(payload)

    namespace: Dict[str, Any] = {
        "__name__": "empty_glass_club_runtime",
        "__file__": str(engine_path),
        "__package__": None,
    }
    exec(compile(payload, GAME_URL, "exec"), namespace)

    missing = [name for name in _PUBLIC_API if not callable(namespace.get(name))]
    if missing:
        raise RuntimeError("完整版缺少必要接口：" + "、".join(missing))

    _RUNTIME = namespace
    globals().update({name: namespace[name] for name in _PUBLIC_API})


def start(mode: Optional[str] = None) -> str:
    """先询问用户，再按用户选择载入完整游戏。"""
    if mode is None or not str(mode).strip():
        return CHOICE_PROMPT

    normalized = str(mode).strip().lower()
    light_aliases = {"1", "light", "lite", "轻量", "轻量模式", "省token", "省 token"}
    full_aliases = {"2", "full", "完整", "完整模式", "完整版"}

    if normalized in light_aliases:
        save_full_source = False
        mode_name = "轻量模式"
    elif normalized in full_aliases:
        save_full_source = True
        mode_name = "完整模式"
    else:
        return "没有识别这个选择。\n\n" + CHOICE_PROMPT

    try:
        _install_runtime(save_full_source)
    except Exception as exc:
        return (
            "载入失败：%s\n"
            "可以改用完整版直链：%s"
            % (exc, GAME_URL)
        )

    extra = (
        "完整源码已保存为 %s。" % FULL_FILENAME
        if save_full_source
        else "完整源码仅由 Python 在后台载入，没有塞进 AI 的对话上下文。"
    )
    return (
        "《空杯俱乐部》%s已就绪，玩法与内容均未删减。%s\n"
        "若要建立新酒馆，请调用 new_game()；若已有同目录存档，请先调用 cmd(\"status\")。"
        % (mode_name, extra)
    )


if __name__ == "__main__":
    print(CHOICE_PROMPT)
