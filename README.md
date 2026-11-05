# PawnChess — 폰 체스 변형 게임 환경

> 인공지능 입문 팀프로젝트
> 이 저장소는 **게임 환경(Environment) + 터미널 인터페이스**까지만 구현되어 있습니다.
> **탐색 알고리즘(미니맥스, 알파베타, 평가 함수)은 팀이 직접 구현**하며, 이 코드에는 포함되어 있지 않습니다.

- 언어/의존성: Python 3.10+ , 표준 라이브러리만 사용 (검증 환경: Python 3.14.3, Windows 11)

---

## 1. 시작

```powershell
python -m pawnchess.cli                          # 4x4 pawn 규칙 (기본)
python -m pawnchess.cli --n 5 --rule pawn        # 5x5
python -m pawnchess.cli --rule cross             # 비교용 변형: 십자 이동
python -m pawnchess.cli --play random            # 시작부터 RandomAgent와 대국
python -m pawnchess.cli --play minimax           # 내가 만든 에이전트와 대국 (먼저 등록 필요: 3장 참고)
```

CLI 옵션:
`--n`(기본 4) : 판 크기 선택
`--rule {pawn,cross}`(기본 pawn = 메인 규칙, cross = 비교용 변형) : 폰의 이동 방식
`--no-move {lose,draw}`(기본 lose = 둘 수 없는 쪽이 패배, draw = 무승부) : 자기 차례에서 둘 수 있는 수가 없을 때의 처리 방식
`--max-plies <정수|auto|none>`(정수 = 그 수만큼 두면 무승부, auto = 규칙별 기본값(cross : 50, pawn : 제한 없음), none = 제한 없음) : 최대 진행수 제한
`--repetition-draw <정수|none>`(정수 = 그 수만큼 반복되면 무승부, none = 반복 무승부 판정을 끔) : 같은 국면 반복 시 무승부 처리
`--play <에이전트 이름>`(기본은 `random`뿐, 내 에이전트 추가 방법은 3장) : 시작부터 그 에이전트와 대국. 이름은 `pawnchess/agents.py`의 `AGENTS` 등록표에 있는 것만 가능

화면 예시: 
(N=4): 백 `W`, 흑 `B`, 빈칸 `.`. 위쪽이 N행이고 마지막 수는 `[ ]`로 표시됩니다.

```
  ply 3 | 차례: 백(W) | 규칙: pawn | N=4
    a b c d
 4  B B . B
 3  . . B .
 2  W . . .
 1  . W W W
```

### CLI 명령어 (명령어 모드)

| 명령 | 동작 | 대응 개념 |
|---|---|---|
| `show` | 판 출력 | state |
| `state` | 내부 State 원본 출력 (repr) | state |
| `actions` | 합법 수 목록에 번호를 붙여 출력 | actions(s) |
| `move a1a2` 또는 `a1a2` | 수 두기 | result(s, a) = transition |
| `move 3` | `actions` 목록의 3번 수 두기 | |
| `a2 up` / `a2 left` … | 방향으로 두기 (`cross`: 4방향 이동 + `upleft`/`upright`(백)·`downleft`/`downright`(흑) 대각선 잡기, `pawn`: `up`=직진, 대각선=잡기) | |
| `peek a1a2` | 판을 바꾸지 않고 결과 국면만 미리 출력 | result(s, a) 확인 |
| `undo` | 한 수 무르기 (이력 스택) | |
| `reset` | 처음부터 | initial_state() |
| `set n 5` / `set rule cross` / `set max_plies 40` … | 설정 변경 후 reset | |
| `play <에이전트> [w\|b]` | 내가 백(w, 기본)/흑(b)을 잡고 등록된 에이전트와 대국 (예: `play random w`). `play human`으로 사람 대 사람 복귀 | |
| `auto random random 100 [seed]` | 무작위 대 무작위 100판 통계 (이 명령은 random 전용) | 성과 측도 |
| `terminal` | is_terminal / utility 값 출력 | |
| `keys` | 방향키 모드 (시연 E 참고) | |
| `help`, `quit` | | |

- 잘못된 입력·불법 수는 이유를 알려 주고 상태를 바꾸지 않습니다.

---

## 2. 게임 개요와 규칙

### 2-1. 개요

| 항목 | 내용 |
|---|---|
| 게임 | N×N 폰 체스 변형 (시작: **4×4**, 이후 5×5 이상으로 확장) |
| 확장 축 ① | 판 크기 N ↑ → 게임 길이(깊이 m) 증가 |
| 확장 축 ② | 이동 규칙/기물 변경 → 분기 계수 b 증가 |
| 사용할 알고리즘 (팀 구현) | 미니맥스 → 알파베타 가지치기 → 깊이 제한 + 평가 함수 → (선택) 반복 심화·수 순서 |

**PEAS**

| | 내용 |
|---|---|
| P (성과 측도) | 특정 상대(무작위 에이전트 등)에 대한 승률, 수당 계산 시간, 탐색 노드 수 |
| E (환경) | N×N 판, **상대 플레이어** |
| A (작동기) | 합법적인 수 하나를 골라 출력 (기물을 옮기는 연산) |
| S (감지기) | 현재 판 전체 상태(기물 위치, 차례) 입력 |

**환경 분석**

| 기준 | 값 |
|---|---|
| 관측 가능성 | fully observable |
| 결정성 | **deterministic** |
| 에피소드 | sequential |
| 정적/동적 | static (수당 시간 제한을 두면 semidynamic) |
| 이산/연속 | discrete |
| 환경 지식 | known |
| 에이전트 수 | multi-agent |

→ 결정적·2인·제로섬·완전 정보 게임이므로 미니맥스 계열 알고리즘이 적합

### 2-2. 공통 규칙
- 판: N×N. 열은 `a, b, c, ...`, 행은 `1..N`. **1행이 백(White) 쪽, N행이 흑(Black) 쪽.**
- 시작 배치: 백 기물이 1행 전체, 흑 기물이 N행 전체를 채웁니다.
- **백이 먼저 둡니다.**
- 승리 조건 (어느 하나라도 만족하면 그 수를 둔 쪽이 승리):
  1. 자기 기물이 **상대편 끝 줄**에 도달 (백은 N행, 흑은 1행)
  2. 상대 기물을 **모두 잡음**
  3. 상대가 자기 차례에 **둘 수 있는 수가 없음** → 둘 수 없는 쪽이 패배 (`--no-move`로 변경 가능)

### 2-3. 규칙 세트 `pawn` (메인 규칙, Hexapawn 일반화)
- 이동: **앞으로 한 칸**, 그 칸이 비어 있을 때만 (백은 위로, 흑은 아래로)
- 잡기: **앞쪽 대각선 한 칸**에 상대 기물이 있을 때 그 칸으로 이동하며 잡음
- 앞에 무엇이든 있으면 직진할 수 없음 (막힘)
- 2칸 전진, 앙파상, 승진 없음
- 폰은 앞으로만 움직이므로 **게임이 반드시 유한한 수 안에 끝나며, 무승부가 없습니다.**

### 2-4. 규칙 세트 `cross` (십자 이동 — 비교용 변형)
> 메인 규칙은 `pawn`이고, `cross`는 이동 방식만 바꾼 비교용 변형입니다. (기본값 `--rule pawn`)
- 이동: **동·서·남·북 한 칸** (빈 칸으로만)
- 잡기: **대각선 앞 한 칸**에 있는 상대 기물을 잡으며 그 칸으로 이동 (`pawn`과 동일, 백은 위쪽 대각선 / 흑은 아래쪽 대각선)
- 동·서·남·북에 있는 상대 기물은 잡을 수 없음 (막힐 뿐)
- 자기 기물이 있는 칸으로는 갈 수 없음
- 뒤·옆으로 움직일 수 있으므로 **같은 국면이 반복될 수 있고 게임이 끝나지 않을 수 있습니다.** → 아래 수 제한·무승부 설정이 필요합니다.

### 2-5. 팀이 확정할 설정값
| 항목 | 설정 키 / CLI 옵션 | 기본값(임시) | 비고 |
|---|---|---|---|
| 둘 수 없을 때 | `no_move` / `--no-move` | `lose` | `lose` 또는 `draw` |
| 최대 반수(ply) 제한 | `max_plies` / `--max-plies` | `pawn`: 없음, `cross`: 50 | 도달하면 무승부 |
| 반복 국면 무승부 | `repetition_draw` / `--repetition-draw` | 없음 | 예: 같은 국면 3회 → 무승부 (선택) |
| 적용 기물 | — | 모든 기물이 같은 규칙 | 기물 종류 추가는 후순위 (7장) |

---

## 3. 에이전트(알고리즘) 설계 및 시연

알고리즘은 `Game` 객체의 함수 6개만 호출하면 됩니다. 판 크기/규칙에 의존하지 않습니다.

```python
# initial_state() : 시작 상연
# to_move(s) : 상태 s에서 누구 차례인지
# actions(s) : s에서 둘 수 있는 합법적인 수 목록
# result(s, a) : s에서 수 a(action)을 둔 뒤의 새로운 상태
# is_terminal(s) : 게임이 끝났는지
# utility(s, player) : 끝난 상태에서 player 입장의 점수(승, 패, 무승부)

from pawnchess import Agent, Game, Config, run_matches, RandomAgent, CountingGame 

class MinimaxAgent(Agent):
    def choose_action(self, game, state):
        me = game.to_move(state) #현재 수를 두는 쪽을 me로 지정
        def value(s): # me 관점의 값 <-> 상태 s가 me에게 얼마나 좋은지 계산하는 재귀함수
            if game.is_terminal(s):
                return game.utility(s, me) #게임이 끝났으면, utility로 실제 점수를 return
            vals = [value(game.result(s, a)) for a in game.actions(s)] #안 끝났으면, 가능한 모든 수를 두어 본 값을 구함.
            return max(vals) if game.to_move(s) == me else min(vals)   #내 차례면 max, 상대 차례면 min을 고름
        return max(game.actions(state), key=lambda a: value(game.result(state, a)))

stats = run_matches(CountingGame(Game(Config(n=4))), MinimaxAgent(), RandomAgent(0), 20) 
print(stats.summary()) #위 stats의 결과를 요줌
```

- `State`는 `frozen dataclass` + 튜플이라 해시 가능 → 전이 테이블(캐시)에 바로 사용 가능, 즉 이미 계산한 상태를 딕셔너리에 저장해 재사용할 수 있음.
- `result()`는 원본을 수정하지 않고 새 상태를 반환 → 탐색 중 되돌리기(undo) 불필요(result(s, a)는 상태 s를 직접 고치지 않고, 수 a를 둔 새 상태(child)를 따로 만들어서 돌려줌)
- `actions()` 순서는 결정적 → 수 순서(move ordering) 실험 시 재현 가능.
- 노드 수 세기: `CountingGame(game)`을 `game` 대신 넘기면 `actions_calls`, `result_calls`가 누적된다. (`reset_counts()`로 초기화)
- 참고: `Game.result()`는 내부에서 합법성 검사를 위해 `actions()`를 한 번 더 호출한다. (탐색 속도가 문제가 되면 이 부분이 최적화 후보)

### 3-1. 데이터 표현 (알아 두면 좋은 것)

- **효용(utility)**: 종료 국면에서만 정의. 승리 **+1**, 패배 **−1**, 무승부 **0**. `utility(s, WHITE) == -utility(s, BLACK)` (제로섬). 종료가 아닌 국면에서 호출하면 예외.
- **`State`** (`frozen=True`): `board[row][col]` (0 빈칸, +1 백, −1 흑), `to_move` (+1 백 / −1 흑), `ply` (지금까지 둔 반수), `winner` (종료 시 +1/−1/0, 진행 중 None), `history` (반복 무승부를 켰을 때만 쌓이는 국면 이력).
- **`Action`** (`frozen=True`): `frm=(row, col)`, `to=(row, col)` (0-based), `capture` (잡기 여부). `"a1b2"` 같은 문자열과는 `parse_move` / `format_move`로 변환.

### 3-2. 내가 만든 에이전트를 CLI에 연결하기

에이전트를 `agents.py`에 구현한 뒤, 클래스 아래에 **한 줄만** 등록하면 CLI에서 이름으로 쓸 수 있습니다.

```python
# pawnchess/agents.py
class MinimaxAgent(Agent):
    ...

AGENTS["minimax"] = MinimaxAgent       # 맨 아래 등록표에 추가
```

```powershell
python -m pawnchess.cli --play minimax    # 시작부터 내가 백, 상대는 minimax
```
```
> play minimax b          # 명령어 모드에서도 가능 (내가 흑이면 minimax가 먼저 둠)
> play human              # 사람 대 사람으로 복귀
```

- 등록 이름(`"minimax"`)이 곧 `--play`와 `play` 명령에 쓰는 이름입니다. 등록하지 않은 이름을 쓰면 오류가 납니다.
- 등록표의 값은 "인자 없이 호출하면 에이전트를 만드는 것"이어야 합니다. 인자가 필요하면 `AGENTS["minimax4"] = lambda: MinimaxAgent(depth=4)`처럼 감싸면 됩니다.
- `auto ...` 명령은 `random` 전용입니다. 에이전트끼리의 통계는 아래 3-3의 `experiment.py`로 냅니다.

### 3-3. 에이전트 성과 측정 (`experiment.py`)

내가 만든 에이전트가 얼마나 잘 두는지 터미널에 수치로 찍어 보는 스크립트 틀입니다. CLI의 `auto` 명령은 random 전용이므로, 에이전트끼리의 비교는 이 스크립트로 합니다. (사람이 직접 붙어 보는 것은 3-2, 수치로 평가하는 것은 3-3)

```powershell
python experiment.py
```

파일 위쪽 **"설정" 부분만** 고치면 됩니다.

```python
AGENT_A = lambda: RandomAgent(0)       # 평가할 에이전트   예) lambda: MinimaxAgent()
AGENT_B = lambda: RandomAgent(1)       # 상대 에이전트

CONFIGS = [                            # 여러 개 적으면 차례로 모두 실행
    Config(n=4, rule="pawn"),
    # Config(n=5, rule="pawn"),
    # Config(n=4, rule="cross"),
]
N_GAMES = 100                          # 설정마다 둘 판 수 (색깔 교대)
```

출력 예시 (기본 설정, Random 대 Random):

```
=== N=4 | rule=pawn | no_move=lose | max_plies=auto | repetition_draw=None ===
100판: A 57승 / B 43승 / 무 0  (A 승률 57.0%)
  A가 white일 때: 32승 18패 0무
  A가 black일 때: 25승 25패 0무
  평균 반수 9.8 | 수당 시간 A 0.007ms / B 0.008ms
  탐색 노드 수: actions 985회 / result 985회
  전체 소요 시간: 0.03초
```

- 에이전트는 `lambda: ...`(인자 없이 호출하면 에이전트를 만드는 함수)로 적습니다. 설정마다 새 객체를 만들어 상태가 섞이지 않게 하기 위해서입니다. 시드를 고정하면(`RandomAgent(0)`) 결과가 재현됩니다.
- 탐색 노드 수는 A와 B가 쓴 것을 합친 대국 전체 합계입니다. A의 탐색량을 보고 싶으면 B를 Random으로 두세요.
- 에이전트를 `agents.py`에 두었다면 `from pawnchess.agents import MinimaxAgent` 후 `lambda: MinimaxAgent()`처럼 쓰면 됩니다.
- 출력 수치를 PPT/엑셀로 옮기는 방법(CSV 저장, 그래프 등)은 아직 정하지 않았습니다. (TODO)

---

## 4. 프로젝트 진행 방식 (로드맵)
| 단계 | 내용 | 상태 |
|---|---|---|
| 1 | `State`, `Action`, 표기 변환, 판 출력 | 완료 |
| 2 | `pawn` 규칙: `actions` / `result` / `is_terminal` / `utility` + 단위 테스트 | 완료 |
| 3 | **환경 검증 기준값 통과** (N=4, 아래 7장) | 완료 (통과) |
| 4 | CLI 명령어 모드 | 완료 |
| 5 | `RandomAgent`, `play_game`, `run_matches`, `CountingGame` | 완료 |
| 6 | `cross` 규칙(이동 4방향) + 수 제한/무승부 | 완료 |
| 7 | 방향키 모드 (`keys`, `cross` 대각선 잡기 입력 `y u b n` 포함) | 완료 |
| 8 | 에이전트 CLI 연결(`AGENTS` 등록표, `--play <이름>`) + 성과 측정 스크립트 틀(`experiment.py`) | 완료 |
|-------------------------------------------------환경 구현----------------------------------------------------|
| **9** | **팀 작업: MinimaxAgent → AlphaBetaAgent → 깊이 제한+평가 함수 → (선택) 반복 심화·수 순서** | **다음 할 일** |

### 앞으로 진행 사항

1. **환경 확정값 합의** — 2-5장의 설정값(`no_move`, `max_plies`, `repetition_draw`)을 팀이 정한다. 바꾸면 7장 기준값도 다시 계산해야 한다.
2. **MinimaxAgent** — `Agent` 인터페이스를 상속해 `agents.py`(또는 새 파일)에 추가하고 `AGENTS`에 등록. 위 3장 코드 예시 참고.
3. **AlphaBetaAgent** — 같은 결과(값)를 내는지 Minimax와 교차 검증, 노드 수 감소량 측정.
4. **깊이 제한 + 평가 함수** — N=5 이상, `cross` 규칙처럼 전수 탐색이 불가능한 설정에서 사용.
5. **성과 측정** — `experiment.py`(3-3)로 `run_matches`를 돌려 Random 대비 승률, 수당 시간, `CountingGame`으로 탐색 노드 수 비교.
   (PEAS의 성과 측도 P에 해당, 백/흑 색깔별로 나눠서 해석할 것 — `cross`는 N=3 흑 필승, N=4 백 필승, 7장 참고)
6. **발표 자료** — 확장 축 ①(N↑ → 깊이 m↑), ②(규칙 변경 → 분기 계수 b↑)에 따른 노드 수/시간 변화를 표,그래프로 정리.

---

## 5. 파일별 역할

```
AI PROJECT/
├─ README.md                   # 이 문서
├─ experiment.py               # 에이전트 성과 측정 스크립트 틀 (3-3)
└─ pawnchess/
   ├─ __init__.py
   ├─ game.py
   ├─ notation.py
   ├─ agents.py
   ├─ runner.py
   ├─ cli.py
   ├─ keys.py
   └─ tests/
      ├─ test_rules_pawn.py
      ├─ test_rules_cross.py
      ├─ test_reference_values.py
      └─ test_runner_cli.py
```

### 소스 파일

| 파일 | 역할 | 핵심 내용 |
|---|---|---|
| `__init__.py` | 편의용 import 모음 (re-export) | `Game, Config, State, Action, WHITE, BLACK, Agent, RandomAgent, HumanAgent, play_game, run_matches, CountingGame, GameRecord, MatchStats`를 한 번에 import 가능하게 함 |
| `game.py` | 게임 환경의 규칙과 상태 정의 | `Config`(n=4 기본, rule, no_move, max_plies, repetition_draw — 설정 검증 포함), `Action(frm, to, capture)`, `State(board, to_move, ply, winner, history)`, `Game`(핵심 6함수), 규칙 생성기 `_pawn_moves` / `_cross_moves`와 `RULES` 레지스트리, 종료 판정 `_winner_after`(도달·전멸·수 없음·ply 제한·반복), 불법 수 이유 `illegal_reason` |
| `notation.py` | 사람이 읽는 표기 ↔ 내부 객체 변환 | `"a1a2"` ↔ `Action`(`parse_move`/`format_move`), 칸 표기, 방향어(`up`, `upleft`…) → `Action`(`direction_to_action`), 판 출력 `render_board`(마지막 수 `[ ]`, 커서 표시 지원), 테스트용 텍스트 → `State`(`state_from_text`) |
| `agents.py` | 에이전트 인터페이스와 기본 구현 | `Agent`(추상 `choose_action`), `RandomAgent`(seed 지정 가능), `HumanAgent`(터미널 입력: `a1a2` / `a2 up` / 번호 / `?`), **`AGENTS` 등록표**(CLI에서 이름으로 에이전트를 만드는 표, 기본은 `random`뿐), **탐색 에이전트는 여기에 팀이 추가하고 `AGENTS`에 등록** |
| `runner.py` | 대국 실행·통계·계측 | `play_game`(수순·수당 시간·결과 기록 → `GameRecord`), `run_matches`(N판, 색깔 교대, 승/패/무와 색깔별 집계 → `MatchStats`), `CountingGame`(`actions`/`result` 호출 횟수 계측 래퍼) |
| `cli.py` | 터미널 인터페이스 | `Session`(상태·undo 이력·상대 에이전트 관리, `cmd_*` 명령 핸들러), 명령어 모드, `keys_mode`(방향키 모드), `main`(argparse 진입점) |
| `keys.py` | OS별 키 입력 흡수 | `read_key()` 하나로 Windows(`msvcrt.getwch`)와 macOS/Linux(`termios`+`tty`)의 방향키 차이를 통일. `'up' 'down' 'left' 'right' 'enter' 'esc'` 또는 문자 반환 |
| `../experiment.py` | 에이전트 성과 측정 스크립트 틀 | 에이전트·환경·판 수를 설정하고 실행하면 승률·색깔별 결과·수당 시간·탐색 노드 수를 터미널에 출력 (3-3) |

### 테스트 파일

| 파일 | 검증 대상 | 개수 / 소요 |
|---|---|---|
| `tests/test_rules_pawn.py` | `pawn` 규칙: 초기 배치, 직진 막힘·대각선 잡기, 흑 방향, 도달/전멸/수 없음 승리, 불법 수 거부, **`result()` 불변성**, 해시 가능, 수 순서 결정성, **utility 제로섬**, 방향 표기, 표기 왕복 | 13개 / 수 초 이내 |
| `tests/test_rules_cross.py` | `cross` 규칙: 시작 수 개수, 4방향 이동 + 대각선 앞 잡기(백/흑), 상하좌우·뒤 잡기 불가, 자기 기물 칸 진입 불가, `max_plies` 무승부, 기본 ply 제한, 반복 국면 무승부 | 8개 / 수 초 이내 |
| `tests/test_reference_values.py` | **7장 기준값**: `pawn` N=4 (11,712 / 4,197,973 / 백 필승), `cross` N=4 (21반수 이상이면 백 필승) | 4개 / **약 2.5분** (N=4 전체 트리 탐색) |
| `tests/test_runner_cli.py` | `play_game` 재현성(seed), `run_matches` 집계 합, 커스텀 에이전트 장착, `CountingGame`, CLI 세션(불법 수 무시, `peek`/`undo`/`set`), 대 Random 대국, **`AGENTS`에 등록한 에이전트와 `play`** | 7개 / 수 초 이내 |

> `tests/__init__.py`, `__pycache__/`는 패키지 인식·파이썬 캐시용 파일로 직접 수정할 필요 없음.

---

## 6. 테스트 & 시연 방법

### 6-1. 자동 환경 검증 테스트 : 게임의 환경이 제대로 만들어 졌는지 컴퓨터가 확인하는 과정(ai agent 시연 아님)

```powershell
# 전체 (약 2.5~3분, 대부분 N=4 pawn 전수 탐색)
python -m unittest discover -s pawnchess/tests -t . -v

# 빠른 테스트만 (기준값 제외, 수 초)
python -m unittest pawnchess.tests.test_rules_pawn pawnchess.tests.test_rules_cross pawnchess.tests.test_runner_cli -v

# 기준값 테스트만
python -m unittest pawnchess.tests.test_reference_values -v

# 특정 테스트 하나(예시 : result()가 입력 상태를 바꾸지 않는지 검사)
python -m unittest pawnchess.tests.test_rules_pawn.PawnRules.test_result_does_not_mutate -v
# pawnchess.tests.test_rules_pawn . PawnRules . test_result_does_not_mutate
# └─────── 파일(모듈) ───────────┘  └ 클래스 ┘  └────── 테스트 함수 ──────┘
```
- 참조 (테스트 종류)
- 규칙 테스트: 초기 배치가 맞는지, 직진이 막히면 못 가는지, 대각선으로만 잡는지, 불법 수를 거부하는지, 도달·전멸하면 승리 판정이 나는지
- 설계 약속 테스트: result()가 원본 상태를 안 바꾸는지, utility가 제로섬(백 +1이면 흑 −1)인지
- 기준값 테스트: 4×4 전체 게임 트리를 끝까지 탐색해 노드 수가 11,712 / 4,197,973이고 백 필승인지 (7장에 적힌 정답과 같아야 통과). 이게 약 2.5분 걸립니다.
- 실행기 테스트: play_game, run_matches, CLI가 오류 없이 도는지

**최근 실행 결과:** `Ran 32 tests in 191.686s — OK` (Python 3.14.3, Windows)

### 6-2. 완료 기준(확인 방법)

| 완료 기준 | 확인 방법 |
|---|---|
| 4×4 `pawn`을 사람 대 사람 / 사람 대 Random으로 끝까지 | 6-3 시연 A, B |
| `actions`, `state`, `peek`, `undo` 확인 | 6-3 시연 A |
| 7장 기준값 통과 (N=3, N=4 pawn) | `python -m unittest pawnchess.tests.test_reference_values -v` |
| `result()`가 입력 상태를 바꾸지 않음 | `test_result_does_not_mutate` |
| `utility` 제로섬 | `test_utility_zero_sum_and_guard` |
| `Agent`만 구현하면 CLI·`run_matches`에 장착 | `test_custom_agent_plugs_in`, `test_cli_registered_agent` |
| 탐색 알고리즘 코드 미포함 | `agents.py`에 `RandomAgent`/`HumanAgent`만 존재 (코드 검색으로 확인) |

### 6-3. 시연 시나리오 (발표/데모용 추천 순서)

**시연 A — 명령어 모드로 환경 보여주기 (`python -m pawnchess.cli`)**
```
> show                 # 초기 판 (백 1행, 흑 N행)
> actions              # 합법 수 번호 목록 → 수업의 actions(s)
> state                # 내부 State repr (frozen, 해시 가능)
> peek a1a2            # 판을 바꾸지 않고 result(s,a) 결과만 미리보기
> a1a2                 # 실제로 수 두기 (move a1a2 / move 1 / a1 up 도 가능)
> undo                 # 무르기
> a1a3                 # 불법 수 → 이유 출력, 상태 불변
> terminal             # is_terminal / utility 값
> reset
```

**시연 B — 사람 대 에이전트 (`play <이름>`)**
```
> play random w         # 내가 백. (b면 흑, 상대가 먼저 둠)
> move 1
> ... 끝까지 진행 → "*** 게임 종료: 백(W) 승리 ***"
> play minimax b        # (내 에이전트를 등록했다면) 이름만 바꿔서 같은 방식으로 대국
> play human            # 사람 대 사람 모드로 복귀
```

**시연 C — 성과 측도 (무작위 대 무작위 통계)**
```
> auto random random 100 1
100판: A 48승 / B 52승 / 무 0  (A 승률 48.0%)
  A가 white일 때: 24승 26패 0무
  A가 black일 때: 24승 26패 0무
  평균 반수 9.9 | 수당 시간 A 0.009ms / B 0.008ms
```
(seed `1` 고정 시 재현 가능. 위 수치는 이 저장소에서 실제 실행한 값. `auto`는 random 전용이라 내 에이전트의 통계는 3-3의 `experiment.py`를 사용)

**시연 D — 규칙/크기 바꾸기 (확장 축 설명)**
```
> set n 5              # 판 크기 N↑ → 깊이 m↑
> set rule cross       # 비교용 변형 규칙으로 변경 → 분기 계수 b↑ (max_plies 자동 50)
> set max_plies 21     # cross N=4에서 백 필승이 드러나는 최소 제한
> set no_move draw     # 둘 수 없으면 무승부로 변경
> set repetition_draw 3
```

**시연 E — 방향키 모드**
```
> keys
```
방향키로 커서 이동 → `Enter`로 기물 선택 → 방향키(또는 숫자)로 이동 선택 → `Enter` 확정, `Esc` 취소, `q`로 명령어 모드 복귀.
대각선 잡기(`pawn`·`cross` 공통)는 `y`(↖) `u`(↗) `b`(↙) `n`(↘) 키 또는 숫자 키로 선택.

**시연 F — 에이전트 성과 측정 (`experiment.py`, 알고리즘 붙인 후 비교 실험)**
```powershell
python experiment.py
```
`experiment.py` 위쪽 "설정"에서 `AGENT_A`(평가할 에이전트), `AGENT_B`(상대), `CONFIGS`(판 크기·규칙), `N_GAMES`(판 수)를 정하고 실행하면, 승률·색깔별 결과·수당 시간·탐색 노드 수가 출력됩니다. 시연 C는 random 전용이므로, 내가 만든 에이전트의 결과는 이 시연 F로 보여줍니다. 자세한 사용법은 3-3 참고.

### 6-4. 주의 사항 / 알려진 한계

- **방향키 모드는 자동 테스트가 없습니다.** 실제 터미널(Windows Terminal, PowerShell)에서 시연 E로 직접 확인해야 합니다.
  `msvcrt`/`termios`는 표준 입력이 TTY일 때만 동작하므로 IDE 내장 콘솔이나 파이프 입력에서는 안 될 수 있습니다.
- 파이프로 CLI에 명령을 넘길 때(`... | python -m pawnchess.cli`) PowerShell이 앞에 BOM을 붙여 첫 명령이 `알 수 없는 명령`으로 보일 수 있습니다. 대화형으로 실행하면 문제 없습니다.
- **기준값 테스트가 느립니다** (약 2.5분). 개발 중에는 6-1의 "빠른 테스트"를 쓰고, 제출 전에 전체를 한 번 돌리세요.
- `cross` 기준값은 `no_move="lose"` 가정(이동 4방향·대각선 앞 잡기)입니다. 2-5장 확정값을 바꾸면 기준값을 다시 계산하고 테스트도 수정해야 합니다.
- 반복 국면 무승부를 켜면 `State.history`에 이력이 쌓이지만 **동등성/해시에는 포함되지 않습니다** (같은 판+차례+ply는 같은 국면으로 취급). 전이 테이블 캐시와 함께 쓸 때 유의하세요.

---

## 7. 환경 검증 기준값

아래 값은 별도 코드로 **완전 탐색**해서 얻은 값입니다. 환경 구현이 맞는지 확인하는 용도입니다.
테스트(`test_reference_values.py`)에서는 **환경 함수만 쓰는 간단한 전수 탐색**(DFS로 트리 크기 세기)을 작성해 비교합니다. 이것은 검증용 코드이며, 팀이 구현할 미니맥스 에이전트와는 별개입니다.

**공통 가정:** 승리 조건 3가지 모두 사용, 둘 수 없으면 패배.

### `pawn` 규칙
| N | 도달 가능한 비종료 국면 수 (판+차례 기준) | 게임 트리 전체 노드 수 (루트·종료 노드 포함) | 완벽하게 둘 때 |
|---|---|---|---|
| 3 | 78 | 252 | 흑(후수) 필승 |
| 4 | 11,712 | 4,197,973 | 백(선수) 필승 |

- N=3 결과(후수 필승)는 Hexapawn(Martin Gardner, 1962)의 알려진 결과와 일치합니다.
- 노드 수는 "어떤 노드를 셀지" 정의에 따라 달라집니다. 여기서는 **루트에서 시작해 모든 수를 끝까지 펼친 트리의 노드 전체**(종료 국면 포함)를 셌습니다. 다른 정의로 세면 숫자가 달라질 수 있으니 정의를 먼저 맞추세요.

### `cross` 규칙 (4방향 이동·대각선 앞 잡기, 수 제한에 걸리면 무승부)
| N | 시작 국면 합법 수 | 완벽하게 둘 때 |
|---|---|---|
| 3 | 3 | 흑 필승, 제한을 **8반수 이상**으로 두어야 드러남 (7반수 이하 제한이면 무승부) |
| 4 | 4 | **백(선수) 필승**, 제한을 **21반수 이상**으로 두어야 드러남 (20반수 이하 제한이면 무승부) |

- 대각선 앞 잡기로 바뀐 뒤에는 N=3은 흑 필승, N=4는 백 필승으로 **판 크기에 따라 유리한 쪽이 달라집니다.** 승률을 해석할 때 백/흑을 나누어 보세요.
- 2-5장의 확정값이 바뀌면 이 기준값도 다시 계산해야 합니다.

---

## 8. 기타

### 8-1. 후순위 확장 (지금은 구현하지 않음, 구조만 열어 둠)
- 기물 종류 추가 (예: 나이트). 보드 칸 값을 `int` 대신 `(색, 종류)`로 바꿀 수 있게 이동 생성 함수를 기물별로 분리해 둠. 다른 기물이 생기면 반복 국면이 가능하므로 2-5장의 수 제한·무승부 규칙을 사용.
- GUI (터미널 버전 완성 후).
- Gymnasium 스타일 래퍼(`reset()`, `step(action)`) — 필요 시.

### 8-2. 환경 요약 (발표용)

| 항목 | 값 |
|---|---|
| 게임 | N×N 폰 체스 변형 (시작 4×4) |
| PEAS | P: 승률·수당 시간·탐색 노드 수 / E: N×N 판 + 상대 / A: 합법 수 선택 / S: 전체 판 상태 |
| 환경 성질 | fully observable, deterministic, sequential, static, discrete, known, multi-agent |
| 기준값 | N=4 → 선수 필승 (11,712 국면 / 4,197,973 노드) |
| 적합 알고리즘 | Minimax → Alpha-Beta → 깊이 제한 + 평가 함수 → (선택) 반복 심화·수 순서 |
