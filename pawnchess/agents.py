"""에이전트 인터페이스. 탐색 에이전트(Minimax 등)는 팀이 이 인터페이스로 추가한다."""
from __future__ import annotations

import random
from collections import deque
from typing import Callable, Optional

from .game import RULES, WHITE, Action, Game, State
from .notation import (direction_to_action, format_move, is_move_text,
                       is_square_text, parse_move, render_board)

#기본 세팅===============================================================================================

def _shuffled_actions(game: Game, state: State, rng: random.Random) -> list[Action]:
    """루트의 합법 수를 섞어서 돌려준다.

    최선 수 선택은 `score > best_score`(엄격 비교)이므로, 점수가 같은 최선 수가 여럿이면
    섞인 순서에서 먼저 나온 것이 뽑힌다 → 동점 수 중 무작위 선택.
    엄격 비교를 유지하므로 알파베타 가지치기의 정확성도 그대로다.
    (seed를 주면 같은 seed끼리는 항상 같은 대국이 나온다)
    """
    acts = game.actions(state)
    rng.shuffle(acts)
    return acts


class Agent:
    def choose_action(self, game: Game, state: State) -> Action:
        raise NotImplementedError


class RandomAgent(Agent):
    def __init__(self, seed: Optional[int] = None) -> None:
        self.rng = random.Random(seed)

    def choose_action(self, game: Game, state: State) -> Action:
        return self.rng.choice(game.actions(state))


class HumanAgent(Agent):
    """터미널에서 수를 입력받는다: 'a1a2', 'a2 up', 또는 합법 수 번호."""

    def __init__(self, input_fn: Callable[[str], str] = input,
                 print_fn: Callable[[str], None] = print) -> None:
        self.input_fn = input_fn
        self.print_fn = print_fn

    def choose_action(self, game: Game, state: State) -> Action:
        acts = game.actions(state)
        self.print_fn(render_board(state, game.config))
        while True:
            text = self.input_fn("수 입력 (예: a1a2 / a2 up / 번호, ? = 목록) > ").strip().lower()
            if text == "?":
                for i, a in enumerate(acts, 1):
                    self.print_fn(f"  {i}: {format_move(a)}")
                continue
            try:
                parts = text.split()
                if len(parts) == 1 and parts[0].isdigit():
                    i = int(parts[0])
                    if not 1 <= i <= len(acts):
                        raise ValueError(f"번호는 1~{len(acts)}")
                    return acts[i - 1]
                if len(parts) == 1 and is_move_text(parts[0]):
                    a = parse_move(parts[0], state)
                    if a not in acts:
                        raise ValueError(game.illegal_reason(state, a))
                    return a
                if len(parts) == 2 and is_square_text(parts[0]):
                    return direction_to_action(game, state, parts[0], parts[1])
                raise ValueError("입력 형식을 이해하지 못했습니다")
            except ValueError as e:
                self.print_fn(f"  불가: {e}")
                
#=======================================================================================================

class MinimaxAgent(Agent):
    """순수 Minimax. 깊이 제한·평가 함수 없이 종료 국면까지 끝까지 탐색한다.

    값은 루트에서 둘 차례인 쪽(me) 관점의 효용(+1 승 / 0 무 / -1 패)이다.
    """

    def __init__(self, name: str = "MinimaxAI", seed: Optional[int] = None) -> None:
        self.name = name
        self.rng = random.Random(seed)   # 동점인 최선 수 중 무작위 선택용

    def choose_action(self, game: Game, state: State) -> Action:
        acts = _shuffled_actions(game, state, self.rng)
        if not acts:
            raise ValueError("가능한 행동이 없습니다.")
        me = game.to_move(state)
        best_score = -float("inf")
        best_action = acts[0]
        for action in acts:
            score = self.minimax(game, game.result(state, action), me)
            if score > best_score:
                best_score, best_action = score, action
        return best_action

    def minimax(self, game: Game, state: State, me: int) -> float:
        """me 관점의 값. 내 차례면 max, 상대 차례면 min."""
        if game.is_terminal(state):
            return game.utility(state, me)
        values = [self.minimax(game, game.result(state, a), me)
                  for a in game.actions(state)]
        return max(values) if game.to_move(state) == me else min(values)


class AlphaBetaAgent(Agent):
    """Minimax + 알파베타 가지치기. 깊이 제한·평가 함수 없이 끝까지 탐색한다.

    순수 Minimax와 같은 값을 내지만, 결과에 영향을 주지 않는 가지를 잘라 노드 수가 줄어든다.
    - alpha: 지금까지 찾은 '내(max)가 보장받는' 최댓값
    - beta : 지금까지 찾은 '상대(min)가 보장받는' 최솟값
    - alpha >= beta가 되면 그 아래 수는 더 볼 필요가 없다 (가지치기)
    """

    def __init__(self, name: str = "AlphaBetaAI", seed: Optional[int] = None) -> None:
        self.name = name
        self.rng = random.Random(seed)   # 동점인 최선 수 중 무작위 선택용

    def choose_action(self, game: Game, state: State) -> Action:
        acts = _shuffled_actions(game, state, self.rng)
        if not acts:
            raise ValueError("가능한 행동이 없습니다.")
        me = game.to_move(state)
        alpha, beta = -float("inf"), float("inf")
        best_score = -float("inf")
        best_action = acts[0]
        for action in acts:
            score = self.alphabeta(game, game.result(state, action), me, alpha, beta)
            if score > best_score:
                best_score, best_action = score, action
            alpha = max(alpha, best_score)
        return best_action

    def alphabeta(self, game: Game, state: State, me: int,
                  alpha: float, beta: float) -> float:
        """me 관점의 값. 내 차례면 max, 상대 차례면 min."""
        if game.is_terminal(state):
            return game.utility(state, me)

        if game.to_move(state) == me:          # max 노드
            value = -float("inf")
            for a in game.actions(state):
                value = max(value, self.alphabeta(game, game.result(state, a), me, alpha, beta))
                alpha = max(alpha, value)
                if alpha >= beta:
                    break                      # beta 컷
            return value
        else:                                  # min 노드
            value = float("inf")
            for a in game.actions(state):
                value = min(value, self.alphabeta(game, game.result(state, a), me, alpha, beta))
                beta = min(beta, value)
                if alpha >= beta:
                    break                      # alpha 컷
            return value


def evaluate(game: Game, state: State, player: int) -> float:
    """종료되지 않은 국면의 평가 함수 (player 관점).

    E = 0.45 * (내 폰 수 - 상대 폰 수) / N
      + 0.45 * (내 전진도 합 - 상대 전진도 합) / (N * (N - 1))

    - 폰 개수: 폰이 많이 남을수록 유리
    - 전진도: 폰이 상대편 끝 줄(목표 줄)에 가까울수록 유리
              (백은 row가 클수록, 흑은 row가 작을수록 전진)
    - 두 항 모두 -1 ~ 1 사이로 정규화하고 0.45를 곱해, |E| < 0.9 가 되게 했다.
      → 실제 승패(utility ±1)가 항상 평가값보다 우선한다.
    """
    n = game.config.n
    my_count = opp_count = 0
    my_adv = opp_adv = 0
    for r, row in enumerate(state.board):
        for v in row:
            if v == 0:
                continue
            progress = r if v == WHITE else (n - 1 - r)
            if v == player:
                my_count += 1
                my_adv += progress
            else:
                opp_count += 1
                opp_adv += progress
    material = (my_count - opp_count) / n
    advance = (my_adv - opp_adv) / (n * (n - 1))
    return 0.45 * material + 0.45 * advance


class AlphaBetaEvalAgent(Agent):
    """Minimax + 알파베타 가지치기 + 깊이 제한 + 평가 함수.

    depth 수까지만 내다보고, 그 깊이에서 끝나지 않은 국면은 evaluate()로 점수를 매긴다.
    """

    def __init__(self, depth: int = 4, name: str = "AlphaBetaEvalAI",
                 seed: Optional[int] = None) -> None:
        if depth < 1:
            raise ValueError("depth는 1 이상이어야 합니다")
        self.depth = depth
        self.name = name
        self.rng = random.Random(seed)   # 동점인 최선 수 중 무작위 선택용

    def choose_action(self, game: Game, state: State) -> Action:
        acts = _shuffled_actions(game, state, self.rng)
        if not acts:
            raise ValueError("가능한 행동이 없습니다.")
        me = game.to_move(state)
        alpha, beta = -float("inf"), float("inf")
        best_score = -float("inf")
        best_action = acts[0]
        for action in acts:
            score = self.alphabeta(game, game.result(state, action), self.depth - 1,
                                   me, alpha, beta)
            if score > best_score:
                best_score, best_action = score, action
            alpha = max(alpha, best_score)
        return best_action

    def evaluate(self, game: Game, state: State, me: int) -> float:
        """깊이 0에서 쓰는 평가 함수. 하위 클래스에서 바꿔 끼울 수 있다."""
        return evaluate(game, state, me)

    def alphabeta(self, game: Game, state: State, depth: int, me: int,
                  alpha: float, beta: float) -> float:
        if game.is_terminal(state):
            # 깊이 제한이 있으면 '언젠가 이기는 수'끼리 점수가 같아 승리를 미룰 수 있다.
            # 남은 깊이가 클수록(=더 빨리 끝날수록) 조금 더 큰 값을 줘서 빨리 이기고 늦게 지게 한다.
            return game.utility(state, me) * (1 + 0.01 * depth)
        if depth == 0:
            return self.evaluate(game, state, me)

        if game.to_move(state) == me:          # max 노드
            value = -float("inf")
            for a in game.actions(state):
                value = max(value, self.alphabeta(game, game.result(state, a), depth - 1,
                                                  me, alpha, beta))
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
            return value
        else:                                  # min 노드
            value = float("inf")
            for a in game.actions(state):
                value = min(value, self.alphabeta(game, game.result(state, a), depth - 1,
                                                  me, alpha, beta))
                beta = min(beta, value)
                if alpha >= beta:
                    break
            return value


def evaluate_advanced(game: Game, state: State, player: int) -> float:
    """추천 평가 함수 (player 관점). 기본 evaluate()에 세 가지 항을 더했다.

    E = 0.30 * (폰 수 차이) / N
      + 0.20 * (전진도 합 차이) / (N * (N - 1))
      + 0.25 * (가장 멀리 나간 폰의 전진도 차이) / (N - 1)
      + 0.15 * (통과 폰 수 차이) / N
      + 0.10 * (합법 수 개수 차이) / (내 합법 수 + 상대 합법 수 + 1)

    - 최대 전진도: 목표 줄에 폰 하나만 닿아도 이기므로, 가장 앞선 폰을 따로 본다.
    - 통과 폰(passed pawn): 앞쪽의 같은 열·양옆 열에 상대 폰이 하나도 없어
      막거나 잡을 수 없는 폰.
    - 기동성: 둘 수 있는 수가 없으면 지므로(no_move="lose") 수가 많을수록 유리.
    - 가중치 합이 1이고 각 항이 -1 ~ 1 사이라 |E| < 1 → 실제 승패(±1)가 항상 우선한다.
    """
    n = game.config.n
    board = state.board
    gen = RULES[game.config.rule]
    opp = -player

    count = {player: 0, opp: 0}
    adv_sum = {player: 0, opp: 0}
    adv_max = {player: 0, opp: 0}
    passed = {player: 0, opp: 0}
    mobility = {player: 0, opp: 0}

    for r in range(n):
        for c in range(n):
            v = board[r][c]
            if v == 0:
                continue
            progress = r if v == WHITE else (n - 1 - r)
            count[v] += 1
            adv_sum[v] += progress
            adv_max[v] = max(adv_max[v], progress)

            # 통과 폰: 내 앞쪽 줄들에서 c-1, c, c+1 열에 상대 폰이 없는가
            ahead = range(r + 1, n) if v == WHITE else range(r - 1, -1, -1)
            cols = range(max(0, c - 1), min(n, c + 2))
            if not any(board[rr][cc] == -v for rr in ahead for cc in cols):
                passed[v] += 1

            # 기동성: 이 폰이 둘 수 있는 수의 개수
            # (game.actions 대신 규칙의 이동 생성기를 직접 써서 탐색 노드 수 집계에 섞이지 않게 함)
            mobility[v] += sum(1 for _ in gen(board, r, c, game.config))

    material = (count[player] - count[opp]) / n
    advance = (adv_sum[player] - adv_sum[opp]) / (n * (n - 1))
    frontier = (adv_max[player] - adv_max[opp]) / (n - 1)
    passed_diff = (passed[player] - passed[opp]) / n
    mob = (mobility[player] - mobility[opp]) / (mobility[player] + mobility[opp] + 1)

    return (0.30 * material + 0.20 * advance + 0.25 * frontier
            + 0.15 * passed_diff + 0.10 * mob)


class AlphaBetaAdvancedAgent(AlphaBetaEvalAgent):
    """AlphaBetaEvalAgent와 탐색은 똑같고, 평가 함수만 evaluate_advanced()로 바꾼 것."""

    def __init__(self, depth: int = 4, name: str = "AlphaBetaAdvancedAI",
                 seed: Optional[int] = None) -> None:
        super().__init__(depth=depth, name=name, seed=seed)

    def evaluate(self, game: Game, state: State, me: int) -> float:
        return evaluate_advanced(game, state, me)


class BfsAgent(Agent):
    """너비 우선 탐색(BFS)으로 '내가 이기는 가장 가까운 종료 국면'을 찾아 그 첫 수를 둔다.

    - 큐에 (국면, 루트에서 둔 첫 수, 깊이)를 넣고 깊이 순서대로 펼친다.
    - 같은 국면(board + to_move)은 visited로 한 번만 펼친다.
    - BFS는 상대의 최선 응수를 고려하지 않으므로, 상대가 바로 이길 수 있게 되는 첫 수는 제외한다.
    - max_depth 안에 승리 경로가 없으면 안전한 수 중에서 무작위로 고른다.
    """

    def __init__(self, max_depth: int = 4, max_nodes: int = 200_000,
                 seed: Optional[int] = None, name: str = "BfsAI") -> None:
        self.max_depth = max_depth
        self.max_nodes = max_nodes
        self.rng = random.Random(seed)
        self.name = name

    @staticmethod
    def _gives_opponent_win(game: Game, state: State, me: int) -> bool:
        if game.is_terminal(state):
            return False
        return any(game.result(state, a).winner == -me for a in game.actions(state))

    def choose_action(self, game: Game, state: State) -> Action:
        acts = game.actions(state)
        if not acts:
            raise ValueError("가능한 행동이 없습니다.")
        me = game.to_move(state)

        # 1) 깊이 1: 즉시 승리하는 수가 있으면 바로 둔다
        children = []
        for a in acts:
            child = game.result(state, a)
            if child.winner == me:
                return a
            children.append((a, child))

        # 2) 상대에게 즉시 승리를 내주지 않는 첫 수만 후보로 남긴다
        safe = [(a, c) for a, c in children
                if c.winner != -me and not self._gives_opponent_win(game, c, me)]
        if not safe:
            safe = [(a, c) for a, c in children if c.winner != -me] or children

        # 3) BFS: 깊이 순으로 펼쳐 가장 얕은 승리 국면의 첫 수를 찾는다
        queue = deque((c, a, 1) for a, c in safe)
        visited = {(state.board, state.to_move)}
        visited.update((c.board, c.to_move) for _, c in safe)
        expanded = 0
        while queue and expanded < self.max_nodes:
            s, first, depth = queue.popleft()
            if s.winner == me:
                return first
            if game.is_terminal(s) or depth >= self.max_depth:
                continue
            expanded += 1
            for a in game.actions(s):
                nxt = game.result(s, a)
                key = (nxt.board, nxt.to_move)
                if key in visited:
                    continue
                visited.add(key)
                queue.append((nxt, first, depth + 1))

        # 4) 승리 경로를 못 찾으면 안전한 수 중 무작위
        return self.rng.choice(safe)[0]







#CLI에 agent 등록===========================================================
# 에이전트 등록표: 이름 -> 인자 없이 호출하면 Agent를 돌려주는 것(보통 클래스)
# CLI(`--play 이름`, `play 이름`)가 이 표로 상대를 만든다
# 팀이 만든 에이전트는 클래스 정의 아래에 한 줄만 추가하면 CLI에서 쓸 수 있다
#   예)  AGENTS["minimax"] = MinimaxAgent
AGENTS: dict[str, Callable[[], Agent]] = {
    "random": RandomAgent,
    "minimax": MinimaxAgent,   # 순수 Minimax (끝까지 탐색)
    "alphabeta": AlphaBetaAgent,           # Minimax + 알파베타 (끝까지 탐색)
    "alphabeta_eval": AlphaBetaEvalAgent,  # Minimax + 알파베타 + 평가 함수 (기본 깊이 4)
    "alphabeta_adv": AlphaBetaAdvancedAgent,  # 위와 같고 추천 평가 함수 사용 (기본 깊이 4)
    "bfs": BfsAgent,           # 기본 최대 깊이 4
}
