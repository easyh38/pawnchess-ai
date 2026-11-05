import random
import unittest

from pawnchess.game import BLACK, WHITE, Action, Config, Game
from pawnchess.notation import (format_move, parse_move, state_from_text,
                                direction_to_action)


class PawnRules(unittest.TestCase):
    def setUp(self):
        self.g = Game(Config(n=4, rule="pawn"))

    def test_initial(self):
        s = self.g.initial_state()
        self.assertEqual(s.to_move, WHITE)
        self.assertEqual(s.board[0], (1, 1, 1, 1))
        self.assertEqual(s.board[3], (-1, -1, -1, -1))
        self.assertEqual(len(self.g.actions(s)), 4)
        self.assertFalse(self.g.is_terminal(s))

    def test_forward_blocked_and_capture(self):
        s = state_from_text("""
            . . . B
            . . . .
            . B . .
            W . W .
        """)
        moves = {format_move(a) for a in self.g.actions(s)}
        self.assertEqual(moves, {"a1a2", "a1b2", "c1c2", "c1b2"})
        s = state_from_text("""
            . . . B
            . . . .
            W . . .
            W . . .
        """)
        self.assertEqual({format_move(a) for a in self.g.actions(s)}, {"a2a3"})  # a1 막힘

    def test_black_moves_down(self):
        s = state_from_text("""
            . B . .
            . . . .
            . . . .
            W . . .
        """, to_move=BLACK)
        self.assertEqual({format_move(a) for a in self.g.actions(s)}, {"b4b3"})

    def test_win_by_reaching_goal(self):
        s = state_from_text("""
            . . . B
            W . . .
            . . . .
            . . W .
        """)
        t = self.g.result(s, parse_move("a3a4", s))
        self.assertTrue(self.g.is_terminal(t))
        self.assertEqual(t.winner, WHITE)

    def test_win_by_capturing_all(self):
        s = state_from_text("""
            . . . .
            . B . .
            W . . .
            . . . .
        """)
        t = self.g.result(s, parse_move("a2b3", s))
        self.assertEqual(t.winner, WHITE)

    def test_no_move_loses(self):
        # 백이 d3으로 두면 흑 d4는 막혀 있고 잡을 것도 없다 → 흑 패배
        s = state_from_text("""
            . . . B
            . . . W
            . . . .
            W . . .
        """)
        # 흑 기물은 d4 하나, d3에 백이 있어 직진 불가, 대각선(c3) 비어 있음 → 흑은 막힘
        t = self.g.result(s, parse_move("a1a2", s))
        self.assertEqual(t.winner, WHITE)
        g2 = Game(Config(n=4, no_move="draw"))
        self.assertEqual(g2.result(s, parse_move("a1a2", s)).winner, 0)

    def test_illegal_rejected(self):
        s = self.g.initial_state()
        for bad in ("a1a3", "a1b2", "b4b3", "a2a3", "a1a1"):
            with self.assertRaises(ValueError):
                self.g.result(s, parse_move(bad, s))

    def test_result_does_not_mutate(self):
        s = self.g.initial_state()
        snapshot = (s.board, s.to_move, s.ply, s.winner)
        for a in self.g.actions(s):
            self.g.result(s, a)
        self.assertEqual((s.board, s.to_move, s.ply, s.winner), snapshot)

    def test_state_hashable(self):
        s = self.g.initial_state()
        self.assertEqual(hash(s), hash(self.g.initial_state()))
        self.assertIn(s, {s})

    def test_actions_deterministic_order(self):
        s = self.g.initial_state()
        self.assertEqual(self.g.actions(s), self.g.actions(s))

    def test_utility_zero_sum_and_guard(self):
        s = self.g.initial_state()
        with self.assertRaises(ValueError):
            self.g.utility(s, WHITE)
        rng = random.Random(0)
        for _ in range(200):
            s = self.g.initial_state()
            while not self.g.is_terminal(s):
                s = self.g.result(s, rng.choice(self.g.actions(s)))
            self.assertEqual(self.g.utility(s, WHITE), -self.g.utility(s, BLACK))
            self.assertIn(self.g.utility(s, WHITE), (1.0, -1.0))   # pawn은 무승부 없음

    def test_direction(self):
        s = self.g.initial_state()
        a = direction_to_action(self.g, s, "a1", "up")
        self.assertEqual(a, Action((0, 0), (1, 0), False))
        with self.assertRaises(ValueError):
            direction_to_action(self.g, s, "a1", "left")

    def test_notation_roundtrip(self):
        s = self.g.initial_state()
        for a in self.g.actions(s):
            self.assertEqual(parse_move(format_move(a), s), a)


if __name__ == "__main__":
    unittest.main()
