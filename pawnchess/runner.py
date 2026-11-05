"""대국 실행기, 대량 대국 통계, 호출 횟수 계측 래퍼."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from .agents import Agent
from .game import BLACK, WHITE, Action, Game, State


@dataclass
class GameRecord:
    moves: list[Action] = field(default_factory=list)
    times: list[float] = field(default_factory=list)   # 수마다 걸린 시간(초)
    winner: Optional[int] = None                        # +1 백 / -1 흑 / 0 무승부
    final_state: Optional[State] = None

    @property
    def plies(self) -> int:
        return len(self.moves)


def play_game(game: Game, agent_white: Agent, agent_black: Agent,
              on_move: Optional[Callable[[State, Action], None]] = None) -> GameRecord:
    agents = {WHITE: agent_white, BLACK: agent_black}
    s = game.initial_state()
    rec = GameRecord()
    while not game.is_terminal(s):
        t0 = time.perf_counter()
        a = agents[game.to_move(s)].choose_action(game, s)
        rec.times.append(time.perf_counter() - t0)
        rec.moves.append(a)
        s = game.result(s, a)
        if on_move:
            on_move(s, a)
    rec.winner = s.winner
    rec.final_state = s
    return rec


@dataclass
class MatchStats:
    n_games: int = 0
    a_wins: int = 0
    b_wins: int = 0
    draws: int = 0
    # 색깔별 집계: {"white"/"black": [A 승, A 패, 무]}  (A 에이전트 관점)
    a_by_color: dict = field(default_factory=lambda: {"white": [0, 0, 0], "black": [0, 0, 0]})
    mean_plies: float = 0.0
    mean_time_a: float = 0.0   # A의 수당 평균 시간(초)
    mean_time_b: float = 0.0

    def summary(self) -> str:
        lines = [
            f"{self.n_games}판: A {self.a_wins}승 / B {self.b_wins}승 / 무 {self.draws}"
            f"  (A 승률 {self.a_wins / max(1, self.n_games):.1%})",
        ]
        for color, (w, l, d) in self.a_by_color.items():
            lines.append(f"  A가 {color}일 때: {w}승 {l}패 {d}무")
        lines.append(f"  평균 반수 {self.mean_plies:.1f} | 수당 시간 A {self.mean_time_a * 1e3:.3f}ms"
                     f" / B {self.mean_time_b * 1e3:.3f}ms")
        return "\n".join(lines)


def run_matches(game: Game, agent_a: Agent, agent_b: Agent, n: int,
                swap_colors: bool = True) -> MatchStats:
    """n판. swap_colors면 홀수 번째 판에서 A가 흑을 잡는다."""
    st = MatchStats(n_games=n)
    total_plies = 0
    ta: list[float] = []
    tb: list[float] = []
    for i in range(n):
        a_white = not (swap_colors and i % 2 == 1)
        rec = play_game(game, agent_a if a_white else agent_b,
                        agent_b if a_white else agent_a)
        total_plies += rec.plies
        a_color = WHITE if a_white else BLACK
        for k, t in enumerate(rec.times):   # 짝수 인덱스 = 백이 둔 수
            white_moved = k % 2 == 0
            (ta if white_moved == a_white else tb).append(t)
        slot = st.a_by_color["white" if a_white else "black"]
        if rec.winner == 0:
            st.draws += 1
            slot[2] += 1
        elif rec.winner == a_color:
            st.a_wins += 1
            slot[0] += 1
        else:
            st.b_wins += 1
            slot[1] += 1
    st.mean_plies = total_plies / max(1, n)
    st.mean_time_a = sum(ta) / len(ta) if ta else 0.0
    st.mean_time_b = sum(tb) / len(tb) if tb else 0.0
    return st


class CountingGame:
    """Game을 감싸 actions/result 호출 횟수를 센다. 나머지는 그대로 위임."""

    def __init__(self, game: Game) -> None:
        self._game = game
        self.actions_calls = 0
        self.result_calls = 0

    def reset_counts(self) -> None:
        self.actions_calls = 0
        self.result_calls = 0

    def actions(self, s):
        self.actions_calls += 1
        return self._game.actions(s)

    def result(self, s, a):
        self.result_calls += 1
        return self._game.result(s, a)

    def __getattr__(self, name):
        return getattr(self._game, name)
