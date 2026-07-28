import unittest
from collections import Counter

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


class WorldBreadthTests(unittest.TestCase):
    def test_ninja_world_and_cross_world_upgrades_exist(self):
        names = {card["name"] for card in bar_game.BUILTIN_GUESTS}
        for name in ("成年后的漩涡鸣人", "成年后的日向雏田", "宇智波斑", "长门"):
            self.assertIn(name, names)
        for upgrade_id in (
            "translator",
            "guestbook",
            "safety_ward",
            "adaptive_ambience",
        ):
            self.assertIn(upgrade_id, bar_game.UPGRADE_DEFS)


if __name__ == "__main__":
    unittest.main()
