"""README "환경 검증 기준값" 절의 값 검증.

여기의 전수 탐색(트리 크기 세기, 필승 여부 판정)은 '검증용 코드'이며
팀이 구현할 Minimax/AlphaBeta 에이전트와는 무관하다. 환경 함수만 사용한다.
"""
import unittest

from pawnchess.game import BLACK, WHITE, Config, Game


def decided_by_goal_or_capture(game, s):
    n = game.config.n
    b = s.board
    return (WHITE in b[n - 1] or BLACK in b[0]
            or not any(WHITE in r for r in b) or not any(BLACK in r for r in b))


def tree_stats(game):
    """(비종료 국면 수[board+to_move 기준], 전체 트리 노드 수[종료 포함], 루트 값[백 관점])

    기준값의 '비종료'는 도달/전멸로 끝나지 않은 국면이다. 차례인 쪽이 둘 수 없는
    국면(수 없음 패배)도 여기에 센다 — N=4에서 11420 + 292 = 11712.
    """
    sizes, values, nonterminal = {}, {}, set()

    def dfs(s):
        key = (s.board, s.to_move)
        if key in sizes:
            return sizes[key], values[key]
        if not decided_by_goal_or_capture(game, s):
            nonterminal.add(key)
        if game.is_terminal(s):
            sizes[key], values[key] = 1, game.utility(s, WHITE)
            return sizes[key], values[key]
        total, vals = 1, []
        for a in game.actions(s):
            sz, v = dfs(game.result(s, a))
            total += sz
            vals.append(v)
        sizes[key] = total
        values[key] = max(vals) if s.to_move == WHITE else min(vals)
        return total, values[key]

    root = game.initial_state()
    total, value = dfs(root)
    return len(nonterminal), total, value


def solve(game, s, memo):
    """s에서 둘 차례인 쪽 관점의 게임 값(+1/0/-1). 필승 발견 시 조기 종료."""
    if game.is_terminal(s):
        return game.utility(s, s.to_move)   # 종료 국면: 차례인 쪽 관점
    key = (s.board, s.to_move, s.ply)
    if key in memo:
        return memo[key]
    best = -2.0
    for a in game.actions(s):
        child = game.result(s, a)
        v = -solve(game, child, memo) if not game.is_terminal(child) \
            else game.utility(child, s.to_move)
        if v > best:
            best = v
            if best == 1.0:
                break
    memo[key] = best
    return best


class PawnReference(unittest.TestCase):
    def test_n3(self):
        nt, total, value = tree_stats(Game(Config(n=3, rule="pawn")))
        self.assertEqual((nt, total), (78, 252))
        self.assertEqual(value, -1.0)   # 흑(후수) 필승

    def test_n4(self):
        nt, total, value = tree_stats(Game(Config(n=4, rule="pawn")))
        self.assertEqual((nt, total), (11712, 4197973))
        self.assertEqual(value, 1.0)    # 백(선수) 필승


class CrossReference(unittest.TestCase):
    @staticmethod
    def white_value(n, limit):
        g = Game(Config(n=n, rule="cross", max_plies=limit))
        return solve(g, g.initial_state(), {})

    def test_n3_black_wins_within_8(self):
        self.assertEqual(self.white_value(3, 8), -1.0)  # 흑 필승
        self.assertEqual(self.white_value(3, 7), 0.0)   # 8반수 미만이면 무승부

    def test_n4_threshold_21(self):
        self.assertEqual(self.white_value(4, 20), 0.0)  # 20반수 이하면 무승부
        self.assertEqual(self.white_value(4, 21), 1.0)  # 21반수 이상이면 백 필승


if __name__ == "__main__":
    unittest.main()
