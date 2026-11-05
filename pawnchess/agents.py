"""에이전트 인터페이스. 탐색 에이전트(Minimax 등)는 팀이 이 인터페이스로 추가한다."""
from __future__ import annotations

import random
from typing import Callable, Optional

from .game import Action, Game, State
from .notation import (direction_to_action, format_move, is_move_text,
                       is_square_text, parse_move, render_board)

#기본 세팅===============================================================================================

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































#CLI에 agent 등록===========================================================
# 에이전트 등록표: 이름 -> 인자 없이 호출하면 Agent를 돌려주는 것(보통 클래스)
# CLI(`--play 이름`, `play 이름`)가 이 표로 상대를 만든다
# 팀이 만든 에이전트는 클래스 정의 아래에 한 줄만 추가하면 CLI에서 쓸 수 있다
#   예)  AGENTS["minimax"] = MinimaxAgent
AGENTS: dict[str, Callable[[], Agent]] = {"random": RandomAgent}
