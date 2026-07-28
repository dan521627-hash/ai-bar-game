import unittest
import importlib.util
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

import bar_game


class SetupAndShopTests(unittest.TestCase):
    def test_readme_requires_owner_to_choose_exactly_one_version(self):
        readme = Path(__file__).with_name("README.md").read_text(encoding="utf-8")
        self.assertIn("执行AI必须先让主人选择版本", readme)
        self.assertIn("你想选择完整版，还是生成式轻量版？", readme)
        self.assertIn("禁止同时读取两版", readme)
        self.assertIn("已经明确指定版本", readme)

    def test_batch_separator_ignores_semicolon_inside_quotes(self):
        command = 'talk guest "first clause; second clause"; status'
        self.assertEqual(
            bar_game._split_command_segments(command),
            ['talk guest "first clause; second clause"', "status"],
        )

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

    def test_closed_report_uses_the_last_completed_session(self):
        state = bar_game._default_state(19)
        state["phase"] = "open"
        state["bar_name"] = "测试酒馆"
        state["session"]["opening_time"] = "深夜23:00"
        state["session"]["weather"] = "雨"
        state["session"]["revenue"] = 80
        state["session"]["spend"] = 260
        state["session"]["owner_drinks"] = ["测试酒"]
        result = bar_game._cmd_leave(state, [])
        self.assertIn("固定营业成本", result)
        report = bar_game._cmd_report(state, [])
        self.assertIn("【上次经营简报】", report)
        self.assertIn("收入80点", report)
        self.assertIn("我喝过：测试酒", report)


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

    def test_lite_version_is_a_thin_offline_numeric_layer(self):
        launcher_path = Path(__file__).with_name("bar_game_lite.py")
        spec = importlib.util.spec_from_file_location("lite_import_test", launcher_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = launcher_path.read_text(encoding="utf-8")
        self.assertNotIn("CORE_URL", source)
        self.assertNotIn("urlopen", source)
        self.assertNotIn("BUILTIN_GUESTS", source)
        self.assertLess(launcher_path.stat().st_size, 80_000)
        guide = module.start()
        self.assertIn("功能完整性清单", guide)
        self.assertIn("示例1：历史人物", guide)
        self.assertIn("没有世界、作品、物种、时代、空间或维度白名单", guide)
        for name in (
            "start",
            "new_game",
            "define_product",
            "purchase",
            "define_recipe",
            "serve",
            "quote_decision",
            "owner_drink",
            "take_loan",
            "repay_loan",
            "score_drink",
            "roll_event",
            "viewer_link",
            "export_archive",
            "restore_archive",
        ):
            self.assertTrue(callable(getattr(module, name, None)), name)

    def test_lite_numeric_flow_and_archive(self):
        launcher_path = Path(__file__).with_name("bar_game_lite.py")
        spec = importlib.util.spec_from_file_location("lite_numeric_test", launcher_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with TemporaryDirectory() as directory:
            module.SAVE_PATH = Path(directory) / "lite.json"
            module.new_game(17, cash=1000)
            module.define_product("gin", "金酒", "gin", 700, 40, 140)
            module.define_product("liqueur", "利口酒", "liqueur", 500, 20, 100)
            module.purchase("gin")
            module.purchase("liqueur")
            recipe = module.define_recipe(
                "test",
                "测试酒",
                {"gin": 45, "liqueur": 15},
                dilution_ml=30,
                price=68,
            )
            self.assertEqual(recipe["volume_ml"], 90)
            self.assertEqual(recipe["pure_alcohol_ml"], 21)
            self.assertEqual(recipe["abv"], 23.33)
            self.assertEqual(recipe["alcohol_units"], 2.1)
            module.register_person("guest", tolerance=50, absorption=1)
            before = module.summary()["cash"]
            served = module.serve("guest", "test", tip=5)
            self.assertEqual(served["received"], 73)
            self.assertEqual(served["service_cost"], 4)
            self.assertEqual(module.summary()["cash"], before + 69)
            self.assertGreater(served["intox"]["intox"], 0)
            self.assertGreater(served["intox"]["pending"], 0)
            owner = module.owner_drink("test")
            self.assertGreater(owner["inventory_loss"], 0)
            before_turn = owner["intox"]["intox"]
            after_turn = module.conversation_turn("owner")
            self.assertGreater(after_turn["intox"], before_turn)
            self.assertIn("body", after_turn)
            self.assertIn("cognition", after_turn)
            self.assertIn("expression", after_turn)
            self.assertTrue(after_turn["must_act"])
            self.assertEqual(after_turn["trend"], "rising")
            self.assertIn("仍在吸收", after_turn["body"])
            recovered = after_turn
            for _ in range(20):
                recovered = module.conversation_turn("owner")
                if not recovered["must_act"]:
                    break
            self.assertFalse(recovered["must_act"])
            self.assertIn("可以恢复平常表达", recovered["expression"])
            self.assertIn("醉态影响已经结束", recovered["hard_limit"])
            module.register_person("guest_two", tolerance=35, absorption=1.1)
            module.serve("guest_two", "test")
            self.assertGreater(module._load()["people"]["guest_two"]["pending"], 0)
            module.close_shift()
            closed_people = module._load()["people"]
            self.assertEqual(closed_people["guest_two"]["intox"], 0)
            self.assertEqual(closed_people["guest_two"]["pending"], 0)
            self.assertEqual(closed_people["owner"]["intox"], recovered["intox"])
            archived_cash = module.summary()["cash"]
            archive = module.export_archive()
            link = module.viewer_link({"bar": "测试酒馆", "guests": []})
            self.assertIn("/#bar=", link)
            module.spend(50, "测试")
            restored = module.restore_archive(archive)
            self.assertEqual(restored["cash"], archived_cash)

    def test_lite_quote_decision_handles_price_without_permanent_refusal(self):
        launcher_path = Path(__file__).with_name("bar_game_lite.py")
        spec = importlib.util.spec_from_file_location("lite_quote_test", launcher_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with TemporaryDirectory() as directory:
            module.SAVE_PATH = Path(directory) / "lite.json"
            module.new_game(31, cash=500)
            module.define_product("gin", "金酒", "gin", 700, 40, 140)
            module.purchase("gin")
            module.define_recipe("house", "店酒", {"gin": 40}, 80, 90)
            first = module.quote_decision(
                "guest",
                "house",
                budget_remaining=40,
                willingness=0.7,
            )
            self.assertIn(
                first["decision"],
                {"haggle", "switch_cheaper", "walk_out"},
            )
            state = module._load()
            state["recipes"]["house"]["price"] = 36
            module._save(state)
            second = module.quote_decision(
                "guest",
                "house",
                budget_remaining=40,
                willingness=0.9,
                explained=True,
                attempt=2,
            )
            self.assertEqual(second["decision"], "accept")

    def test_lite_committed_order_does_not_randomly_reverse_itself(self):
        launcher_path = Path(__file__).with_name("bar_game_lite.py")
        spec = importlib.util.spec_from_file_location("lite_committed_test", launcher_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with TemporaryDirectory() as directory:
            module.SAVE_PATH = Path(directory) / "lite.json"
            module.new_game(31, cash=500)
            module.define_product("gin", "金酒", "gin", 700, 40, 140)
            module.purchase("gin")
            module.define_recipe("neat", "净饮", {"gin": 40}, 0, 30)
            result = module.quote_decision(
                "guest",
                "neat",
                budget_remaining=48,
                willingness=0.01,
                committed_order=True,
            )
            self.assertEqual(result["decision"], "accept")
            self.assertEqual(result["accept_chance"], 1.0)

    def test_lite_accepts_products_from_any_world_or_dimension(self):
        launcher_path = Path(__file__).with_name("bar_game_lite.py")
        spec = importlib.util.spec_from_file_location("lite_open_world_test", launcher_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with TemporaryDirectory() as directory:
            module.SAVE_PATH = Path(directory) / "lite.json"
            module.new_game(88, cash=900)
            product = module.define_product(
                "第七码头·月潮",
                "第七码头月潮",
                "六维潮汐发酵物",
                880,
                31,
                210,
            )
            self.assertEqual(product["kind"], "六维潮汐发酵物")
            module.purchase("第七码头·月潮")
            recipe = module.define_recipe(
                "折叠海岸",
                "折叠海岸",
                {"第七码头·月潮": 40},
                dilution_ml=60,
                price=96,
            )
            self.assertEqual(recipe["abv"], 12.4)


if __name__ == "__main__":
    unittest.main()
