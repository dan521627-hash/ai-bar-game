import unittest
import importlib.util
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

import bar_game


class SetupAndShopTests(unittest.TestCase):
    def test_setup_accepts_space_separated_likes(self):
        state = bar_game._default_state(7)
        result = bar_game._cmd_setup(
            state,
            ["树洞酒馆", "sweet", "floral", "fruity", "crisp"],
        )
        self.assertIn("树洞酒馆", result)
        self.assertEqual(
            state["owner_likes"],
            ["sweet", "floral", "fruity", "crisp"],
        )
        self.assertEqual(state["owner_dislikes"], [])

    def test_setup_accepts_brackets_and_named_groups(self):
        variants = [
            ["树洞酒馆", "sweet", "floral", "[smoky", "bitter]"],
            [
                "树洞酒馆",
                "like=sweet,floral",
                "avoid=smoky,bitter",
            ],
            ["树洞酒馆", "sweet,floral", "smoky,bitter"],
        ]
        for args in variants:
            with self.subTest(args=args):
                state = bar_game._default_state(7)
                bar_game._cmd_setup(state, args)
                self.assertEqual(state["owner_likes"], ["sweet", "floral"])
                self.assertEqual(state["owner_dislikes"], ["smoky", "bitter"])

    def test_numeric_shop_id_defaults_to_permanent_shop(self):
        state = bar_game._default_state(9)
        bar_game._refresh_market(state, starter=True)
        state["phase"] = "stocking"
        result = bar_game._cmd_buy(state, ["1"])
        self.assertIn("购入", result)
        self.assertTrue(state["inventory"])


class InteractionTests(unittest.TestCase):
    def test_conflict_is_exception_not_default_for_pairs(self):
        counts = Counter()
        samples = 3000
        for seed in range(1, samples + 1):
            state = bar_game._default_state(seed)
            state["visit"] = 1
            bar_game._spawn_scene(state, force=True)
            if len(state.get("active_guests", [])) != 2:
                continue
            counts["pairs"] += 1
            interaction = state.get("interaction")
            if not interaction:
                counts["coexist"] += 1
                continue
            if interaction["kind"] in bar_game._CONFLICT_INTERACTION_KINDS:
                counts["conflicts"] += 1
            else:
                counts["social"] += 1

        self.assertGreater(counts["pairs"], 250)
        self.assertGreater(counts["coexist"] + counts["social"], counts["conflicts"] * 10)
        self.assertLess(counts["conflicts"] / counts["pairs"], 0.08)

    def test_recent_conflict_forces_a_cooldown(self):
        cards = bar_game.BUILTIN_GUESTS[:2]
        for seed in range(1, 300):
            state = bar_game._default_state(seed)
            state["visit"] = 5
            state["last_conflict_visit"] = 5
            bar_game._start_interaction(state, cards[0], cards[1])
            interaction = state.get("interaction")
            if interaction:
                self.assertNotIn(
                    interaction["kind"],
                    bar_game._CONFLICT_INTERACTION_KINDS,
                )

    def test_stage_increases_company_not_conflict_wording(self):
        self.assertIn("不直接增加冲突", bar_game.UPGRADE_DEFS["stage"]["desc"])

    def test_later_guests_can_join_without_clearing_the_first_wave(self):
        state = bar_game._default_state(260)
        state["visit"] = 3
        first_text = bar_game._spawn_scene(state, force=True)
        first_ids = {guest["id"] for guest in state["active_guests"]}
        self.assertTrue(first_ids)
        for guest in state["active_guests"]:
            guest["served"] = True
            guest["closed"] = True
        state["interaction"] = None
        later_text = bar_game._spawn_scene(state, join_existing=True)
        later_ids = {guest["id"] for guest in state["active_guests"]}
        self.assertTrue(first_ids.issubset(later_ids))
        self.assertGreater(len(later_ids), len(first_ids))
        self.assertIn("营业中途又有人推门", later_text)
        self.assertIn("制作流水线", first_text)

    def test_known_companions_can_arrive_as_a_party(self):
        found_party = False
        for seed in range(1, 1200):
            state = bar_game._default_state(seed)
            state["visit"] = 4
            text = bar_game._spawn_scene(state, force=True)
            ids = {guest["id"] for guest in state["active_guests"]}
            if len(ids) < 3 or "一伙本来就认识" not in text:
                continue
            self.assertTrue(
                any(ids.issubset(set(group)) for group in bar_game.GUEST_COMPANION_GROUPS)
            )
            self.assertIn("一起看酒单", text)
            found_party = True
            break
        self.assertTrue(found_party, "应能抽到原作熟人结伴到店")


class WorldBreadthTests(unittest.TestCase):
    def test_ninja_world_and_cross_world_upgrades_exist(self):
        names = {card["name"] for card in bar_game.BUILTIN_GUESTS}
        for name in ("成年后的漩涡鸣人", "成年后的日向雏田", "宇智波斑", "长门"):
            self.assertIn(name, names)
        for name in (
            "张楚岚",
            "冯宝宝",
            "王也",
            "伍六七",
            "坂田银时",
            "芙莉莲",
            "成年后的魏无羡",
            "成年后的郭靖",
        ):
            self.assertIn(name, names)
        for upgrade_id in (
            "translator",
            "guestbook",
            "safety_ward",
            "adaptive_ambience",
        ):
            self.assertIn(upgrade_id, bar_game.UPGRADE_DEFS)

    def test_season_time_and_weather_are_not_a_fixed_cycle(self):
        state = bar_game._default_state(2026)
        seasons = []
        opening_times = []
        weathers = []
        for _ in range(16):
            bar_game._advance_calendar(state)
            seasons.append(state["season"])
            opening_times.append(state["opening_time"])
            weathers.append(state["weather"])

        self.assertGreaterEqual(len(set(seasons)), 3)
        self.assertTrue(
            all(
                opening_times[index] != opening_times[index - 1]
                for index in range(1, len(opening_times))
            )
        )
        self.assertTrue(
            all(
                weathers[index] != weathers[index - 1]
                for index in range(1, len(weathers))
            )
        )

    def test_viewer_snapshot_includes_owner_drinks_and_body_state(self):
        state = bar_game._default_state(41)
        state["session"]["owner_drinks"] = ["长安酸", "黄油啤酒（与用户共饮）"]
        state["session"]["owner_self_servings"] = 2
        state["session"]["owner_self_liquid_loss"] = 11
        state["session"]["owner_self_service_loss"] = 5
        snapshot = bar_game._viewer_snapshot(state)

        self.assertEqual(snapshot["owner_drinks"], state["session"]["owner_drinks"])
        self.assertEqual(snapshot["owner_self_servings"], 2)
        self.assertEqual(snapshot["owner_self_loss"], 16)
        self.assertTrue(snapshot["owner_body"])


class NpcIntoxicationTests(unittest.TestCase):
    def test_npc_intoxication_has_distinct_stages(self):
        self.assertEqual(bar_game._npc_intox_stage(0), ("清醒", 0))
        self.assertEqual(bar_game._npc_intox_stage(22), ("微醺", 2))
        self.assertEqual(bar_game._npc_intox_stage(42), ("醉酒", 3))
        self.assertEqual(bar_game._npc_intox_stage(64), ("重醉", 4))

    def test_drunk_directive_requires_visible_character_specific_changes(self):
        state = bar_game._default_state(73)
        card = {
            "id": "quiet_test",
            "name": "沉默客",
            "origin": "测试世界",
            "temperament": "寡言、克制、警觉",
            "ethos": "memory",
        }
        active = {"npc_drunk": 48.0}
        directive = bar_game._npc_intox_directive(state, card, active)
        self.assertIn("醉酒（48.0/100）", directive)
        self.assertIn("克制失守型", directive)
        self.assertIn("至少落实两项变化", directive)
        self.assertIn("不得原样念给用户", directive)


class DynamicGuestTests(unittest.TestCase):
    def test_ai_guest_is_saved_once_and_reused_as_a_returning_candidate(self):
        with TemporaryDirectory() as directory:
            previous_path = bar_game.SAVE_PATH
            bar_game.SAVE_PATH = Path(directory) / "bar_save.json"
            try:
                bar_game.new_game(808)
                card = {
                    "name": "测试星际旅人",
                    "origin": "第九卫星·外星来客",
                    "adult": True,
                    "temperament": "谨慎、好奇，不把沉默误解为敌意",
                    "ethos": "理解陌生文明",
                    "canon_anchor": "成年外交员；通过气味记忆航线，不饮用会腐蚀硅基组织的溶剂。",
                }
                first = bar_game.register_guest(card)
                second = bar_game.register_guest(card)
                self.assertIn("已加入本酒馆", first)
                self.assertIn("没有新建重复卡", second)
                state = bar_game._load()
                self.assertEqual(len(state["custom_guests"]), 1)
                self.assertTrue(state["custom_guests"][0]["created_by_ai"])
            finally:
                bar_game.SAVE_PATH = previous_path

    def test_guest_creation_prompt_describes_an_unbounded_world(self):
        with TemporaryDirectory() as directory:
            previous_path = bar_game.SAVE_PATH
            bar_game.SAVE_PATH = Path(directory) / "bar_save.json"
            try:
                bar_game.new_game(809)
                prompt = bar_game.guest_creation_prompt()
                self.assertIn("范围没有世界、物种、维度或媒介限制", prompt)
                self.assertIn("register_guest", prompt)
                self.assertIn("检索现有图鉴", prompt)
            finally:
                bar_game.SAVE_PATH = previous_path

    def test_lite_version_is_self_contained_and_offline(self):
        launcher_path = Path(__file__).with_name("bar_game_lite.py")
        spec = importlib.util.spec_from_file_location("lite_import_test", launcher_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = launcher_path.read_text(encoding="utf-8")
        self.assertNotIn("CORE_URL", source)
        self.assertNotIn("urlopen", source)
        self.assertEqual(len(module.BUILTIN_GUESTS), 24)
        for name in (
            "start",
            "new_game",
            "cmd",
            "viewer_link",
            "guest_creation_prompt",
            "register_guest",
        ):
            self.assertTrue(callable(getattr(module, name, None)), name)


if __name__ == "__main__":
    unittest.main()
