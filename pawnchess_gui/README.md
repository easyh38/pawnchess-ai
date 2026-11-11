# PawnChess GUI

`pawnchess` 엔진을 그대로 쓰는 tkinter GUI입니다. CLI(`pawnchess/cli.py`)와는 독립적이며, 표준 라이브러리만 사용합니다.

## 실행

```powershell
python -m pawnchess_gui                                   # 사람(백) vs random(흑), 4x4 pawn
python -m pawnchess_gui --n 5 --black alphabeta_adv       # 5x5에서 alphabeta_adv와 대국
python -m pawnchess_gui --white bfs --black alphabeta_eval  # AI끼리 관전
python -m pawnchess_gui --rule cross --white minimax      # 내가 흑
```

옵션(`--n`, `--rule`, `--no-move`, `--max-plies`, `--repetition-draw`)은 CLI와 같고, `--white` / `--black`에 `human` 또는 `pawnchess/agents.py`의 `AGENTS`에 등록된 이름을 넣습니다. 모든 설정은 창 오른쪽 패널에서 바꾼 뒤 **새 게임**으로도 적용할 수 있습니다.

## 조작

- 내 기물 클릭 → 갈 수 있는 칸에 점(이동) / 고리(잡기) 표시 → 그 칸 클릭으로 수 두기
- 마지막 수는 노란색 칸으로 표시
- **무르기**: 사람이 둘 차례까지 되돌림 (AI 수는 같이 무름)
- **일시정지/재개**: AI 차례 진행을 멈춤
- **AI끼리 수 간격**: AI vs AI 관전 속도

## 구조

| 파일 | 역할 |
|---|---|
| `controller.py` | 대국 진행 로직 (`Match`): 국면, 무르기 이력, 대국자. tkinter 비의존 |
| `app.py` | tkinter 화면. AI 계산은 별도 스레드에서 실행해 창이 멈추지 않음 |
| `__main__.py` | 명령행 옵션 처리 |
| `tests/test_controller.py` | `Match` 단위 테스트 (`python -m unittest pawnchess_gui.tests.test_controller`) |

> 새 에이전트를 `AGENTS`에 등록하면 GUI 드롭다운에도 자동으로 나타납니다.
>
> `minimax`, `alphabeta`는 끝까지 탐색하므로 N≥5에서는 한 수에 오래 걸릴 수 있습니다. 계산 중에 새 게임을 시작하면 이전 결과는 버려지지만, 계산 자체는 끝날 때까지 뒤에서 CPU를 사용합니다.
