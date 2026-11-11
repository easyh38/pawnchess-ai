"""tkinter GUI. 판 클릭으로 수를 두고, AGENTS의 에이전트와 대국하거나 AI끼리 관전한다.

AI 계산은 별도 스레드에서 돌리고 결과를 큐로 받아, 계산 중에도 창이 멈추지 않는다.
"""
from __future__ import annotations

import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

from pawnchess.game import BLACK, RULES, WHITE, Action, Config

from .controller import (COLOR_NAME, HUMAN, Match, parse_max_plies,
                         parse_repetition, player_choices)

LIGHT = "#eed9b6"
DARK = "#b58863"
LAST_LIGHT = "#f3e58a"
LAST_DARK = "#d6c25a"
SELECT = "#6aa84f"
TARGET = "#3d5a2a"
WHITE_FILL, WHITE_EDGE = "#fafafa", "#333333"
BLACK_FILL, BLACK_EDGE = "#262626", "#000000"
MARGIN = 26
POLL_MS = 40
HUMAN_VS_AI_DELAY_MS = 150


class PawnChessApp:
    def __init__(self, root: tk.Tk, config: Config, white: str = HUMAN, black: str = "random") -> None:
        self.root = root
        root.title("PawnChess")
        root.minsize(720, 480)

        self.match = Match(config, white, black)
        self.selected: Optional[tuple[int, int]] = None
        self.gen = 0                  # 새 게임/무르기 때마다 증가 → 이전 AI 결과 폐기
        self.thinking = False
        self.paused = False
        self.pending_after: Optional[str] = None
        self.results: "queue.Queue[tuple]" = queue.Queue()

        self._build_widgets(config, white, black)
        self.root.after(POLL_MS, self._poll_ai)
        self._refresh()
        self._maybe_start_ai()

    # ================================================================ 위젯
    def _build_widgets(self, cfg: Config, white: str, black: str) -> None:
        outer = ttk.Frame(self.root, padding=8)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(outer, background="#f4f1ea", highlightthickness=0,
                                width=480, height=480)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", lambda e: self._draw())
        self.canvas.bind("<Button-1>", self._on_click)

        side = ttk.Frame(outer, padding=(10, 0, 0, 0))
        side.grid(row=0, column=1, sticky="ns")

        # --- 게임 설정
        box = ttk.LabelFrame(side, text="게임 설정", padding=8)
        box.pack(fill="x")
        self.var_n = tk.StringVar(value=str(cfg.n))
        self.var_rule = tk.StringVar(value=cfg.rule)
        self.var_nomove = tk.StringVar(value=cfg.no_move)
        mp = cfg.max_plies
        self.var_maxp = tk.StringVar(value="none" if mp is None else str(mp))
        rp = cfg.repetition_draw
        self.var_rep = tk.StringVar(value="none" if rp is None else str(rp))
        self.var_white = tk.StringVar(value=white)
        self.var_black = tk.StringVar(value=black)

        rows = [
            ("판 크기 N", ttk.Spinbox(box, from_=2, to=10, width=10, textvariable=self.var_n)),
            ("규칙", ttk.Combobox(box, values=sorted(RULES), state="readonly",
                                width=10, textvariable=self.var_rule)),
            ("수 없음", ttk.Combobox(box, values=["lose", "draw"], state="readonly",
                                  width=10, textvariable=self.var_nomove)),
            ("최대 반수", ttk.Combobox(box, values=["auto", "none", "50", "100"],
                                   width=10, textvariable=self.var_maxp)),
            ("반복 무승부", ttk.Combobox(box, values=["none", "3"],
                                    width=10, textvariable=self.var_rep)),
            ("백(W)", ttk.Combobox(box, values=player_choices(), state="readonly",
                                 width=14, textvariable=self.var_white)),
            ("흑(B)", ttk.Combobox(box, values=player_choices(), state="readonly",
                                 width=14, textvariable=self.var_black)),
        ]
        for i, (label, w) in enumerate(rows):
            ttk.Label(box, text=label).grid(row=i, column=0, sticky="w", pady=2)
            w.grid(row=i, column=1, sticky="ew", pady=2, padx=(6, 0))
        box.columnconfigure(1, weight=1)
        ttk.Button(box, text="새 게임", command=self.new_game).grid(
            row=len(rows), column=0, columnspan=2, sticky="ew", pady=(8, 0))

        # --- 진행 제어
        ctl = ttk.LabelFrame(side, text="진행", padding=8)
        ctl.pack(fill="x", pady=(8, 0))
        self.btn_undo = ttk.Button(ctl, text="무르기", command=self.undo)
        self.btn_undo.grid(row=0, column=0, sticky="ew")
        self.btn_pause = ttk.Button(ctl, text="일시정지", command=self.toggle_pause)
        self.btn_pause.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ttk.Label(ctl, text="AI끼리 수 간격(ms)").grid(row=1, column=0, columnspan=2,
                                                 sticky="w", pady=(8, 0))
        self.var_delay = tk.IntVar(value=500)
        ttk.Scale(ctl, from_=0, to=2000, variable=self.var_delay,
                  orient="horizontal").grid(row=2, column=0, columnspan=2, sticky="ew")
        ctl.columnconfigure(0, weight=1)
        ctl.columnconfigure(1, weight=1)

        # --- 상태 + 기보
        self.var_status = tk.StringVar()
        ttk.Label(side, textvariable=self.var_status, wraplength=230,
                  font=("TkDefaultFont", 10, "bold")).pack(fill="x", pady=(10, 4))
        ttk.Label(side, text="기보").pack(anchor="w")
        lf = ttk.Frame(side)
        lf.pack(fill="both", expand=True)
        self.moves_box = tk.Listbox(lf, height=12, width=28, font=("Consolas", 10),
                                    activestyle="none")
        sb = ttk.Scrollbar(lf, orient="vertical", command=self.moves_box.yview)
        self.moves_box.configure(yscrollcommand=sb.set)
        self.moves_box.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    # ================================================================ 동작
    def _read_config(self) -> Config:
        return Config(
            n=int(self.var_n.get()),
            rule=self.var_rule.get(),
            no_move=self.var_nomove.get(),
            max_plies=parse_max_plies(self.var_maxp.get()),
            repetition_draw=parse_repetition(self.var_rep.get()),
        )

    def new_game(self) -> None:
        try:
            cfg = self._read_config()
            match = Match(cfg, self.var_white.get(), self.var_black.get())
        except ValueError as e:
            messagebox.showerror("설정 오류", str(e), parent=self.root)
            return
        self._invalidate_ai()
        self.match = match
        self.selected = None
        self.paused = False
        self._refresh()
        self._maybe_start_ai()

    def undo(self) -> None:
        if not self.match.can_undo():
            return
        self._invalidate_ai()
        self.match.undo()
        self.selected = None
        self._refresh()
        self._maybe_start_ai()

    def toggle_pause(self) -> None:
        self.paused = not self.paused
        if self.paused:
            self._invalidate_ai()
        self._refresh()
        self._maybe_start_ai()

    def _on_click(self, event) -> None:
        if not self.match.is_human_turn() or self.thinking:
            return
        sq = self._square_at(event.x, event.y)
        if sq is None:
            self.selected = None
            self._draw()
            return
        if self.selected is not None:
            for a in self.match.targets_from(self.selected):
                if a.to == sq:
                    self._play(a)
                    return
        r, c = sq
        if self.match.state.board[r][c] == self.match.to_move():
            self.selected = None if self.selected == sq else sq
        else:
            self.selected = None
        self._draw()

    def _play(self, a: Action, secs: Optional[float] = None) -> None:
        self.match.apply(a, secs)
        self.selected = None
        self._refresh()
        self._maybe_start_ai()

    # ================================================================ AI 스레드
    def _invalidate_ai(self) -> None:
        self.gen += 1
        self.thinking = False
        if self.pending_after is not None:
            self.root.after_cancel(self.pending_after)
            self.pending_after = None

    def _maybe_start_ai(self) -> None:
        m = self.match
        if (self.paused or self.thinking or self.pending_after is not None
                or m.agent_to_move() is None):
            return
        delay = int(self.var_delay.get()) if m.all_ai() else HUMAN_VS_AI_DELAY_MS
        self.pending_after = self.root.after(delay, self._launch_ai, self.gen)

    def _launch_ai(self, gen: int) -> None:
        self.pending_after = None
        if gen != self.gen:
            return
        agent = self.match.agent_to_move()
        if agent is None:
            return
        game, state = self.match.game, self.match.state
        self.thinking = True
        self._refresh()

        def work() -> None:
            t0 = time.perf_counter()
            try:
                a = agent.choose_action(game, state)
                self.results.put((gen, state, a, time.perf_counter() - t0, None))
            except Exception as e:  # 에이전트 오류는 화면에 표시
                self.results.put((gen, state, None, 0.0, e))

        threading.Thread(target=work, daemon=True).start()

    def _poll_ai(self) -> None:
        try:
            while True:
                gen, state, a, secs, err = self.results.get_nowait()
                if gen != self.gen or state is not self.match.state:
                    continue  # 새 게임/무르기 이전에 시작된 계산 결과
                self.thinking = False
                if err is not None:
                    self.paused = True
                    self._refresh()
                    messagebox.showerror("에이전트 오류", f"{type(err).__name__}: {err}",
                                         parent=self.root)
                    continue
                try:
                    self._play(a, secs)
                except ValueError as e:
                    self.paused = True
                    self._refresh()
                    messagebox.showerror("에이전트 오류", f"불법 수 {a}: {e}", parent=self.root)
        except queue.Empty:
            pass
        self.root.after(POLL_MS, self._poll_ai)

    # ================================================================ 그리기
    def _geometry(self) -> tuple[float, float, float]:
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        n = self.match.config.n
        side = max(min(w, h) - 2 * MARGIN, 40)
        cell = side / n
        x0 = (w - side) / 2
        y0 = (h - side) / 2
        return x0, y0, cell

    def _square_at(self, x: int, y: int) -> Optional[tuple[int, int]]:
        x0, y0, cell = self._geometry()
        n = self.match.config.n
        col = int((x - x0) // cell)
        disp_row = int((y - y0) // cell)
        if not (0 <= col < n and 0 <= disp_row < n) or x < x0 or y < y0:
            return None
        return (n - 1 - disp_row, col)   # 화면 위쪽 = N행

    def _draw(self) -> None:
        cv = self.canvas
        cv.delete("all")
        m = self.match
        n = m.config.n
        x0, y0, cell = self._geometry()
        last = {m.last.frm, m.last.to} if m.last else set()
        targets = {a.to: a for a in m.targets_from(self.selected)} if self.selected else {}
        font = ("TkDefaultFont", max(8, int(cell * 0.14)))

        for disp_row in range(n):
            r = n - 1 - disp_row
            for c in range(n):
                xa, ya = x0 + c * cell, y0 + disp_row * cell
                light = (r + c) % 2 == 1
                fill = (LAST_LIGHT if light else LAST_DARK) if (r, c) in last else (
                    LIGHT if light else DARK)
                cv.create_rectangle(xa, ya, xa + cell, ya + cell, fill=fill, outline="")
                if (r, c) == self.selected:
                    cv.create_rectangle(xa + 2, ya + 2, xa + cell - 2, ya + cell - 2,
                                        outline=SELECT, width=4)
                piece = m.state.board[r][c]
                if piece:
                    pad = cell * 0.16
                    fill, edge = (WHITE_FILL, WHITE_EDGE) if piece == WHITE else (BLACK_FILL, BLACK_EDGE)
                    cv.create_oval(xa + pad, ya + pad, xa + cell - pad, ya + cell - pad,
                                   fill=fill, outline=edge, width=2)
                if (r, c) in targets:
                    cx, cy = xa + cell / 2, ya + cell / 2
                    if targets[(r, c)].capture:
                        rad = cell * 0.42
                        cv.create_oval(cx - rad, cy - rad, cx + rad, cy + rad,
                                       outline=SELECT, width=4)
                    else:
                        rad = cell * 0.13
                        cv.create_oval(cx - rad, cy - rad, cx + rad, cy + rad,
                                       fill=TARGET, outline="")

        cv.create_rectangle(x0, y0, x0 + n * cell, y0 + n * cell, outline="#5a4632", width=2)
        for i in range(n):
            cv.create_text(x0 + (i + 0.5) * cell, y0 + n * cell + MARGIN / 2,
                           text=chr(ord("a") + i), font=font, fill="#5a4632")
            cv.create_text(x0 - MARGIN / 2, y0 + (i + 0.5) * cell,
                           text=str(n - i), font=font, fill="#5a4632")

    def _refresh(self) -> None:
        m = self.match
        res = m.result_text()
        color = m.to_move()
        who = m.controllers[color]
        if res:
            status = f"게임 종료: {res}  (ply {m.state.ply})"
        elif self.thinking:
            status = f"{COLOR_NAME[color]} 생각 중… ({who})"
        elif self.paused and who != HUMAN:
            status = f"일시정지 — {COLOR_NAME[color]} 차례 ({who})"
        else:
            status = f"{COLOR_NAME[color]} 차례 ({'사람' if who == HUMAN else who})"
        self.var_status.set(f"ply {m.state.ply} | {m.config.rule} | N={m.config.n}\n{status}")

        self.moves_box.delete(0, "end")
        for line in m.move_lines():
            self.moves_box.insert("end", line)
        self.moves_box.see("end")

        self.btn_undo.state(["!disabled"] if m.can_undo() else ["disabled"])
        self.btn_pause.configure(text="재개" if self.paused else "일시정지")
        self._draw()


def _enable_hidpi() -> None:
    """Windows 화면 배율(125%, 150% 등)에서 글자가 흐려지지 않게 한다."""
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def run(config: Optional[Config] = None, white: str = HUMAN, black: str = "random") -> None:
    _enable_hidpi()
    root = tk.Tk()
    PawnChessApp(root, config or Config(), white, black)
    root.mainloop()
