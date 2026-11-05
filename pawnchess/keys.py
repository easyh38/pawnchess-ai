"""OS별 키 입력을 read_key() 하나로 흡수한다.

반환값: 'up' 'down' 'left' 'right' 'enter' 'esc' 또는 입력한 문자 한 글자.
"""
import sys

try:
    import msvcrt  # Windows
except ImportError:
    msvcrt = None

_WIN_ARROWS = {"H": "up", "P": "down", "K": "left", "M": "right"}
_ANSI_ARROWS = {"A": "up", "B": "down", "D": "left", "C": "right"}


def read_key() -> str:
    if msvcrt is not None:
        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            return _WIN_ARROWS.get(msvcrt.getwch(), "")
        return _normalize(ch)
    return _read_key_posix()


def _normalize(ch: str) -> str:
    if ch in ("\r", "\n"):
        return "enter"
    if ch == "\x1b":
        return "esc"
    if ch == "\x03":
        raise KeyboardInterrupt
    return ch


def _read_key_posix() -> str:
    import select
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            if select.select([sys.stdin], [], [], 0.05)[0]:
                seq = sys.stdin.read(2)
                if len(seq) == 2 and seq[0] in "[O":
                    return _ANSI_ARROWS.get(seq[1], "")
                return ""
            return "esc"
        return _normalize(ch)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
