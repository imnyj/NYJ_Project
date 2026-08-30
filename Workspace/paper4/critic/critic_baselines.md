# Critic 검토 — src/baselines/, run_all.py, src/evaluate.py, src/hpo.py

검토일 2026-08-30. 대상: `idea/design_spec_v2.md`(3·5·9절), `Conversation.md`(4절 문헌근거).
Python: `/home/imnyj/venv/bin/python`. 코드 수정 없음(Critic은 읽고 검증만 함).
`checkpoints/`, `logs/training/`는 **건드리지 않았다** — 모든 실측은 `etc/scripts/verify_all_baselines.py`
(기존 스크립트, 체크포인트 미생성) 실행과 모델 단독 인스턴스화(파일 저장 없음)로만 수행했다.

---

## 산출물 1: 코드 구조 요약

### `coder/src/baselines/base_agent.py`
```
class BaseRLModel(nn.Module):  # 9종 전부의 공통 부모, Act/Rest 핫스왑·평가 스위트 계약
    def __init__(): state_dim/num_channels/ActionDecoder/hparams 초기화
    def _prepare_state_tensor(): numpy/list/tensor 입력을 모델 디바이스의 2D float32 텐서로 변환
    def select_action(): NotImplementedError — 서브클래스가 구현할 하이브리드 액션 선택 인터페이스
    def update(): NotImplementedError — 배치 1개로 1회 그래디언트 업데이트
    def save(): state_dict 체크포인트 저장
    def load(): state_dict 체크포인트 복원
BaseAgent = BaseRLModel  # 하위호환 별칭
```

### `coder/src/baselines/sb3_wrapper.py` (기본 3종 공유 인프라)
```
class HybridActionBoxWrapper:  # SB3의 3차원 Box[-1,1] <-> (Δ,ch,p) 그랜트 양방향 변환
    action_space: Box(-1,1,shape=3) 프로퍼티
    observation_space(): StateVectorizer 출력용 Box 공간(정적 메서드)
    channel_bin_width: 채널 1개 빈의 Box 폭
    _to_unit()/_from_unit(): [-1,1]<->[0,1] 아핀 변환
    channel_from_box()/channel_to_box(): Box 좌표<->채널 인덱스 균등폭 비닝
    to_grant(): Box 액션 -> (delta_s, ch, power). Δ는 delta_from_unit(기하), power는 선형
    from_grant(): 그랜트 -> Box 인코딩(역방향)
    _as_vector(): 임의 컨테이너를 길이-3 float 배열로 평탄화
class HybridGrantSpecEnv(gym.Env):  # SB3가 관측/액션 공간만 읽어가는 스펙 전용 환경. step() 실사용 안 됨
def move_optimizer_state(): 옵티마이저 상태 텐서를 지정 디바이스로 이동
class SB3BaselineModel(BaseRLModel):  # PPO/SAC/TD3 공통 기반
    def _build_sb3(): 실제 SB3 알고리즘 생성, policy를 서브모듈로 등록해 핫스왑 가능하게 함
    def sb3_optimizers(): 옵티마이저 목록(기본 policy.optimizer)
    def _sync_device()/to()/device: SB3 내부 device 북키핑을 nn.Module.to()와 동기화
    def unpack_batch(): 리플레이 버퍼 배치를 SMDP discount 포함 텐서 튜플로 언팩
    def decode()/encode(): Box<->그랜트 변환 위임
```

### `coder/src/baselines/sb3_ppo.py` — **[기본 1/3] 유지: PPO 알고리즘 자체 / 버림: 진짜 behaviour log-prob(정직하게 근사로 명시)**
```
class PPO(SB3BaselineModel):  # Schulman 2017
    def __init__(): SB3 PPO 구성(rollout_n_steps 작게 — Act/Rest 이중 메모리 절약)
    def sb3_optimizers(): policy.optimizer
    def select_action(): 가우시안 액터 샘플 -> wrapper 디코딩, raw(미클립) 벡터 반환
    def update(): 배치=1회 롤아웃 취급 클리핑 서로게이트(1-step SMDP TD, GAE λ=0)
```

### `coder/src/baselines/sb3_sac.py` — **유지: SAC 알고리즘 / 버림: 없음(온전 이식), target_entropy 재튜닝 필요성만 명시**
```
class SAC(SB3BaselineModel):  # Haarnoja 2018
    def __init__(): SB3 SAC 구성, log_ent_coef를 nn.Parameter로 재등록(핫스왑 가능화)
    target_entropy: 프로퍼티
    def sb3_optimizers(): actor/critic/ent_coef 옵티마이저
    def _sync_device(): ent_coef_tensor 디바이스 추적
    def select_action(): tanh-가우시안 샘플 + Q값
    def _current_ent_coef(): 현재 엔트로피 온도
    def update(): 온도->트윈크리틱->액터->polyak, γ 대신 γ^Δ
```

### `coder/src/baselines/sb3_td3.py` — **유지: TD3 알고리즘 / 버림: 없음. 결정적 정책의 이산채널 탐색은 외부 주입 노이즈 의존임을 명시**
```
class TD3(SB3BaselineModel):  # Fujimoto 2018
    def __init__(): SB3 TD3 구성 + 채널전용 탐색노이즈(기본 1 bin 폭)
    noise_sigma: 차원별 탐색 노이즈
    def sb3_optimizers(): actor/critic 옵티마이저
    def select_action(): 결정적 액터 + 가우시안 노이즈(채널 차원 큰 σ)
    def update(): 타깃정책스무딩 + 클립더블Q + 지연액터, γ^Δ
```

### `coder/src/baselines/res_mapddpg.py` — **유지: P-DQN류 파라미터화액션 러너·잔차트렁크·CTDE / 버림: NOMA+convex 최적화 단계(SIC 수신기 없음)**
```
class _ResidualBlock(nn.Module): 사전정규화 잔차 MLP 블록
class _ResidualTrunk(nn.Module): 입력투영->잔차블록 스택->선형 출력
class RESMAPDDPG(BaseRLModel):  # Li et al., IEEE TVT 75(7) 2026
    def _grant_from_unit_action(): [-1,1] 연속쌍+채널 -> 그랜트(Δ는 delta_from_unit 기하)
    def _pool_neighbourhood(): 마스킹 평균풀링(가변 에이전트 수 처리, 논문에 없는 추가)
    def _q_values(): 풀링 이웃맥락 조건 중앙집중 크리틱 Q
    def select_action(): ε-그리디 채널선택 + tanh 파라미터 액터, action_idx 반환
    def _resolve_channel_indices(): action_idx 우선, 없으면 raw_action[1]에서 정확 복구
    def update(): 크리틱(실행된 서브채널 자리에 실제 실행 연속값 대입)->액터->polyak
```

### `coder/src/baselines/ma2hdqn.py` — **유지: MA-D3QN+i-DDPG 분기구조·적응형 lr / 버림: 없음(n-step 리턴은 조건부 비활성)**
```
class MA2HDQN(BaseRLModel):  # Hong et al., IEEE TVT 75(6) 2026
    def _grant_from_unit_action(): 연속쌍+채널 -> 그랜트(기하 Δ)
    def _q_values(): 듀얼링 집계 Q=V+(A-mean A)
    def _channel_one_hot(): 채널 원핫
    def select_action(): ε-그리디 D3QN 채널 + tanh DDPG 연속
    def _resolve_channel_indices(): action_idx 우선, 없으면 raw_action[1] 정확 복구
    def _adapt_learning_rate(): 보상 EMA 기반 적응형 학습률(논문 정성서술을 저자가 구체화, 명시됨)
    def update(): 더블DQN(D3QN)->DDPG크리틱(타깃스무딩)->액터->하드/폴리악 혼합 갱신
```

### `coder/src/baselines/i_hamappo.py` — **유지: 하이브리드 MAPPO 러너 / 버림: 시맨틱압축·IEM 절반(명시: "원 기여의 절반 미재현")**
```
class IHAMAPPO(BaseRLModel):  # Chen et al., IEEE TWC 25 2026
    def _grant_from_pre_squash(): pre-tanh 샘플 -> 그랜트(기하 Δ)
    def _distributions(): 현재/구정책 (Categorical, Normal)
    def _policy_log_prob(): 결합 로그확률(tanh 자코비안 생략—파라미터무관이라 상쇄됨)
    def _pool_neighbourhood(): 마스킹 평균풀링 크리틱 컨텍스트
    def _value(): 이웃맥락 포함 가치함수
    def select_action(): 샘플/결정적 선택, pre-tanh raw_action 저장
    def _resolve_channel_indices(): action_idx 우선, 없으면 raw_action[1] 정확 복구
    def _sync_old_policy(): 고정 행동정책 스냅샷 갱신
    def update(): 1-step TD 크리틱 -> 스냅샷 대비 클리핑 서로게이트 -> 주기 스냅샷 갱신
```

### `coder/src/baselines/spam_d3qn.py` — **유지: 인프라측 관측·듀얼링더블DQN·완전이산 조인트헤드 / 버림: "어느 차량" 축(파이프라인이 차량별 호출), PER은 배치내 재가중으로 약화(명시)**
```
def build_geometric_delta_grid(): 결정자 기반 Δ 기하격자
def build_linear_power_grid(): 결정자 기반 전력 선형격자
class SPAMD3QN(BaseRLModel):  # Bai et al., IEEE TVT 73(4) 2024
    def pack_action_index()/unpack_action_index(): 3-factor 결합 인덱스 변환
    def _action_to_tuple(): 인덱스 -> 그랜트
    def _forward_q(): 온라인/타깃 듀얼링 Q
    def _infer_action_indices(): raw_action(encode_action 출력)에서 delta·power·ch 전부 복구
    def select_action(): ε-그리디 결합 인덱스
    def update(): 더블DQN 타깃 + 배치내 PER 재가중 MSE + 주기 하드동기화
```

### `coder/src/baselines/carlton.py` — **유지: DeepMellow 브랜칭 Q, 문제설정(서브채널 경쟁) 그대로 / 버림: 없음. Δ·전력 축은 SPAM-D3QN과 동일 방식의 우리측 확장(명시)**
```
def build_geometric_delta_grid()/build_linear_power_grid(): spam_d3qn과 동일(독립 중복 구현)
def mellowmax(): DeepMellow mellowmax 연산자(logsumexp 안정화)
class CARLTON(BaseRLModel):  # Cohen et al., IEEE TWC 24(1) 2025
    def pack_action_index()/unpack_action_index(): SPAM-D3QN과 비트호환
    def _branch_indices_from_combined(): 결합 인덱스 -> (B,3) 벡터화
    def _forward_branches(): 브랜치별 Q(공유 트렁크)
    def _infer_branch_indices(): raw_action에서 delta·power·ch 전부 복구
    def select_action(): mellowmax 유도 볼츠만(β=ω) 브랜치별 샘플링
    def update(): mellowmax 백업(기본 타깃망 미사용) 브랜치별 MSE 평균
```

### `coder/src/baselines/maddpg_mt.py` — **유지: 이중크리틱(local+global)·태스크분해 구조(보상4항과 1:1) / 버림: 플래툰 구조 전체(신호교차로 시나리오엔 대응 없음), 태스크분해는 조건부 비활성(명시)**
```
class MADDPGMT(BaseRLModel):  # Parvini et al., IEEE TVT 72(8) 2023
    def _build_critic(): num_tasks개 가치헤드 크리틱 빌더
    def _delta_from_unit_t()/_unit_from_delta_t(): ActionDecoder 매핑 벡터화 버전
    def _decode_batch_actions(): 저장 raw_action(encode_action) -> 크리틱 입력 형식 복원
    def _actor_action(): 액터 forward, 채널은 straight-through Gumbel-Softmax
    def _encode_others(): 마스킹 평균+최대 풀링 가변 에이전트 컨텍스트
    def select_action(): 결정적/노이즈 액션, raw_action은 encode_action 직렬화
    def update(): local+global 크리틱 블렌드 타깃 -> 액터(합산 태스크가치 최대화) -> polyak
```

### `coder/src/baselines/__init__.py`
```
BASELINE_REGISTRY: 9개 정본이름 -> 클래스
_ALIASES: 하이픈없는 철자 별칭
BASELINE_CATEGORIES: basic/latest/similar 그룹
ALL_BASELINES: 표 순서 9개 튜플
def get_baseline(): 이름 -> 클래스 조회, 실패 시 사용가능 목록과 함께 KeyError
```

### `coder/run_all.py`
```
def main(): ALL_BASELINES(또는 --models 부분집합)를 순회하며 run_hot_swap_training 호출.
            total_steps = episodes * steps_per_episode 로 200,000스텝 산식을 코드에서 재계산(회귀 방지 주석 있음).
            get_baseline()으로 클래스 주입(문자열 주입 아님).
```

### `coder/src/evaluate.py` (핵심만)
```
def normalize_model_name(): 문자열 별칭 정규화 — CANONICAL_EVAL_MODELS(구세대 명명, 아래 결함 참조)
def load_optimal_hparams(): optuna_best_params.csv 로드
def instantiate_model(): 모델 인스턴스화. HeuristicScheduler 외 문자열은 NotImplementedError(아래 결함1 참조)
def calculate_jains_fairness(): Jain 공정성 지수
def evaluate_single_run(): 실제 SUMO AoiV2IEnv 이벤트구동 1회 실행 평가 (needs_decision 사용, 정상)
def run_full_benchmark(): 다중모델x밀도x시드 벤치마크, raw/summary/leaderboard 3 CSV 생성
```

### `coder/src/hpo.py` (핵심만)
```
CANONICAL_MODEL_NAMES / MODEL_CATEGORIES: 구세대 9개 이름(아래 결함1 참조)
def normalize_model_name(): 구세대 별칭 정규화
def sample_reward_weights(): w1~w4 로그 샘플 후 합=1로 정규화, user_attr로 기록
def sample_hparams(): 모델별 맞춤 탐색공간(구세대 이름 매칭 실패 시 범용 {lr,hidden_dim,gamma})
def compute_composite_objective(): mean_error+mean_aoi+outage+power_norm 가중합
def evaluate_model_in_env(): 이벤트구동 SMDP 롤아웃(needs_decision 사용, 정상), 옵션으로 buffer.push+model.update
def evaluate_trial_multiseed(): model_cls(**hparams)로 인스턴스화 후 다중시드 평균 스코어
def run_hpo_study(): Optuna Study 생성+objective 최적화. model_cls 없이 문자열만 주면 예외(아래 결함1)
def save_study_results()/run_all_baselines_hpo()/main(): 결과저장 및 CLI 진입점
```

### 9종 비교표

| 모델명 | 분류 | 원 논문 | 액션 헤드 구조 | on/off-policy | 파라미터 수(실측) |
|---|---|---|---|---|---|
| PPO | 기본 | Schulman+ 2017 (arXiv:1707.06347) | SB3 Box(3) — 연속 Gaussian, 채널은 비닝 | on-policy(구조), 실제로는 오프폴리시 스트림에 근사 적용(명시) | 10,887 |
| SAC | 기본 | Haarnoja+, ICML 2018 | SB3 Box(3) — tanh-Gaussian, 채널 비닝 | off-policy | 357,643 |
| TD3 | 기본 | Fujimoto+, ICML 2018 | SB3 Box(3) — 결정적+외부노이즈, 채널 비닝 | off-policy | 772,810 |
| RES-MAPDDPG | 최신 | Li+, IEEE TVT 75(7) 2026, DOI 10.1109/TVT.2026.3662431 | 파라미터화 액션(P-DQN류): 이산 채널 argmax-Q + 연속(Δ,p) 액터 | off-policy | 301,656 |
| MA2HDQN | 최신 | Hong+, IEEE TVT 75(6) 2026, DOI 10.1109/TVT.2025.3640225 | 분기형: MA-D3QN(이산 채널) + i-DDPG(연속 Δ,p) | off-policy | 148,880 |
| I-HAMAPPO | 최신 | Chen+, IEEE TWC 25 2026, DOI 10.1109/TWC.2025.3626670 | 하이브리드: Categorical(채널)+Gaussian(Δ,p), 중앙집중 크리틱 | on-policy(근사) | 68,657 |
| SPAM-D3QN | 유사 | Bai+, IEEE TVT 73(4) 2024, DOI 10.1109/TVT.2023.3333825 | 완전이산 결합인덱스(Δ×p×ch) 듀얼링더블DQN | off-policy | 87,426 |
| CARLTON | 유사 | Cohen+, IEEE TWC 24(1) 2025, DOI 10.1109/TWC.2024.3491035 | 브랜칭 DQN(Δ,p,ch 3브랜치), DeepMellow 백업 | off-policy | 44,624 |
| MADDPG-MT | 유사 | Parvini+, IEEE TVT 72(8) 2023, DOI 10.1109/TVT.2023.3259688 | 연속(Δ,p) DDPG + Gumbel-Softmax 채널, 태스크분해 이중크리틱 | off-policy | 222,748 |

**파라미터 수 9개 전부 서로 다름** — 과거 "MAPPO가 PPO의 구조적 복제본(파라미터 수 동일)" 사건과 같은 문제는 이번 9종에서 재발하지 않음(실측 확인).

측정 방법: `/home/imnyj/venv/bin/python etc/scripts/verify_all_baselines.py` 실행. 체크포인트/로그 파일 생성 없음(스크립트 자체가 인메모리로만 동작).

---

## 산출물 2: 결함 검토

### 요약표

| # | 심각도 | 대상 | 한 줄 요약 |
|---|---|---|---|
| 1 | **[치명]** | `src/evaluate.py`, `src/hpo.py` | 9종 실제 baseline을 문자열 이름으로 벤치마크/HPO 실행하면 **전부 크래시**하거나(evaluate) **model_cls 미주입 시 즉시 예외**(hpo) — 두 파이프라인의 최상위 진입점이 구세대(폐기된) 모델명 체계에 머물러 있고 `src.baselines.get_baseline()`에 연결된 적이 없음 |
| 2 | **[중대]** | `src/hpo.py::sample_hparams` | PPO/SAC/TD3/RES-MAPDDPG/MA2HDQN/I-HAMAPPO/MADDPG-MT에 대해 Optuna가 샘플링하는 하이퍼파라미터 키 이름 다수가 실제 생성자 인자명과 불일치 — `**hparams`로 조용히 흡수되어 **아무 효과 없이 버려짐** (실측 확인) |
| 3 | [경] | `spam_d3qn.py`, `carlton.py` 주석 | docstring이 언급하는 `etc/scripts/verify_baselines_similar.py`가 실제로 존재하지 않음(문서-현실 불일치, 기능 결함 아님) |
| 4 | [확인필요] | `src/hpo.py:331-332` | `model.update(batch)` 호출부의 `except Exception: pass` — 실패를 로그조차 없이 삼킴 |
| 5 | 결함 아님(확인 완료) | 9종 전부 | Δ 매핑, 액션 범위, 크레딧 할당(action_idx 전체 복구), `optimizer.step()` 실동작, 이벤트구동 루프 — 전부 설계 준수 확인 |

---

### 1. [치명] `evaluate.py`/`hpo.py` 최상위 진입점이 실제 9종 baseline과 연결되어 있지 않음

**근거(실측, 아래 명령으로 직접 재현):**

```python
from src.evaluate import instantiate_model, normalize_model_name
from src.baselines import get_baseline

instantiate_model("PPO")
# -> NotImplementedError: Baseline models scraped. New IEEE baselines to be provided.

normalize_model_name(get_baseline("PPO"))
# -> AttributeError: type object 'PPO' has no attribute 'replace'
```

`src/hpo.py`도 동일한 뿌리의 문제:

```python
from src.hpo import run_hpo_study
run_hpo_study(model_name="PPO", n_trials=1)
# -> NotImplementedError: Baseline models scraped. New IEEE baselines to be provided.
#    Cannot run HPO for 'PPO' without model_cls.
```

**원인.** `src/baselines/`가 9종(PPO, SAC, TD3, RES-MAPDDPG, MA2HDQN, I-HAMAPPO, SPAM-D3QN, CARLTON,
MADDPG-MT)으로 전면 재작성됐지만, `src/evaluate.py`와 `src/hpo.py`는 그 이전 세대의 모델명 체계
(`HybridPPO`, `HybridSAC`, `HybridTD3`, `MAPPO`, `HyARPPO`, `MPDQN`, `PureAoI`, `DuelingQAoI`, `SACAoI` —
`Conversation.md` 5절의 2026-08-27 FAIL 판정에서 "실제 구현체"로 지목되었다가 이후 전량 폐기된 이름들)에
그대로 머물러 있다. 두 파일 어디에도 `from src.baselines import ...`가 없다(grep 확인, `run_all.py`와
`etc/scripts/verify_all_baselines.py`만 연결되어 있음).

구체적으로:
- `evaluate.py::CANONICAL_EVAL_MODELS = ["HeuristicScheduler"]` — `run_full_benchmark()`의 기본
  대상 모델이 휴리스틱 하나뿐이고, 9종 RL baseline은 목록에 아예 없음.
- `evaluate.py::instantiate_model()`은 `"HeuristicScheduler"`가 아닌 모든 문자열에 대해
  `NotImplementedError("Baseline models scraped...")`를 던진다. 이것은 `Conversation.md`가 기록한
  2026-08-27 회귀 사건("baselines_scraped_m4로 이동" 당시의 스텁 메시지)와 **동일한 문구**이며,
  baseline이 실제로 존재하는 지금까지 지워지지 않고 남아 있다.
- `run_full_benchmark()`의 루프는 `model_name`(문자열 가정)을 먼저 `normalize_model_name()`에 넘기므로,
  호출자가 실제 클래스(`get_baseline("PPO")` 등)를 넘겨도 `.replace()` 호출에서 `AttributeError`로
  더 일찍 죽는다. 즉 **문자열로도, 클래스로도 9종을 평가할 방법이 없다.**
- `hpo.py::run_hpo_study()`는 문자열 `model_name`만 주어지고 `model_cls`가 없으면 무조건
  `NotImplementedError`를 던진다. `hpo.py::main()` → `run_all_baselines_hpo()` → `run_hpo_study()`
  경로 전체가 `model_cls`를 넘기지 않으므로, **`python src/hpo.py`를 문서화된 방식대로 실행하면
  첫 모델에서 즉시 크래시한다.**

**테스트가 이를 놓친 이유.** `tests/test_hpo.py::test_09_scraped_baseline_raises_error`가
"`run_hpo_study(model_name="HybridPPO", n_trials=1)`은 `NotImplementedError`를 던져야 한다"를
**통과 기준으로 고정**해 놓았고, `tests/test_evaluation.py::test_09_run_full_benchmark_end_to_end`는
`models=["HeuristicScheduler"]`로만 벤치마크를 검증한다. 두 테스트 모두 9종이 존재하기 전 세대의
가정을 그대로 lock-in한 것이라, "테스트 119/119 통과"라는 현재 상태와 이 결함이 모순되지 않는다
(실제로 재실행: `pytest tests/test_hpo.py tests/test_evaluation.py` → 26 passed).

**영향.** `src/baselines/`의 9종 구현 자체는 건전하다(아래 5번 참조). 하지만 design_spec_v2.md 11절이
남은 작업으로 명시한 "Optuna HPO"와 "다중 밀도·다중 시드 벤치마크"는 **현재 코드로는 어느 쪽도 9종
실제 baseline에 대해 실행할 수 없다** — 각각 즉시 예외를 던지거나(HPO), HeuristicScheduler로만
동작한다(벤치마크). 본훈련(`run_all.py`)은 이 결함의 영향을 받지 않는다(별도로 `get_baseline()`을
올바르게 사용함, 확인 완료).

**확인 필요.** 이 두 파일에 대해 별도의, 아직 병합되지 않은 수정 브랜치/작업이 존재하는지는 이번
검토 범위 밖이라 알 수 없음. 현재 워킹트리 상태 기준의 사실만 보고한다.

---

### 2. [중대] `hpo.py::sample_hparams`의 하이퍼파라미터 키가 실제 생성자 인자명과 불일치

결함 1(위)이 먼저 해소되어 `model_cls`가 올바르게 주입된다고 가정해도, 샘플링되는 하이퍼파라미터
자체가 대부분 목표에 도달하지 못한다. 실측(체크포인트 미생성, 순수 인스턴스화):

```python
from src.baselines.sb3_ppo import PPO
m = PPO(state_dim=17, num_channels=4,
        lr=999.0, hidden_dim=999, clip_ratio=0.99, entropy_coef=0.99, value_coef=0.99, gamma=0.5)
m.gamma                              # 0.5   (정상 반영됨)
m.policy.optimizer.param_groups[0]["lr"]   # 0.0003  (lr=999.0이 반영 안 됨)
m._sb3.clip_range(1.0)               # 0.2     (clip_ratio=0.99가 반영 안 됨)
m._sb3.ent_coef                      # 0.0     (entropy_coef=0.99가 반영 안 됨)
m._sb3.vf_coef                       # 0.5     (value_coef=0.99가 반영 안 됨)
m.hparams                            # {'lr': 999.0, 'hidden_dim': 999, 'clip_ratio': 0.99, ...} — 저장만 되고 미사용
```

원인은 `sample_hparams()`가 (결함 1과 같은 뿌리인) 구세대 모델명 분기 `"HybridPPO"/"HybridSAC"/
"HybridTD3"`에서 `{"lr", "hidden_dim", "clip_ratio", "entropy_coef", "value_coef"}` 같은 키를
샘플링하는데, 실제 `PPO.__init__`의 인자명은 `learning_rate`, `clip_range`, `ent_coef`, `vf_coef`이고
`hidden_dim`은 아예 없다(정책 크기는 `policy_kwargs`로 넘겨야 함). `BaseRLModel.__init__`이 이름이
안 맞는 키워드를 전부 `**hparams`로 조용히 받아 `self.hparams`에 저장만 하고 실제 모델 구성에는
쓰지 않으므로, **`TypeError`도 나지 않고 그냥 무효화된다** — 사용자가 알아챌 방법이 없는 조용한 결함.

모델별 영향 정도(코드 대조로 확인, `gamma`/`tau`처럼 우연히 이름이 같은 키는 실제로 반영됨):

| 모델 | 실제 반영되는 것 | 무효화되는 것 |
|---|---|---|
| PPO | `gamma` | `lr`, `hidden_dim`, `clip_ratio`, `entropy_coef`, `value_coef` (실측 확인) |
| SAC | `gamma`, `tau` | `lr`, `hidden_dim` |
| TD3 | `gamma`, `tau` | `lr`, `hidden_dim`, `policy_noise`(실제 인자명 `target_policy_noise`), `noise_clip`(실제 `target_noise_clip`), `policy_freq`(실제 `policy_delay`) |
| RES-MAPDDPG, MA2HDQN, I-HAMAPPO, MADDPG-MT | `hidden_dim`, `gamma`(제네릭 폴백 분기로 감) | `lr`(실제 인자명은 `lr_actor`/`lr_critic`/`lr_q` 등 분리형) |
| SPAM-D3QN, CARLTON | `lr`, `hidden_dim`, `gamma` 전부 정상 반영 | (우연히 제네릭 폴백 키와 실제 인자명이 일치) |

**영향.** Optuna가 탐색·기록하는 "최적 하이퍼파라미터"의 상당수(특히 학습률)가 실제로는 학습에
아무 영향을 주지 못한 채 결과 CSV에 값만 남는다. 결함 1로 인해 이 경로 자체가 현재 실행 불가능하므로
당장 결과를 오염시키고 있지는 않지만, 결함 1을 고치는 순간 이 결함이 그대로 드러난다 — **결함 1을
해소할 때 반드시 함께 고쳐야 할 선결 이슈**로 기록한다.

---

### 3. [경] 존재하지 않는 검증 스크립트를 문서화

`src/baselines/spam_d3qn.py`(122-124행)와 `src/baselines/carlton.py`(90-91행) 모두
"그 버그는 이전 세대 dueling-Q 모델에서 발견·수정되었고 `etc/scripts/verify_baselines_similar.py`에서
검증(assert)된다"고 명시하지만, 해당 파일은 `etc/scripts/` 어디에도 없다(`find` 확인). 실제 동작
자체는 정상임을 이번 검토에서 직접 실측했으므로(아래 5번) 기능적 결함은 아니지만, 코드 주석이
가리키는 증거 파일이 실재하지 않는다는 점은 "주장은 실제로 읽고 확인한 것"이어야 한다는 이 검토
원칙에 비추어 볼 때 남겨두면 안 되는 참조다.

---

### 4. [확인필요] `hpo.py:331-332`의 조용한 예외 흡수

```python
try:
    model.update(batch)
except Exception:
    pass
```

`evaluate_model_in_env()`의 롤아웃 도중 학습 스텝에서 `model.update()`가 실패해도 아무 로그 없이
넘어간다. 상위의 `evaluate_trial_multiseed()`에는 시드 단위 `except Exception as e: logger.warning(...)`가
있어 완전한 무음은 아니지만, "그 시드에서 학습이 몇 번 실패했는지"는 어디에도 남지 않는다. 결함 1이
막고 있어 현재 이 경로가 실행되는지 자체가 불확실하므로, 심각도는 [확인필요]로 표시한다 — 결함 1을
해소한 뒤 재검토가 필요하다.

---

### 5. 결함 없음으로 확인된 항목 (실측 근거 포함)

- **액션 범위 준수**: `etc/scripts/verify_all_baselines.py` 실행 결과 9종 전부 300회 샘플링에서
  Δ∈[0.1,45.0], p∈[10.0,23.0], ch∈{0,1,2,3} 범위를 벗어나지 않음(PASS). 극단 입력(로짓 999 등)에
  대해서도 각 모델의 `tanh`/`sigmoid`/`clip` 경유 경로가 클램프를 보장함을 코드 검토로 확인.
- **Δ 매핑 일관성**: 9종 전부 실제 그랜트 산출에 `ActionDecoder.delta_from_unit`(기하)을 사용함을
  각 파일에서 직접 확인. `decode_action`(선형)을 그랜트 산출에 쓰는 모델은 없음. 단, `SPAM-D3QN`,
  `CARLTON`, `MADDPG-MT`는 리플레이 버퍼에 저장할 `raw_action`을 **직렬화 목적으로만**
  `ActionDecoder.encode_action`(선형 로짓)에 통과시키는데, 이는 그랜트 자체의 Δ 값과는 무관하고
  (그랜트는 이미 기하격자에서 뽑힌 값), 인코드→디코드가 단조함수라 왕복이 정확함을 확인했으므로
  결함이 아니다.
- **크레딧 할당**: `RetrospectiveReplayBuffer`/`TransitionStreamer`가 `action_idx`를 전달하지 않는
  현재 파이프라인(각 모듈 docstring이 명시)에서, 5개 이산/혼합 baseline(`RES-MAPDDPG`, `MA2HDQN`,
  `I-HAMAPPO`, `SPAM-D3QN`, `CARLTON`) 전부 `raw_action`에서 **채널·Δ·전력 세 요소 전부**를 정확히
  복구함을 코드에서 확인(과거 "20개 중 4개만 학습" 버그의 패턴 — 일부 요소만 복구 — 없음).
  `verify_all_baselines.py`의 `update[idx=True]`/`update[idx=False]` 양쪽 케이스가 9종 전부 PASS.
- **`update()`가 실제로 가중치를 이동**: `verify_all_baselines.py`의 `moved()` 함수가 `update()`
  전후 `state_dict()` floating 텐서를 `torch.allclose`로 비교해 실제 이동을 확인하며, 9종 전부
  `n_moved > 0`으로 PASS. `optimizer.step()` 호출 자체도 전 파일에서 코드 검토로 확인.
- **명칭-동작 일치 / 파라미터 수 중복 여부**: 9종 파라미터 수를 전부 실측(위 비교표) — 10,887 /
  357,643 / 772,810 / 301,656 / 148,880 / 68,657 / 87,426 / 44,624 / 222,748로 **전부 상이**.
  과거 "MAPPO가 PPO의 구조적 복제본" 같은 사건 재발 없음. 각 모듈 docstring이 CTDE·다중에이전트
  주장의 실제 범위(단일 RSU 중앙집중이 곧 "배치"이지 별도 가정이 아님)를 스스로 한정하고 있어
  과장된 명칭 사용도 발견되지 않았다.
- **이벤트 구동 루프**: `run_hot_swap_training`(hot_swap_trainer.py), `evaluate.py::evaluate_single_run`,
  `hpo.py::evaluate_model_in_env` **세 곳 모두** `step_info["needs_decision"]`에 포함된 차량에만
  새 그랜트를 요청하고, 나머지는 기존 그랜트를 유지함을 코드에서 확인. 매 스텝 전 차량에 grant를
  주는 패턴은 없음.
- **hpo.py 보상 가중치**: `REWARD_WEIGHT_KEYS = ("w1","w2","w3","w4")`가 실제로 Optuna 탐색공간에
  있고(`sample_reward_weights`), 로그스케일 샘플 후 합=1로 정규화된다. `w1` 범위(0.10~1.00)가
  `w2/w3/w4` 범위(0.02~0.60)보다 높게 설정되어 있어 정규화 후 오차항이 우세해지는 경향은 있으나,
  이는 설계 기본값(0.5/0.2/0.2/0.1)과 방향이 일치하고 하한이 0이 아니라 어느 항도 구조적으로
  0에 강제되지는 않는다 — 10절 실측(혼잡항 0.73%)이 이 범위의 인공물이 아니라 물리(802.11p
  에어타임)에서 나온다는 것은 `design_spec_v2.md` 10절의 밀도 스윕으로 이미 별도 검증되어 있다.
- **빈 구현/TODO/pass**: `src/baselines/*.py`, `run_all.py`, `src/evaluate.py`, `src/hpo.py` 전체
  grep 결과 `NotImplementedError`는 `base_agent.py`의 추상메서드 2곳(정상, 서브클래스가 전부 구현함
  확인)과 위 결함 1의 두 곳뿐. `except: pass`류는 위 결함 4의 한 곳뿐.

---

## 부록: 실측 명령 로그

```bash
/home/imnyj/venv/bin/python etc/scripts/verify_all_baselines.py   # 9/9 PASS, 파라미터 수 실측
/home/imnyj/venv/bin/python -m pytest tests/test_hpo.py tests/test_evaluation.py -q   # 26 passed
# 개별 인스턴스화 테스트(체크포인트/로그 파일 생성 없음, /tmp도 사용 안 함 — 순수 메모리):
#   src.baselines.sb3_ppo.PPO(...) 로 하이퍼파라미터 무효화 실측
#   src.evaluate.instantiate_model("PPO") -> NotImplementedError 재현
#   src.evaluate.normalize_model_name(get_baseline("PPO")) -> AttributeError 재현
#   src.hpo.run_hpo_study(model_name="PPO", n_trials=1) -> NotImplementedError 재현
```

`checkpoints/`, `logs/training/` 디렉토리는 검토 시작 시점과 동일하게 비어 있음(오염 없음).
