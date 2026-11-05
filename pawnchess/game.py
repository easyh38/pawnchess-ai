"""게임 환경: State, Action, Config, Game (규칙 세트 pawn / cross).

알고리즘은 Game의 6개 함수(initial_state, to_move, actions, result,
is_terminal, utility)만 호출한다. 판 크기와 규칙은 Config로 바꾼다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterator, Optional, Union

WHITE = 1
BLACK = -1
Player = int

# 화면 기준 방향 (row 인덱스는 위쪽이 커진다: row 0 = 1행 = 백 쪽)
DIRS: dict[str, tuple[int, int]] = {
    "up": (1, 0),
    "down": (-1, 0),
    "left": (0, -1),
    "right": (0, 1),
    "upleft": (1, -1),
    "upright": (1, 1),
    "downleft": (-1, -1),
    "downright": (-1, 1),
}

DEFAULT_MAX_PLIES = {"pawn": None, "cross": 50}


@dataclass(frozen=True)
class Config:
    n: int = 4
    rule: str = "pawn"                      # "pawn" | "cross"
    no_move: str = "lose"                   # 둘 수 없을 때: "lose" | "draw"
    max_plies: Union[int, str, None] = "auto"  # "auto"=규칙별 기본값, None=제한 없음
    repetition_draw: Optional[int] = None   # 같은 국면 k회 → 무승부 (None=끔)

    def __post_init__(self) -> None:
        if not isinstance(self.n, int) or self.n < 2:
            raise ValueError("n은 2 이상의 정수여야 합니다")
        if self.rule not in RULES:
            raise ValueError(f"rule은 {sorted(RULES)} 중 하나여야 합니다")
        if self.no_move not in ("lose", "draw"):
            raise ValueError("no_move는 'lose' 또는 'draw'")
        if self.max_plies not in ("auto", None) and not (
            isinstance(self.max_plies, int) and self.max_plies > 0
        ):
            raise ValueError("max_plies는 양의 정수, 'auto', None 중 하나")
        if self.repetition_draw is not None and (
            not isinstance(self.repetition_draw, int) or self.repetition_draw < 2
        ):
            raise ValueError("repetition_draw는 2 이상의 정수 또는 None")

    @property
    def effective_max_plies(self) -> Optional[int]:
        if self.max_plies == "auto":
            return DEFAULT_MAX_PLIES[self.rule]
        return self.max_plies  # type: ignore[return-value]


@dataclass(frozen=True)
class Action:
    frm: tuple[int, int]   # (row, col), 0-based
    to: tuple[int, int]
    capture: bool


@dataclass(frozen=True)
class State:
    board: tuple[tuple[int, ...], ...]   # board[row][col]: 0 빈칸, +1 백, -1 흑
    to_move: int                          # +1 백, -1 흑
    ply: int                              # 지금까지 둔 반수
    winner: Optional[int] = None          # 종료 시 +1 / -1 / 0(무승부), 진행 중 None
    # 반복 국면 이력. repetition_draw를 켰을 때만 채워진다.
    # compare=False → 동등성/해시에는 포함되지 않는다(국면 = board+to_move+ply+winner).
    # 따라서 이력이 달라도 같은 국면으로 취급된다는 점에 유의.
    history: tuple = field(default=(), compare=False, repr=False)


# ---------------------------------------------------------------- 이동 생성
# 기물 종류를 추가할 때는 이 함수들처럼 (board, r, c, cfg) -> Action 생성기를
# 만들어 RULES에 등록하고, 기물별로 분기하면 된다.
def _pawn_moves(board, r: int, c: int, cfg: Config) -> Iterator[Action]:
    color = board[r][c]
    n = cfg.n
    fr = r + color
    if not 0 <= fr < n:
        return
    if board[fr][c] == 0:
        yield Action((r, c), (fr, c), False)
    for dc in (-1, 1):
        nc = c + dc
        if 0 <= nc < n and board[fr][nc] == -color:
            yield Action((r, c), (fr, nc), True)


_CROSS_ORDER = ("up", "down", "left", "right")


def _cross_moves(board, r: int, c: int, cfg: Config) -> Iterator[Action]:
    color = board[r][c]
    n = cfg.n
    # 이동: 동·서·남·북 한 칸 (빈 칸으로만)
    for name in _CROSS_ORDER:
        dr, dc = DIRS[name]
        nr, nc = r + dr, c + dc
        if 0 <= nr < n and 0 <= nc < n and board[nr][nc] == 0:
            yield Action((r, c), (nr, nc), False)
    # 잡기: 대각선 앞 한 칸 (pawn과 동일)
    fr = r + color
    if 0 <= fr < n:
        for dc in (-1, 1):
            nc = c + dc
            if 0 <= nc < n and board[fr][nc] == -color:
                yield Action((r, c), (fr, nc), True)


RULES: dict[str, Callable[..., Iterator[Action]]] = {
    "pawn": _pawn_moves,
    "cross": _cross_moves,
}


def goal_row(player: Player, n: int) -> int:
    return n - 1 if player == WHITE else 0


class Game:
    def __init__(self, config: Optional[Config] = None, **kwargs) -> None:
        if config is not None and kwargs:
            raise ValueError("config와 키워드 인자를 함께 쓸 수 없습니다")
        self.config = config if config is not None else Config(**kwargs)
        self._gen = RULES[self.config.rule]

    # ------------------------------------------------------ 6개 핵심 함수
    def initial_state(self) -> State:
        n = self.config.n
        board = [[0] * n for _ in range(n)]
        board[0] = [WHITE] * n
        board[n - 1] = [BLACK] * n
        frozen = tuple(tuple(row) for row in board)
        history = ((frozen, WHITE),) if self.config.repetition_draw else ()
        return State(frozen, WHITE, 0, None, history)

    def to_move(self, s: State) -> Player:
        return s.to_move

    def actions(self, s: State) -> list[Action]:
        """합법 수. 순서는 (row, col) 오름차순 → 기물별 생성 순서로 결정적."""
        if s.winner is not None:
            return []
        out: list[Action] = []
        board = s.board
        for r in range(self.config.n):
            row = board[r]
            for c in range(self.config.n):
                if row[c] == s.to_move:
                    out.extend(self._gen(board, r, c, self.config))
        return out

    def result(self, s: State, a: Action) -> State:
        """수를 둔 뒤의 새 State. s는 변경하지 않는다."""
        if s.winner is not None:
            raise ValueError("이미 끝난 게임입니다")
        if a not in self.actions(s):
            raise ValueError(self.illegal_reason(s, a))
        cfg = self.config
        rows = [list(row) for row in s.board]
        (fr, fc), (tr, tc) = a.frm, a.to
        rows[tr][tc] = rows[fr][fc]
        rows[fr][fc] = 0
        board = tuple(tuple(row) for row in rows)
        mover, nxt, ply = s.to_move, -s.to_move, s.ply + 1

        history = s.history
        if cfg.repetition_draw:
            history = history + ((board, nxt),)

        winner = self._winner_after(board, mover, nxt, tr, ply, history)
        return State(board, nxt, ply, winner, history)

    def is_terminal(self, s: State) -> bool:
        return s.winner is not None

    def utility(self, s: State, player: Player) -> float:
        if s.winner is None:
            raise ValueError("종료되지 않은 국면에서는 utility를 정의하지 않습니다")
        if s.winner == 0:
            return 0.0
        return 1.0 if s.winner == player else -1.0

    # ------------------------------------------------------------- 보조
    def _winner_after(self, board, mover, nxt, to_row, ply, history) -> Optional[int]:
        cfg = self.config
        if to_row == goal_row(mover, cfg.n):
            return mover
        if not any(nxt in row for row in board):
            return mover
        probe = State(board, nxt, ply, None)
        if not self.actions(probe):
            return mover if cfg.no_move == "lose" else 0
        limit = cfg.effective_max_plies
        if limit is not None and ply >= limit:
            return 0
        if cfg.repetition_draw and history.count((board, nxt)) >= cfg.repetition_draw:
            return 0
        return None

    def illegal_reason(self, s: State, a: Action) -> str:
        n = self.config.n
        (fr, fc), (tr, tc) = a.frm, a.to
        for r, c in (a.frm, a.to):
            if not (0 <= r < n and 0 <= c < n):
                return "판 밖의 칸입니다"
        piece = s.board[fr][fc]
        if piece == 0:
            return "출발 칸에 기물이 없습니다"
        if piece != s.to_move:
            return "상대 기물입니다 (자기 차례의 기물만 움직일 수 있습니다)"
        target = s.board[tr][tc]
        if target == piece:
            return "도착 칸에 자기 기물이 있습니다"
        legal = [x for x in self.actions(s) if x.frm == a.frm]
        if not legal:
            return "그 기물은 움직일 수 있는 수가 없습니다"
        return "이 규칙에서는 불가능한 이동입니다"
