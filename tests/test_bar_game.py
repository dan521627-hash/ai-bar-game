import unittest
import importlib.util
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

import bar_game

ROOT = Path(__file__).resolve().parents[1]

class SetupAndShopTests(unittest.TestCase):
    def test_license_invites_derivatives_but_requires_original_attribution(self):
        license_text = (ROOT / "LICENSING.md").read_text(encoding="utf-8")
        software_license = (ROOT / "LICENSE").read_text(encoding="utf-8")
        notice = (ROOT / "NOTICE.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for text in (license_text, notice, readme):
            self.assertIn("dan521627-hash", text)
            self.assertIn("https://github.com/dan521627-hash/ai-bar-game", text)
        self.assertIn("MIT License", license_text)
        self.assertIn("CC BY 4.0", license_text)
        self.assertIn("说明你是否作出了修改", license_text)
        self.assertIn("Copyright (c) 2026 dan521627-hash", software_license)
        self.assertIn("欢迎二创", readme)

    def test_readme_requires_user_to_choose_exactly_one_version(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("执行AI必须先让用户选择版本", readme)
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

    def test_full_decor_and_upgrade_purchase_persist_and_charge_cash(self):
        state = bar_game._default_state(44)
        state["cash"] = 5000
        decor_id = next(iter(bar_game.DECOR_DEFS))
        decor_cost = int(bar_game.DECOR_DEFS[decor_id]["cost"])
        before = state["cash"]
        decor_result = bar_game._cmd_decorate(state, [decor_id])
        self.assertIn(decor_id, state["decorations"])
        self.assertEqual(state["cash"], before - decor_cost)
        self.assertIn("已添置", decor_result)

        upgrade_id = next(iter(bar_game.UPGRADE_DEFS))
        upgrade_cost = int(bar_game.UPGRADE_DEFS[upgrade_id]["costs"][0])
        before_upgrade = state["cash"]
        upgrade_result = bar_game._cmd_upgrade(state, [upgrade_id])
        self.assertEqual(state["upgrades"][upgrade_id], 1)
        self.assertEqual(state["cash"], before_upgrade - upgrade_cost)
        self.assertIn("完成升级", upgrade_result)


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

    def test_next_keeps_finished_guests_seated_instead_of_clearing_the_room(self):
        state = bar_game._default_state(260)
        state["phase"] = "open"
        state["visit"] = 3
        bar_game._spawn_scene(state, force=True)
        original_ids = {guest["id"] for guest in state["active_guests"]}
        self.assertTrue(original_ids)
        for guest in state["active_guests"]:
            guest["served"] = True
            guest["closed"] = True
            guest["dwell_turns"] = 3
        state["interaction"] = None
        bar_game._cmd_next(state, [])
        remaining_ids = {guest["id"] for guest in state["active_guests"]}
        self.assertTrue(original_ids.issubset(remaining_ids))

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

    def test_later_normal_shift_forces_real_companion_group_if_none_arrived(self):
        state = bar_game._default_state(812)
        state["visit"] = 4
        state["session"]["arrival_waves"] = 2
        state["session"]["group_arrivals"] = 0
        text = bar_game._spawn_scene(state, join_existing=True)
        self.assertGreaterEqual(len(state["active_guests"]), 2)
        self.assertEqual(state["session"]["group_arrivals"], 1)
        self.assertIn("熟人", text)


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
        launcher_path = ROOT / "bar_game_lite.py"
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
        launcher_path = ROOT / "bar_game_lite.py"
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
        launcher_path = ROOT / "bar_game_lite.py"
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
        launcher_path = ROOT / "bar_game_lite.py"
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
        launcher_path = ROOT / "bar_game_lite.py"
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

    def test_lite_assets_are_paid_owned_upgraded_and_remembered(self):
        launcher_path = ROOT / "bar_game_lite.py"
        spec = importlib.util.spec_from_file_location("lite_asset_test", launcher_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with TemporaryDirectory() as directory:
            module.SAVE_PATH = Path(directory) / "lite.json"
            module.new_game(91, cash=900)
            bought = module.buy_asset(
                "old_jukebox",
                "旧世界点唱机",
                "equipment",
                180,
                "一间停业舞厅",
                "偶尔触发音乐相关事件",
            )
            self.assertEqual(bought["level"], 1)
            upgraded = module.upgrade_asset(
                "old_jukebox",
                260,
                "可以读出跨世界唱片",
            )
            self.assertEqual(upgraded["level"], 2)
            story = module.record_asset_story(
                "old_jukebox", 1, "第一次在雨夜自行响起"
            )
            self.assertEqual(story["story_stage"], 1)
            state = module._load()
            self.assertEqual(state["cash"], 460)
            self.assertEqual(state["assets"]["old_jukebox"]["total_spent"], 440)
            self.assertEqual(module.summary()["assets"]["old_jukebox"]["level"], 2)

    def test_lite_domain_shuffle_covers_every_macro_domain_without_context_bias(self):
        launcher_path = ROOT / "bar_game_lite.py"
        spec = importlib.util.spec_from_file_location("lite_domain_test", launcher_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with TemporaryDirectory() as directory:
            module.SAVE_PATH = Path(directory) / "lite.json"
            module.new_game(20260728)
            custom = module.register_guest_domain(
                "dream_archaeology",
                "梦境考古、失落记忆文明及尚未命名的叙事来源",
            )
            self.assertEqual(custom["domain_id"], "dream_archaeology")
            draws = [
                module.draw_guest_domain()
                for _ in range(len(module.GUEST_DOMAINS) + 1)
            ]
            domain_ids = [item["domain_id"] for item in draws]
            self.assertEqual(
                set(domain_ids),
                set(module.GUEST_DOMAINS) | {"dream_archaeology"},
            )
            self.assertEqual(len(domain_ids), len(set(domain_ids)))
            self.assertIn("history_reality", domain_ids)
            self.assertIn("literature", domain_ids)
            for item in draws:
                self.assertEqual(item["source"], "independent_shuffle_bag")
                self.assertNotIn("选择熟悉人物", item["director_rule"])
            myth_label = module.GUEST_DOMAINS["myth_legend"]
            self.assertIn("中国", myth_label)
            self.assertIn("日本", myth_label)
            self.assertIn("西游记", myth_label)
            history_label = module.GUEST_DOMAINS["history_reality"]
            self.assertIn("中国上下五千年", history_label)
            self.assertIn("中外帝王", history_label)
            self.assertIn("同一国家、时代、文化或作品系列", draws[0]["director_rule"])

    def test_interaction_window_is_mandatory_in_both_editions_and_readme(self):
        full_text = (ROOT / "bar_game.py").read_text(encoding="utf-8")
        lite_text = (ROOT / "bar_game_lite.py").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for text in (full_text, lite_text, readme):
            self.assertIn("强制互动窗口" if text != readme else "强制互动节奏", text)
            self.assertIn("进门→点单→喝完→评价→离店", text)
            self.assertIn("弹", text)
        self.assertIn("持续在场制", lite_text)
        self.assertIn("持续在场制", readme)
        self.assertIn("正常长度的营业至少应实际", lite_text)
        self.assertIn("分类字段只用于记账，不能成为想象边界", full_text)
        self.assertIn("只是数值档案的记账分类，不是内容白名单", lite_text)
        self.assertIn("酒馆可以开在现实街区", readme)

    def test_full_arrival_and_service_emit_internal_pacing_brakes(self):
        state = bar_game._default_state(seed=20260728)
        state["phase"] = "open"
        state["visit"] = 1
        arrival = bar_game._spawn_scene(state, force=True)
        self.assertIn("强制互动窗口", arrival)


if __name__ == "__main__":
    unittest.main()
