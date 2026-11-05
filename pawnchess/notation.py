"""표기 변환: Action <-> "a1b2", 방향 -> Action, 판 출력, 텍스트 -> State."""
from __future__ import annotations

import re
from typing import Optional

from .game import BLACK, DIRS, WHITE, Action, Config, Game, State

_MOVE_RE = re.compile(r"^([a-z])(\d+)([a-z])(\d+)$")
_SQUARE_RE = re.compile(r"^([a-z])(\d+)$")


def format_square(rc: tuple[int, int]) -> str:
    r, c = rc
    return f"{chr(ord('a') + c)}{r + 1}"


def parse_square(text: str, n: int) -> tuple[int, int]:
    m = _SQUARE_RE.match(text.strip().lower())
    if not m:
        raise ValueError(f"칸 표기가 올바르지 않습니다: '{text}' (예: a1)")
    c, r = ord(m.group(1)) - ord("a"), int(m.group(2)) - 1
    if not (0 <= r < n and 0 <= c < n):
        raise ValueError(f"판 밖의 칸입니다: '{text}' (열 a~{chr(ord('a') + n - 1)}, 행 1~{n})")
    return (r, c)


def format_move(a: Action) -> str:
    return format_square(a.frm) + format_square(a.to)


def is_move_text(text: str) -> bool:
    return bool(_MOVE_RE.match(text.strip().lower()))


def is_square_text(text: str) -> bool:
    return bool(_SQUARE_RE.match(text.strip().lower()))


def parse_move(text: str, state: State) -> Action:
    """'a1b2' -> Action. capture 여부는 도착 칸에 기물이 있는지로 정한다(합법성은 검사 안 함)."""
    m = _MOVE_RE.match(text.strip().lower())
    if not m:
        raise ValueError(f"수 표기가 올바르지 않습니다: '{text}' (예: a1a2)")
    n = len(state.board)
    frm = parse_square(m.group(1) + m.group(2), n)
    to = parse_square(m.group(3) + m.group(4), n)
    return Action(frm, to, state.board[to[0]][to[1]] != 0)


def direction_to_action(game: Game, state: State, square: str, direction: str) -> Action:
    """'a2' + 'up' -> 그 방향으로 가는 합법 수. 없으면 이유와 함께 ValueError."""
    direction = direction.lower()
    if direction not in DIRS:
        raise ValueError(f"알 수 없는 방향: '{direction}' (사용 가능: {', '.join(DIRS)})")
    frm = parse_square(square, game.config.n)
    dr, dc = DIRS[direction]
    to = (frm[0] + dr, frm[1] + dc)
    n = game.config.n
    if not (0 <= to[0] < n and 0 <= to[1] < n):
        raise ValueError("그 방향은 판 밖입니다")
    a = Action(frm, to, state.board[to[0]][to[1]] != 0)
    if a not in game.actions(state):
        raise ValueError(game.illegal_reason(state, a))
    return a


_SYMBOL = {WHITE: "W", BLACK: "B", 0: "."}


def render_board(state: State, config: Config, last: Optional[Action] = None,
                 marks: Optional[dict] = None) -> str:
    """위쪽이 N행. last의 도착 칸은 [ ], marks는 {(r,c): '<>'} 형태로 칸을 감싼다."""
    n = config.n
    who = "백(W)" if state.to_move == WHITE else "흑(B)"
    if state.winner is None:
        head = f"ply {state.ply} | 차례: {who} | 규칙: {config.rule} | N={n}"
    else:
        head = f"ply {state.ply} | 종료 | 규칙: {config.rule} | N={n}"
    marks = dict(marks or {})
    if last is not None:
        marks.setdefault(last.to, "[]")
    width = len(str(n))
    lines = [head, " " * (width + 1) + "".join(f" {chr(ord('a') + c)} " for c in range(n))]
    for r in range(n - 1, -1, -1):
        cells = ""
        for c in range(n):
            mk = marks.get((r, c), "  ")
            cells += f"{mk[0]}{_SYMBOL[state.board[r][c]]}{mk[1]}"
        lines.append(f"{r + 1:>{width}} {cells}")
    return "\n".join(lines)


def state_from_text(text: str, to_move: int = WHITE, ply: int = 0) -> State:
    """테스트/실험용. 위 행부터 'W' 'B' '.' 로 쓴다. 공백은 무시."""
    rows = [r.replace(" ", "") for r in text.strip().splitlines() if r.strip()]
    sym = {"W": WHITE, "B": BLACK, ".": 0}
    board = [[sym[ch] for ch in row] for row in reversed(rows)]
    return State(tuple(tuple(r) for r in board), to_move, ply, None)
