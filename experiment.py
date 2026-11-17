"""에이전트 성과 측정 스크립트 틀.

실행:  python experiment.py          (이 파일이 있는 폴더에서)

아래 "설정" 부분만 고치면 된다.
  - 어떤 에이전트끼리 붙일지 (AGENT_A, AGENT_B)
  - 어떤 환경에서 붙일지 (CONFIGS: 판 크기 N, 규칙 등)
  - 몇 판 둘지 (N_GAMES)

출력(터미널): 설정마다 승/패/무, 색깔별 결과, 평균 반수, 수당 시간, 탐색 노드 수.
※ 노드 수(actions/result 호출 횟수)는 A·B 두 에이전트가 쓴 것을 합친 대국 전체 합계다.
   A의 탐색량만 보고 싶으면 B를 RandomAgent로 두면 사실상 A의 값이다.
"""
import time

from pawnchess import Config, CountingGame, Game, RandomAgent, run_matches
# from pawnchess.agents import AGENTS        # CLI 등록표를 그대로 쓰고 싶을 때
from pawnchess.agents import BfsAgent, MinimaxAgent, AlphaBetaEvalAgent, AlphaBetaAgent, AlphaBetaAdvancedAgent

# ============================== 설정 (여기를 수정) ==============================

# 에이전트: "인자 없이 호출하면 Agent 객체를 만드는 함수"로 적는다.
# (매 설정마다 새 객체를 만들어 상태가 섞이지 않게 하기 위함)
AGENT_A = lambda: AlphaBetaEvalAgent()       # 평가할 에이전트 예) lambda: MinimaxAgent()  /  AGENTS["minimax"]
AGENT_B = lambda: AlphaBetaAdvancedAgent()     # 상대 에이전트     예) lambda: RandomAgent(1)

# [파라미터 조정 실험] 깊이(depth)와 평가 함수 가중치(weights)를 바꿔서 넣을 수 있다. (README 3-5)
#   - 빠진 가중치는 기본값을 쓴다. 가중치 절댓값의 합은 1 이하여야 한다 (넘으면 오류).
#   - evaluate 항목:          material, advance                        (기본 0.45 / 0.45)
#   - evaluate_advanced 항목: material, advance, frontier, passed, mobility (기본 0.30/0.20/0.25/0.15/0.10)
# 예)
# AGENT_A = lambda: AlphaBetaEvalAgent(depth=3, weights={"material": 0.7, "advance": 0.2})
# AGENT_A = lambda: AlphaBetaAdvancedAgent(depth=4, weights={"frontier": 0.35, "mobility": 0.0})
#
# [수 순서 실험] ordering=True면 좋을 것 같은 수부터 탐색한다 (값은 같고 노드 수만 줄어듦, README 3-6).
# AGENT_A = lambda: AlphaBetaAdvancedAgent(depth=4, ordering=True)

# 실험할 환경 목록. 여러 개 적으면 차례로 모두 돌린다. (확장 축 ① N↑, ② 규칙 변경)
CONFIGS = [
    Config(n=6, rule="pawn"),
    # Config(n=5, rule="pawn"),
    # Config(n=4, rule="cross"),   # cross는 max_plies 기본 50
]

N_GAMES = 100       #W 설정마다 둘 판 수 (색깔은 교대로 잡는다)

# ===============================================================================


def run_one(config: Config) -> None:
    game = CountingGame(Game(config))
    t0 = time.perf_counter()
    stats = run_matches(game, AGENT_A(), AGENT_B(), N_GAMES)
    elapsed = time.perf_counter() - t0

    print(f"=== N={config.n} | rule={config.rule} | no_move={config.no_move} | "
          f"max_plies={config.max_plies} | repetition_draw={config.repetition_draw} ===")
    print(stats.summary())
    print(f"  탐색 노드 수: actions {game.actions_calls:,}회 / result {game.result_calls:,}회")
    print(f"  전체 소요 시간: {elapsed:.2f}초")
    print()


if __name__ == "__main__":
    for cfg in CONFIGS:
        run_one(cfg)
