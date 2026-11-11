"""GUI용 대국 진행 로직 (tkinter에 의존하지 않음).

엔진(pawnchess.game)의 함수와 에이전트 등록표(pawnchess.agents.AGENTS)만 사용한다.
화면 코드(app.py)는 이 Match 객체를 통해서만 게임 상태를 바꾼다.
"""
from __future__ import annotations

from typing import Optional

from pawnchess.agents import AGENTS, Agent
from pawnchess.game import BLACK, WHITE, Action, Config, Game, State
from pawnchess.notation import format_move

HUMAN = "human"
COLOR_NAME = {WHITE: "백(W)", BLACK: "흑(B)"}


def player_choices() -> list[str]:
    """대국자 선택지: 사람 + AGENTS에 등록된 에이전트 이름."""
    return [HUMAN] + list(AGENTS)


def parse_max_plies(text: str):
    """'auto' | 'none' | 양의 정수 -> Config.max_plies 값."""
    t = text.strip().lower()
    if t == "auto":
        return "auto"
    if t in ("none", ""):
        return None
    return int(t)


def parse_repetition(text: str) -> Optional[int]:
    """'none' | 2 이상의 정수 -> Config.repetition_draw 값."""
    t = text.strip().lower()
    if t in ("none", ""):
        return None
    return int(t)


class Match:
    """한 판의 진행 상태: 현재 국면, 무르기 이력, 각 색의 대국자."""

    def __init__(self, config: Config, white: str = HUMAN, black: str = "random") -> None:
        for name in (white, black):
            if name != HUMAN and name not in AGENTS:
                raise ValueError(f"알 수 없는 대국자: {name}")
        self.config = config
        self.game = Game(config)
        self.controllers = {WHITE: white, BLACK: black}
        # 같은 에이전트를 양쪽에 골라도 인스턴스는 따로 만든다
        self.agents: dict[int, Agent] = {
            color: AGENTS[name]() for color, name in self.controllers.items() if name != HUMAN
        }
        self.state: State = self.game.initial_state()
        self.last: Optional[Action] = None
        self.history: list[tuple[State, Optional[Action]]] = []
        self.moves: list[tuple[Action, Optional[float]]] = []  # (수, AI 소요 시간)

    # ------------------------------------------------------------ 조회
    def is_over(self) -> bool:
        return self.game.is_terminal(self.state)

    def to_move(self) -> int:
        return self.game.to_move(self.state)

    def is_human_turn(self) -> bool:
        return not self.is_over() and self.controllers[self.to_move()] == HUMAN

    def has_human(self) -> bool:
        return HUMAN in self.controllers.values()

    def all_ai(self) -> bool:
        return not self.has_human()

    def agent_to_move(self) -> Optional[Agent]:
        if self.is_over():
            return None
        return self.agents.get(self.to_move())

    def legal_actions(self) -> list[Action]:
        return self.game.actions(self.state)

    def targets_from(self, square: tuple[int, int]) -> list[Action]:
        return [a for a in self.legal_actions() if a.frm == square]

    def result_text(self) -> Optional[str]:
        w = self.state.winner
        if w is None:
            return None
        return {WHITE: "백(W) 승리", BLACK: "흑(B) 승리", 0: "무승부"}[w]

    def move_lines(self) -> list[str]:
        out = []
        for i, (a, secs) in enumerate(self.moves):
            color = "W" if i % 2 == 0 else "B"
            t = f"  ({secs:.2f}s)" if secs is not None else ""
            out.append(f"{i + 1:>3}. {color} {format_move(a)}{'x' if a.capture else ''}{t}")
        return out

    # ------------------------------------------------------------ 변경
    def apply(self, a: Action, secs: Optional[float] = None) -> None:
        """수를 둔다. 불법 수면 ValueError (상태는 그대로)."""
        new = self.game.result(self.state, a)
        self.history.append((self.state, self.last))
        self.moves.append((a, secs))
        self.state, self.last = new, a

    def can_undo(self) -> bool:
        return bool(self.history) and self.has_human()

    def undo(self) -> bool:
        """사람이 둘 차례까지 되돌린다 (AI 수는 함께 무른다)."""
        if not self.can_undo():
            return False
        self._pop()
        while self.history and not self.is_human_turn():
            self._pop()
        return True

    def _pop(self) -> None:
        self.state, self.last = self.history.pop()
        self.moves.pop()
