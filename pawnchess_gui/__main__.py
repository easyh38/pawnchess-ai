"""실행: python -m pawnchess_gui [--n 4] [--rule pawn] [--white human] [--black random]"""
from __future__ import annotations

import argparse
from typing import Optional

from pawnchess.game import RULES, Config

from .controller import parse_max_plies, parse_repetition, player_choices


def main(argv: Optional[list[str]] = None) -> None:
    p = argparse.ArgumentParser(prog="python -m pawnchess_gui", description="PawnChess GUI")
    p.add_argument("--n", type=int, default=4, help="판 크기 (기본 4)")
    p.add_argument("--rule", choices=sorted(RULES), default="pawn")
    p.add_argument("--no-move", choices=["lose", "draw"], default="lose")
    p.add_argument("--max-plies", default="auto", help="정수 | auto | none")
    p.add_argument("--repetition-draw", default="none", help="정수 | none")
    p.add_argument("--white", choices=player_choices(), default="human", help="백 대국자")
    p.add_argument("--black", choices=player_choices(), default="random", help="흑 대국자")
    args = p.parse_args(argv)

    config = Config(n=args.n, rule=args.rule, no_move=args.no_move,
                    max_plies=parse_max_plies(args.max_plies),
                    repetition_draw=parse_repetition(args.repetition_draw))

    from .app import run  # tkinter는 실제 실행할 때만 불러온다
    run(config, args.white, args.black)


if __name__ == "__main__":
    main()
