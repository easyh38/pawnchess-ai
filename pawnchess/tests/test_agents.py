"""탐색 에이전트 검증: Minimax-AlphaBeta 교차 검증, 평가 함수 가중치, 기본 동작."""
import unittest

from pawnchess import Config, CountingGame, Game, RandomAgent, run_matches
from pawnchess.agents import (ADV_EVAL_WEIGHTS, EVAL_WEIGHTS, AlphaBetaAdvancedAgent,
                              AlphaBetaAgent, AlphaBetaEvalAgent, BfsAgent,
                              MinimaxAgent, evaluate, evaluate_advanced)

INF = float("inf")


class TestMinimaxAlphaBeta(unittest.TestCase):
    def test_same_values_and_fewer_nodes(self):
        """N=3 pawn: 루트의 모든 수에 대해 Minimax와 AlphaBeta 값이 같고, AlphaBeta 노드가 더 적다."""
        game = Game(Config(n=3))
        s0 = game.initial_state()
        me = game.to_move(s0)
        mm_game, ab_game = CountingGame(game), CountingGame(game)
        mm, ab = MinimaxAgent(), AlphaBetaAgent()
        for a in game.actions(s0):
            child = game.result(s0, a)
            self.assertEqual(mm.minimax(mm_game, child, me),
                             ab.alphabeta(ab_game, child, me, -INF, INF))
        self.assertLess(ab_game.result_calls, mm_game.result_calls)

    def test_n3_black_wins_with_perfect_play(self):
        """7장 기준값: N=3 pawn은 흑 필승 → 루트(백 차례)의 minimax 값은 -1."""
        game = Game(Config(n=3))
        s0 = game.initial_state()
        mm = MinimaxAgent()
        values = [mm.minimax(game, game.result(s0, a), game.to_move(s0))
                  for a in game.actions(s0)]
        self.assertEqual(max(values), -1)


class TestEvalWeights(unittest.TestCase):
    def setUp(self):
        self.game = Game(Config(n=5))
        s = self.game.initial_state()
        for _ in range(3):                       # 비대칭 국면을 하나 만든다
            s = self.game.result(s, self.game.actions(s)[0])
        self.state = s

    def test_default_weights_match_original_formula(self):
        """가중치를 안 주면 원래 식(0.45/0.45, 0.30/0.20/0.25/0.15/0.10)과 같다."""
        self.assertEqual(EVAL_WEIGHTS, {"material": 0.45, "advance": 0.45})
        self.assertAlmostEqual(sum(ADV_EVAL_WEIGHTS.values()), 1.0)
        ag = AlphaBetaEvalAgent()
        self.assertEqual(ag.evaluate(self.game, self.state, 1),
                         evaluate(self.game, self.state, 1))
        adv = AlphaBetaAdvancedAgent()
        self.assertEqual(adv.evaluate(self.game, self.state, 1),
                         evaluate_advanced(self.game, self.state, 1))

    def test_partial_override(self):
        ag = AlphaBetaEvalAgent(weights={"material": 0.9, "advance": 0.0})
        self.assertEqual(ag.weights, {"material": 0.9, "advance": 0.0})
        adv = AlphaBetaAdvancedAgent(weights={"mobility": 0.0})
        self.assertEqual(adv.weights["mobility"], 0.0)
        self.assertEqual(adv.weights["material"], ADV_EVAL_WEIGHTS["material"])

    def test_eval_is_zero_sum(self):
        for w in ({"material": 0.2, "advance": 0.7}, None):
            e_w = evaluate(self.game, self.state, 1, w)
            e_b = evaluate(self.game, self.state, -1, w)
            self.assertAlmostEqual(e_w, -e_b)

    def test_invalid_weights_rejected(self):
        with self.assertRaises(ValueError):
            AlphaBetaEvalAgent(weights={"material": 0.8, "advance": 0.5})   # 합 > 1
        with self.assertRaises(ValueError):
            AlphaBetaEvalAgent(weights={"passed": 0.1})                    # 기본 평가 함수에 없는 항


class TestAgentsPlay(unittest.TestCase):
    def test_agents_beat_random_on_4x4(self):
        game = Game(Config(n=4))
        for make in (lambda: AlphaBetaEvalAgent(seed=0), lambda: AlphaBetaAdvancedAgent(seed=0),
                     lambda: BfsAgent(seed=0)):
            stats = run_matches(game, make(), RandomAgent(0), 10)
            self.assertGreaterEqual(stats.a_wins, 7, msg=stats.summary())


if __name__ == "__main__":
    unittest.main()
