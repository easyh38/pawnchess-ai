"""터미널 인터페이스: 명령어 모드 + 방향키 모드.

실행: python -m pawnchess.cli --n 4 --rule pawn
"""
from __future__ import annotations

import argparse
import dataclasses
import os
import sys
from typing import Optional

from .agents import AGENTS, Agent, RandomAgent
from .game import BLACK, DIRS, WHITE, Action, Config, Game, State
from .notation import (direction_to_action, format_move, is_move_text,
                       is_square_text, parse_move, render_board)
from .runner import run_matches

HELP = """\
show                 판 출력
state                내부 State 원본(repr)
actions              합법 수 목록
move a1a2 | a1a2     수 두기
move 3               actions 목록의 3번 수
a2 up | move a2 up   방향으로 두기 (화면 기준: up down left right upleft upright downleft downright)
peek a1a2            판을 바꾸지 않고 결과 국면만 보기
undo                 한 수 무르기 (상대 에이전트가 있으면 내 차례까지)
reset                처음부터
set <키> <값>        n / rule / max_plies / no_move / repetition_draw 변경 후 reset
                     (max_plies, repetition_draw는 none 가능, max_plies는 auto 가능)
play <에이전트> [w|b] 내가 w(기본)/b를 잡고 등록된 에이전트(agents.AGENTS, 예: random)와 대국
                     play human 으로 해제
auto random random N [seed]   무작위 대 무작위 N판 통계
terminal             is_terminal / utility 출력
keys                 방향키 모드 (q로 복귀)
help, quit"""


class Session:
    def __init__(self, config: Config) -> None:
        self.opponent: Optional[Agent] = None
        self.opponent_color = BLACK
        self.set_config(config)

    # ------------------------------------------------------------ 상태
    def set_config(self, config: Config) -> list[str]:
        self.config = config
        self.game = Game(config)
        return self.reset()

    def reset(self) -> list[str]:
        self.state = self.game.initial_state()
        self.history: list[tuple[State, Optional[Action]]] = []
        self.last: Optional[Action] = None
        return [render_board(self.state, self.config)] + self._run_opponent()

    def board_text(self) -> str:
        return render_board(self.state, self.config, self.last)

    def _result_line(self) -> list[str]:
        s = self.state
        if s.winner is None:
            return []
        name = {WHITE: "백(W) 승리", BLACK: "흑(B) 승리", 0: "무승부"}[s.winner]
        return [f"*** 게임 종료: {name} ***"]

    def _run_opponent(self) -> list[str]:
        out: list[str] = []
        while (self.opponent is not None and not self.game.is_terminal(self.state)
               and self.state.to_move == self.opponent_color):
            a = self.opponent.choose_action(self.game, self.state)
            self.history.append((self.state, self.last))
            self.state, self.last = self.game.result(self.state, a), a
            out.append(f"상대 수: {format_move(a)}")
            out.append(self.board_text())
        return out + self._result_line()

    def do_move(self, a: Action) -> list[str]:
        if self.game.is_terminal(self.state):
            return ["게임이 이미 끝났습니다. reset 하세요."]
        try:
            new = self.game.result(self.state, a)
        except ValueError as e:
            return [f"불가: {e}"]
        self.history.append((self.state, self.last))
        self.state, self.last = new, a
        out = [self.board_text()] + self._result_line()
        if not self.game.is_terminal(self.state):
            out += self._run_opponent()
        return out

    def undo(self) -> list[str]:
        if not self.history:
            return ["무를 수가 없습니다"]
        self.state, self.last = self.history.pop()
        while (self.opponent is not None and self.history
               and self.state.to_move == self.opponent_color):
            self.state, self.last = self.history.pop()
        return [self.board_text()] + self._run_opponent()

    # ------------------------------------------------------------ 명령
    def resolve_move(self, args: list[str]) -> Action:
        acts = self.game.actions(self.state)
        if len(args) == 1 and args[0].isdigit():
            i = int(args[0])
            if not 1 <= i <= len(acts):
                raise ValueError(f"번호는 1~{len(acts)} 범위입니다")
            return acts[i - 1]
        if len(args) == 1 and is_move_text(args[0]):
            a = parse_move(args[0], self.state)
            if a not in acts:
                raise ValueError(self.game.illegal_reason(self.state, a))
            return a
        if len(args) == 2 and is_square_text(args[0]):
            return direction_to_action(self.game, self.state, args[0], args[1])
        raise ValueError("수 표기를 이해하지 못했습니다 (예: a1a2 / 3 / a2 up)")

    def execute(self, line: str) -> list[str]:
        tokens = line.strip().lower().split()
        if not tokens:
            return []
        cmd, args = tokens[0], tokens[1:]
        try:
            if is_move_text(cmd) or (is_square_text(cmd) and len(tokens) == 2):
                return self.do_move(self.resolve_move(tokens))
            handler = getattr(self, "cmd_" + cmd, None)
            if handler is None:
                return [f"알 수 없는 명령: '{cmd}' (help 참고)"]
            return handler(args)
        except ValueError as e:
            return [f"오류: {e}"]

    def cmd_help(self, args): return [HELP]
    def cmd_show(self, args): return [self.board_text()]
    def cmd_state(self, args): return [repr(self.state)]
    def cmd_reset(self, args): return self.reset()
    def cmd_undo(self, args): return self.undo()

    def cmd_actions(self, args):
        acts = self.game.actions(self.state)
        if not acts:
            return ["합법 수 없음"]
        return [f"{i:>3}: {format_move(a)}{'  (잡기)' if a.capture else ''}"
                for i, a in enumerate(acts, 1)]

    def cmd_move(self, args):
        if not args:
            raise ValueError("사용법: move a1a2 | move 3 | move a2 up")
        return self.do_move(self.resolve_move(args))

    def cmd_peek(self, args):
        if not args:
            raise ValueError("사용법: peek a1a2")
        a = self.resolve_move(args)
        return ["(미리보기 — 실제 판은 바뀌지 않음)",
                render_board(self.game.result(self.state, a), self.config, a)]

    def cmd_terminal(self, args):
        s = self.state
        out = [f"is_terminal = {self.game.is_terminal(s)}"]
        if self.game.is_terminal(s):
            out += [f"utility(백) = {self.game.utility(s, WHITE):+.0f}",
                    f"utility(흑) = {self.game.utility(s, BLACK):+.0f}"]
        return out

    def cmd_set(self, args):
        if len(args) != 2:
            raise ValueError("사용법: set <n|rule|max_plies|no_move|repetition_draw> <값>")
        key, val = args
        if key not in {f.name for f in dataclasses.fields(Config)}:
            raise ValueError(f"알 수 없는 설정 키: {key}")
        if key in ("n", "max_plies", "repetition_draw"):
            if val == "none" and key != "n":
                parsed = None
            elif val == "auto" and key == "max_plies":
                parsed = "auto"
            elif val.isdigit():
                parsed = int(val)
            else:
                raise ValueError(f"{key}의 값이 올바르지 않습니다: {val}")
        else:
            parsed = val
        new = dataclasses.replace(self.config, **{key: parsed})
        return [f"설정 변경: {key}={parsed} → reset"] + self.set_config(new)

    def cmd_play(self, args):
        names = "|".join(AGENTS)
        if not args or (args[0] != "human" and args[0] not in AGENTS):
            raise ValueError(f"사용법: play <{names}> [w|b] | play human")
        if args[0] == "human":
            self.opponent = None
            return ["사람 대 사람 모드"]
        me = args[1] if len(args) > 1 else "w"
        if me not in ("w", "b"):
            raise ValueError("색은 w 또는 b")
        self.opponent = AGENTS[args[0]]()
        self.opponent_color = BLACK if me == "w" else WHITE
        return [f"{args[0]} 에이전트와 대국 (나: " + ("백" if me == "w" else "흑") + ")"] + self.reset()

    def cmd_auto(self, args):
        if len(args) < 3 or args[0] != "random" or args[1] != "random" or not args[2].isdigit():
            raise ValueError("사용법: auto random random N [seed]")
        seed = int(args[3]) if len(args) > 3 and args[3].isdigit() else None
        a = RandomAgent(seed)
        b = RandomAgent(None if seed is None else seed + 1)
        return [run_matches(self.game, a, b, int(args[2])).summary()]

    def cmd_keys(self, args):
        keys_mode(self)
        return [self.board_text()]

    def cmd_quit(self, args): raise SystemExit(0)
    cmd_exit = cmd_quit


# ------------------------------------------------------------ 방향키 모드
# 방향키 모드의 대각선 입력 (vi 스타일): 화면 기준 ↖ ↗ ↙ ↘
DIAG_KEYS = {"y": "upleft", "u": "upright", "b": "downleft", "n": "downright"}


def _clear() -> None:
    print("\033[2J\033[H", end="")


def keys_mode(sess: Session) -> None:
    from .keys import read_key

    if os.name == "nt":
        os.system("")  # Windows 터미널에서 ANSI 이스케이프 활성화
    game, n = sess.game, sess.config.n
    cur = (0, 0)
    selected: Optional[tuple[int, int]] = None
    pending: Optional[Action] = None
    msg = ""
    while True:
        marks = {cur: "<>"}
        moves: list[Action] = []
        if selected is not None:
            marks[selected] = "**"
            moves = [a for a in game.actions(sess.state) if a.frm == selected]
            for a in moves:
                marks[a.to] = "()"
            if pending is not None:
                marks[pending.to] = "{}"
        _clear()
        print(render_board(sess.state, sess.config, sess.last, marks))
        for line in sess._result_line():
            print(line)
        if selected is not None:
            print("이동 선택: 방향키(상하좌우) | 대각선 잡기 y=↖ u=↗ b=↙ n=↘ | 숫자 → Enter 확정, Esc 취소")
            for i, a in enumerate(moves, 1):
                print(f"  {i}: {format_move(a)}{' (잡기)' if a.capture else ''}")
        else:
            print("방향키: 커서 이동 | Enter: 기물 선택 | q: 명령어 모드")
        if msg:
            print(msg)
            msg = ""
        key = read_key()
        if key == "q":
            return
        if sess.game.is_terminal(sess.state):
            msg = "게임이 끝났습니다. q로 나가 reset 하세요."
            continue
        if selected is None:
            if key in DIRS and key in ("up", "down", "left", "right"):
                dr, dc = DIRS[key]
                cur = (min(n - 1, max(0, cur[0] + dr)), min(n - 1, max(0, cur[1] + dc)))
            elif key == "enter":
                if sess.state.board[cur[0]][cur[1]] != sess.state.to_move:
                    msg = "자기 차례의 기물을 선택하세요"
                elif not any(a.frm == cur for a in game.actions(sess.state)):
                    msg = "그 기물은 움직일 수 없습니다"
                else:
                    selected, pending = cur, None
        else:
            if key in ("up", "down", "left", "right") or key in DIAG_KEYS:
                dr, dc = DIRS[DIAG_KEYS.get(key, key)]
                hit = [a for a in moves if (a.to[0] - a.frm[0], a.to[1] - a.frm[1]) == (dr, dc)]
                if hit:
                    pending = hit[0]
                else:
                    msg = "그 방향으로는 둘 수 없습니다 (대각선 잡기: y u b n 또는 숫자 키)"
            elif key.isdigit() and 1 <= int(key) <= len(moves):
                pending = moves[int(key) - 1]
            elif key == "enter":
                if pending is None:
                    msg = "먼저 이동 방향을 고르세요"
                else:
                    sess.do_move(pending)
                    cur = pending.to
                    selected = pending = None
            elif key == "esc":
                selected = pending = None


# ------------------------------------------------------------ 진입점
def _opt_int(v: str) -> Optional[int]:
    return None if v.lower() == "none" else int(v)


def main(argv: Optional[list[str]] = None) -> None:
    p = argparse.ArgumentParser(prog="pawnchess.cli")
    p.add_argument("--n", type=int, default=4)
    p.add_argument("--rule", choices=["pawn", "cross"], default="pawn")
    p.add_argument("--no-move", choices=["lose", "draw"], default="lose")
    p.add_argument("--max-plies", default="auto", help="정수 | auto | none")
    p.add_argument("--repetition-draw", default="none", help="정수 | none")
    p.add_argument("--play", choices=list(AGENTS),
                   help="시작부터 등록된 에이전트와 대국 (agents.AGENTS에 등록된 이름)")
    ns = p.parse_args(argv)
    max_plies = ns.max_plies if ns.max_plies == "auto" else _opt_int(ns.max_plies)
    try:
        cfg = Config(ns.n, ns.rule, ns.no_move, max_plies,
                     _opt_int(ns.repetition_draw))
    except ValueError as e:
        p.error(str(e))
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    sess = Session(cfg)
    if ns.play:
        print("\n".join(sess.cmd_play([ns.play])))
    else:
        print(sess.board_text())
    print("help 로 명령어 확인")
    while True:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return
        try:
            out = sess.execute(line)
        except SystemExit:
            return
        if out:
            print("\n".join(out))


if __name__ == "__main__":
    main()
