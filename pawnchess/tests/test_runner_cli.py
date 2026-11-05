import unittest

from pawnchess.agents import AGENTS, Agent, RandomAgent
from pawnchess.cli import Session
from pawnchess.game import Config, Game
from pawnchess.runner import CountingGame, play_game, run_matches


class RunnerTests(unittest.TestCase):
    def test_play_game_and_seed(self):
        g = Game(Config(n=4))
        r1 = play_game(g, RandomAgent(1), RandomAgent(2))
        r2 = play_game(g, RandomAgent(1), RandomAgent(2))
        self.assertEqual(r1.moves, r2.moves)
        self.assertIn(r1.winner, (1, -1))
        self.assertEqual(len(r1.times), r1.plies)

    def test_run_matches_counts(self):
        g = Game(Config(n=4))
        st = run_matches(g, RandomAgent(0), RandomAgent(1), 40)
        self.assertEqual(st.a_wins + st.b_wins + st.draws, 40)
        self.assertEqual(sum(sum(v) for v in st.a_by_color.values()), 40)
        self.assertEqual(sum(st.a_by_color["white"]), 20)

    def test_custom_agent_plugs_in(self):
        class First(Agent):
            def choose_action(self, game, state):
                return game.actions(state)[0]
        st = run_matches(Game(Config(n=4)), First(), RandomAgent(0), 4)
        self.assertEqual(st.n_games, 4)

    def test_counting_game(self):
        cg = CountingGame(Game(Config(n=4)))
        play_game(cg, RandomAgent(0), RandomAgent(0))
        self.assertGreater(cg.actions_calls, 0)
        self.assertGreater(cg.result_calls, 0)

    def test_cli_session(self):
        s = Session(Config(n=4))
        before = s.state
        self.assertIn("불가", s.execute("a1a3")[0])
        self.assertIs(s.state, before)
        s.execute("peek a1a2")
        self.assertIs(s.state, before)
        s.execute("a1a2")
        self.assertEqual(s.state.ply, 1)
        s.execute("undo")
        self.assertEqual(s.state, before)
        s.execute("set rule cross")
        self.assertEqual(s.config.rule, "cross")
        s.execute("move 1")
        self.assertEqual(s.state.ply, 1)
        self.assertIn("A", s.execute("auto random random 10 1")[0] + "A")

    def test_cli_vs_random(self):
        s = Session(Config(n=4))
        s.execute("play random w")
        s.execute("move 1")
        self.assertEqual(s.state.ply, 2)    # 내 수 + 상대 응수
        s.execute("undo")
        self.assertEqual(s.state.ply, 0)

    def test_cli_registered_agent(self):
        class First(Agent):
            def choose_action(self, game, state):
                return game.actions(state)[0]
        AGENTS["first"] = First
        try:
            s = Session(Config(n=4))
            self.assertIn("first", s.execute("play first w")[0])
            s.execute("move 1")
            self.assertEqual(s.state.ply, 2)    # 내 수 + 등록 에이전트의 응수
            self.assertIn("사용법", s.execute("play nothing")[0])
        finally:
            del AGENTS["first"]


if __name__ == "__main__":
    unittest.main()
