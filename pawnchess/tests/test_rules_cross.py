import unittest

from pawnchess.game import BLACK, WHITE, Config, Game
from pawnchess.notation import format_move, parse_move, state_from_text


class CrossRules(unittest.TestCase):
    def test_initial_counts(self):
        self.assertEqual(len(Game(Config(n=3, rule="cross")).actions(
            Game(Config(n=3, rule="cross")).initial_state())), 3)
        g = Game(Config(n=4, rule="cross"))
        self.assertEqual(len(g.actions(g.initial_state())), 4)

    def test_four_dir_moves_diagonal_capture(self):
        g = Game(Config(n=4, rule="cross"))
        s = state_from_text("""
            . . . .
            B B . .
            . W . .
            . . . .
        """)
        # 이동은 빈 칸 4방향(앞 b3은 막힘), 잡기는 대각선 앞(a3)만
        self.assertEqual({format_move(a) for a in g.actions(s)},
                         {"b2a2", "b2c2", "b2b1", "b2a3"})
        caps = {format_move(a) for a in g.actions(s) if a.capture}
        self.assertEqual(caps, {"b2a3"})

    def test_no_orthogonal_or_backward_capture(self):
        g = Game(Config(n=4, rule="cross"))
        s = state_from_text("""
            . . . .
            . B . .
            B W B .
            . B . .
        """)
        # 앞(b3)·옆(a2,c2)·뒤(b1)의 적은 잡을 수 없다
        self.assertEqual([a for a in g.actions(s) if a.capture], [])
        self.assertEqual(g.actions(s), [])

    def test_black_captures_diagonally_down(self):
        g = Game(Config(n=4, rule="cross"))
        s = state_from_text("""
            . . . .
            . B . .
            W . W .
            . . . .
        """)
        s = type(s)(s.board, -1, s.ply, None)
        caps = {format_move(a) for a in g.actions(s) if a.capture}
        self.assertEqual(caps, {"b3a2", "b3c2"})

    def test_cannot_enter_own_piece(self):
        g = Game(Config(n=4, rule="cross"))
        s = state_from_text("""
            . . . B
            . . . .
            W W . .
            . . . .
        """)
        self.assertNotIn("a2b2", {format_move(a) for a in g.actions(s)})

    def test_max_plies_draw(self):
        g = Game(Config(n=4, rule="cross", max_plies=2))
        s = g.initial_state()
        s = g.result(s, g.actions(s)[0])
        self.assertIsNone(s.winner)
        s = g.result(s, g.actions(s)[0])
        self.assertTrue(g.is_terminal(s))
        self.assertEqual(s.winner, 0)
        self.assertEqual(g.utility(s, WHITE), 0.0)

    def test_default_max_plies(self):
        self.assertEqual(Config(rule="cross").effective_max_plies, 50)
        self.assertIsNone(Config(rule="pawn").effective_max_plies)

    def test_repetition_draw(self):
        g = Game(Config(n=4, rule="cross", repetition_draw=3, max_plies=None))
        s = state_from_text("""
            B . . .
            . . . .
            . . . .
            . . . W
        """)
        s = type(s)(s.board, s.to_move, s.ply, None, ((s.board, s.to_move),))
        moves = ["d1c1", "a4b4", "c1d1", "b4a4"]
        for _ in range(2):
            for m in moves:
                self.assertIsNone(s.winner)
                s = g.result(s, parse_move(m, s))
        self.assertEqual(s.winner, 0)


if __name__ == "__main__":
    unittest.main()
