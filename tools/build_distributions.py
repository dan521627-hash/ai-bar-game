"""从完整版生成可选预制角色资料包。

生成式轻量版绝不能由本工具从完整版截取；它是手工维护的规则书、
示例卡和薄计算层。
"""

from __future__ import annotations

import importlib.util
import pprint
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FULL_PATH = ROOT / "bar_game.py"
PACK_PATH = ROOT / "bar_character_pack.py"


def _load_full_module():
    spec = importlib.util.spec_from_file_location("bar_game_distribution_source", FULL_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法读取完整版。")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build() -> None:
    cards = list(_load_full_module().BUILTIN_GUESTS)
    rendered = pprint.pformat(cards, width=100, sort_dicts=False)
    source = '''"""《空杯俱乐部》可选预制角色资料包。

包含完整版的全部预制人物，供想要稳定人物池的 AI 查阅。
生成式轻量版不需要它；加载它会增加上下文成本。
本文件只是数据，不会改存档、联网或自动执行游戏。
"""

from __future__ import annotations

CHARACTER_CARDS = %s
''' % rendered
    PACK_PATH.write_text(source, encoding="utf-8", newline="\n")
    print("generated character_pack=%d; lightweight files untouched" % len(cards))


if __name__ == "__main__":
    build()
