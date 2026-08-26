# S2 — 확률적 SINR 업링크 (Communications.py + aoi_env.py)

S1 환경 위에 grant `(Δ, 서브채널, 전력)`과 **SINR 확률 성공판정**을 배선한 구현·검증본입니다.

## 무엇을 추가했나

**`Communications.py`** — 업링크 SINR 모델(경로손실 + 열잡음 + Rayleigh 페이딩 간섭):
- `path_loss_db`, `rx_power_mw`, `noise_floor_mw`, `rayleigh_success_prob`
- `judge_uplink(group)` : 동일 서브채널 그룹의 각 전송에 대해 상호 간섭 하 성공확률 `{id: P_succ}` 반환. 표준 폐형: `P = exp(-γ_th·N0/S)·Π 1/(1+γ_th·I_k/S)`.
- 파라미터: `NUM_SUBCHANNELS=4`, `TX_POWER_LEVELS_DBM=[20,25,30]`, `SINR_TH_DB=0`, `PL_EXP=2.3`, `FREQ_HZ=5.9e9`, `TOTAL_BW_HZ=20e6`.

**`aoi_env.py`** — E2 전송이 SINR 판정을 거치도록 교체:
- `decide_grant()` → `(Δ, ch, p)` 3-튜플 반환(placeholder: 고정 Δ, round-robin 서브채널, 중간 전력). **S3/S4에서 RL 에이전트로 교체.**
- E2 시 차량이 RSU의 `pending_tx`에 전송 시도를 큐잉. RSU가 매 스텝 동일 서브채널끼리 묶어 `judge_uplink`로 판정, **성공분만** `on_update`로 갱신, 실패는 낡은 추정 유지.
- RSU가 차량보다 먼저 스텝되므로 한 스텝 지연 후 해소(1-step processing delay).

## 검증 결과 (실제 SUMO 1.27.1)

**SINR 단위 거동**: 단독 전송은 셀 전역 가능(100m 0.999 → 800m 0.865), 동일 서브채널 경합↑ → 성공↓(1→0.99, 2→0.50, 4→0.12, 6→0.03), 전력↑ → 자기 성공↑·타 차량↓.

**환경 통합 (E2가 SINR을 거침)**:
- 밀도↑ → 채널당 경합↑ → 성공률↓ (density 15/30/50 → 0.066/0.036/0.022)
- 서브채널↑ → 성공률↑ (2/4/8ch → 0.012/0.039/0.10 @density40)
- Δ↑(갱신 덜함) → 부하 분산 → 성공률↑ (Δ 1/3/6s → 0.065/0.325/0.459 @density15)
- `tx_attempts = tx_success + tx_fail` 정합. 성공분만 RSU 갱신.

## 이 결과가 말해주는 것 (S3/S4 설계 함의)

1. **AoI vs 혼잡 트레이드오프가 실측으로 드러남**: 자주 갱신하면 신선하지만 충돌(성공↓), 드물게 갱신하면 성공하지만 낡음. RL이 이 균형을 차량별로 잡아야 함.
2. **"정지=갱신 불필요"의 함정**: 갱신이 희박하면 RSU가 차량의 정지를 *모른 채* 낡은 이동속도로 외삽 → 정지 차량이 오히려 큰 오차. 따라서 스케줄러는 **동역학이 바뀌는 순간(예: 정지 진입)엔 반드시 한 번 갱신**시키고, 그 뒤 정지 상태에서 백오프해야 함. 이 nuance가 보상 설계(S3)에서 중요.
3. placeholder(모든 차량 매초·round-robin)는 최악 베이스라인. RL은 (a) 동역학에 따라 Δ 차등, (b) 서브채널·전력 분산으로 이를 크게 개선할 여지가 있음.

## 실행법 (요지)

S1과 동일하되 `comm.NUM_SUBCHANNELS` 등으로 자원을 조정. `env.reset_env()` 후 `sim.run()`, `env.METRICS.summary()`의 `tx_success_rate`, `mean_contenders_per_ch`, `mean_interval_err_integral` 등을 확인.

## 다음 단계 (S3)

`decide_grant`를 RL 에이전트 인터페이스로 교체: State 벡터화(나이·동역학·신호맥락·로컬혼잡·채널·전역 망상태), grant `(Δ,ch,p)` 디코딩, transition/reward 조립(소급 오차 적분 − λ1·혼잡 − λ2 − β(1−P_succ)). 지금 `pending_tx` 해소 지점에서 각 전송의 `P_succ`와 소급 오차가 이미 계산되므로 보상 조립 훅이 자연스럽게 붙습니다.
