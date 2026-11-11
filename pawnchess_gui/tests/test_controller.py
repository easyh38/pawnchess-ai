import unittest

from pawnchess.game import BLACK, WHITE, Config
from pawnchess_gui.controller import (HUMAN, Match, parse_max_plies,
                                      parse_repetition, player_choices)


class MatchTests(unittest.TestCase):
    def test_choices_include_human_and_agents(self):
        ch = player_choices()
        self.assertEqual(ch[0], HUMAN)
        self.assertIn("random", ch)

    def test_unknown_player_rejected(self):
        with self.assertRaises(ValueError):
            Match(Config(), HUMAN, "nope")

    def test_targets_and_apply(self):
        m = Match(Config(n=4), HUMAN, HUMAN)
        self.assertTrue(m.is_human_turn())
        ts = m.targets_from((0, 0))
        self.assertEqual([a.to for a in ts], [(1, 0)])
        m.apply(ts[0])
        self.assertEqual(m.to_move(), BLACK)
        self.assertEqual(m.last, ts[0])
        self.assertEqual(len(m.move_lines()), 1)

    def test_illegal_move_keeps_state(self):
        m = Match(Config(n=4), HUMAN, HUMAN)
        bad = m.targets_from((0, 0))[0]
        m.apply(bad)
        with self.assertRaises(ValueError):
            m.apply(bad)  # 이제 흑 차례라 불법
        self.assertEqual(len(m.history), 1)

    def test_undo_skips_ai_moves(self):
        m = Match(Config(n=4), HUMAN, "random")
        m.apply(m.legal_actions()[0])
        ai = m.agent_to_move()
        m.apply(ai.choose_action(m.game, m.state), 0.0)
        self.assertEqual(m.to_move(), WHITE)
        self.assertTrue(m.undo())
        self.assertEqual(m.state, m.game.initial_state())
        self.assertEqual(m.moves, [])

    def test_ai_vs_ai_cannot_undo_and_finishes(self):
        m = Match(Config(n=4), "random", "random")
        self.assertTrue(m.all_ai())
        while not m.is_over():
            m.apply(m.agent_to_move().choose_action(m.game, m.state))
        self.assertFalse(m.can_undo())
        self.assertIsNotNone(m.result_text())

    def test_parsers(self):
        self.assertEqual(parse_max_plies("auto"), "auto")
        self.assertIsNone(parse_max_plies("none"))
        self.assertEqual(parse_max_plies("30"), 30)
        self.assertIsNone(parse_repetition("none"))
        self.assertEqual(parse_repetition("3"), 3)


if __name__ == "__main__":
    unittest.main()
