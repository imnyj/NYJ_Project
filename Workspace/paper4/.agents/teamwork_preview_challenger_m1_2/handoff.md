# Milestone 1 Handoff Report: 802.11p 채널 및 모빌리티 적대적 검증

- **작성 에이전트**: `challenger_m1_2` (Milestone 1 적대적 검증 챌린저)
- **작성 일시**: 2026-08-24T01:38:15Z
- **타겟 디렉토리**: `/home/imnyj/Workspace/paper4/.agents/teamwork_preview_challenger_m1_2`
- **판정 (Verdict)**: **APPROVE (승인)**

---

## 1. Observation (직접 관측 사실)

1. **802.11p 무선 채널 모델 수식 구현 (`code/sim_engine.py`)**:
   - `reception_probability` 및 `reception_probability_vec` 함수는 $5.9\text{ GHz}$ 주파수, $PL_0 = 47.858\text{ dB}$, $\alpha = 2.0$의 Log-distance Path Loss와 $m=3$인 Nakagami-$m$ CCDF를 적용합니다.
   - 10,000개 무작위 거리/파워 쌍에 대한 스칼라-벡터 연산 최대 오차는 $2.39 \times 10^{-15}$로 완벽히 일치했습니다.
   - 송신 파워 $P_{tx} = +5\text{ dBm}$에서 거리에 따른 이론적 수신율은 $25\text{m}(100.00\%) \to 125\text{m}(89.23\%) \to 275\text{m}(8.74\%)$로 급격히 감쇄합니다.
   - $P_{tx} = +20\text{ dBm}$에서는 링크 마진이 커 $300\text{m}$에서도 $99.87\%$의 물리적 수신율을 유지합니다.

2. **CBR 충돌 감쇄 및 로컬 센싱 (`code/sim_engine.py`)**:
   - `col_factors = np.maximum(0.1, 1.0 - rcv_cbrs * 0.8)`로 정의되어, $CBR = 0.0$일 때 $1.0$, $CBR = 0.5$일 때 $0.6$, $CBR = 1.0$일 때 $0.2$로 정확히 스케일링됩니다.
   - 200대 차량의 초고밀도 동시 송신 시뮬레이션에서 CBR은 $1.0$으로 포화되었고, 충돌 손실로 인해 PDR이 $19.94\%$로 억제되었습니다.

3. **거리별 PDR / AoI 몬테카를로 교차 검증 (`etc/scripts/test_channel_empirical.py`)**:
   - 6개 거리 구간(25m, 75m, 125m, 175m, 225m, 275m)에 대한 5,000패킷 실측 결과:
     * PDR: $76.00\% \to 75.14\% \to 68.76\% \to 47.38\% \to 21.24\% \to 6.42\%$ ($\text{Spearman } \rho = -1.0$)
     * AoI: $32.02\text{ ms} \to 32.52\text{ ms} \to 45.88\text{ ms} \to 114.72\text{ ms} \to 354.28\text{ ms} \to 1065.28\text{ ms}$ ($\text{Spearman } \rho = +1.0$)

4. **SUMO 실제 시뮬레이션 및 `cbr_history` 검증**:
   - $N=10, 25, 40$ 차량 밀도에 대한 25초(250스텝) 시뮬레이션 수행:
     * 웜업(5초=50스텝) 이후 $cbr\_history$ 길이는 정확히 $200$개로 누락이 없습니다.
     * 모든 스텝의 $CBR$은 $[0.0, 1.0]$ 범위 내에 엄격히 위치하며 결측치(NaN/Inf)는 0건입니다.
     * 스텝 간 델타는 평균 $0.0024 \sim 0.0040$, 최대 $0.0107$로 매우 연속적이고 안정적입니다.
     * 차량 밀도가 $10 \to 25 \to 40$대로 증가함에 따라 평균 CBR은 $0.0124 \to 0.0281 \to 0.0387$로 단조 증가하고, 평균 PDR은 $98.17\% \to 96.53\% \to 95.59\%$로 감소, 평균 AoI는 $133.59\text{ ms} \to 137.21\text{ ms} \to 143.75\text{ ms}$로 증가했습니다.

5. **적대적 경계 조건 검증**:
   - 차량 이탈 시 `aoi_tracker.remove_vehicle`을 통해 잔여 상태가 즉시 소거되어 메모리 누수나 고아 상태(Orphaned pairs)가 발생하지 않습니다.
   - 단일 차량(차량 1대) 환경에서 에러 없이 $CBR = 0.0$, $AoI = 0.0\text{ ms}$, $PDR = 100.0\%$가 정상 반환됩니다.

---

## 2. Logic Chain (논리 추론 체인)

1. **수학적 무결성**:
   - $\text{SNR} = P_{tx} - PL_0 - 10\alpha \log_{10}(d) - N_{\text{thermal}}$ 수식에 따라 거리가 멀어질수록 수신 SNR이 단조 감소합니다 (Observation 1).
   - $m=3$인 Nakagami-$m$ Gamma 분포의 CCDF $e^{-x}(1 + x + x^2/2)$는 SNR이 감소할수록($x$가 증가할수록) 엄격하게 단조 감소하여 물리적 채널 감쇄를 충실히 반영합니다 (Observation 1).
2. **패킷 전달율(PDR)과 정보 노후화(AoI)의 반비례 상관성**:
   - 거리가 증가하면 $P_{success}$가 감소하여 패킷 수신 실패율이 증가합니다.
   - 패킷이 손실되면 수신 차량의 수신 시각 $t_{rx}$ 갱신이 누락되어 직전 수신 시점 $t_{gen}$과의 차이 $(t_{sim} - t_{gen})$인 AoI가 지속적으로 누적 증가합니다 (Observation 3).
   - 이로 인해 Distance vs PDR은 음의 상관관계($\rho = -1.0$), Distance vs AoI는 양의 상관관계($\rho = +1.0$)를 나타냅니다.
3. **트래픽 밀도 및 CBR 시계열 무결성**:
   - 동일 도로망에서 차량 수가 증가하면 $300\text{m}$ 통신 반경 내 패킷 발생 빈도가 높아져 단위 시간당 채널 점유율 $CBR$이 증가합니다.
   - $CBR$ 상승은 충돌 감쇄 계수 $f_{\text{col}}$를 저하시켜 전체 PDR을 하락시키고 AoI를 증가시킵니다 (Observation 4).
   - `cbr_history`는 웜업 이후 매 스텝 정확히 기록되며 유효 범위 $[0.0, 1.0]$ 내에서 매끄럽게 전이됩니다.
4. **결론 도출**:
   - SUMO 모빌리티와 802.11p Nakagami-m 채널, CBR 감쇄 및 AoI 추적 엔진이 모든 이론적/경험적 요구사항을 완벽히 만족하므로 M1 채널/모빌리티 단계는 **APPROVE** 판정입니다.

---

## 3. Caveats (주의 사항 및 전제 조건)

- **공칭 송신 파워 (+20 dBm)에서의 통신 반경**:
  * 802.11p 표준 최고 송신 파워인 $+20\text{ dBm}$ (100mW)에서는 $300\text{m}$에서도 물리적 수신 확률이 약 $99.87\%$에 달합니다. 따라서 $+20\text{ dBm}$ 고정 송신 시 거리별 PDR 저하는 주로 패킷 간 충돌($f_{\text{col}}$)에 의해 주도됩니다.
  * 강화학습(DCC) 에이전트가 송신 파워를 적응적으로 낮추는 경우(예: $0\text{ dBm} \sim 10\text{ dBm}$)에는 거리별 페이딩 감쇄가 매우 가파르게 작용합니다.
- **DENSITY 파라미터 전달 규칙**:
  * `SimulationRunner` 실행 시 `config["DENSITY"]`를 특정 값으로 고정하여 스윕하려면 `method_params={"n_vehicles_sweep": density}`를 반드시 명시적으로 전달해야 합니다.

---

## 4. Conclusion (최종 판정 및 결론)

- **최종 판정**: **APPROVE (승인)**
- SUMO 기반 차량 모빌리티 연동 및 802.11p Nakagami-$m$ 무선 채널 모델, CBR 센싱 및 충돌 감쇄 메커니즘이 모두 경험적/통계적으로 검증되었습니다.
- 거리에 따른 PDR 감소와 AoI 증가가 실측 데이터로 명확히 입증되었으며, `cbr_history`는 스텝별 누락 없이 $[0.0, 1.0]$ 범위 내에서 완전 무결하게 유지됩니다.
- 다음 단계(M2 가짜 데이터 제거 및 Optuna 하이퍼파라미터 최적화)로 진행할 준비가 완료되었습니다.

---

## 5. Verification Method (독립 검증 방법)

누구나 아래 명령어를 통해 본 검증 결과를 동일하게 재현할 수 있습니다.

```bash
# 1. 독립 채널 및 모빌리티 경험적 검증 스크립트 실행
python3 /home/imnyj/Workspace/paper4/etc/scripts/test_channel_empirical.py

# 2. 결과 JSON 파일 확인
cat /home/imnyj/Workspace/paper4/etc/scripts/test_channel_empirical_results.json

# 3. M1 통합 단위 테스트 실행
pytest -v /home/imnyj/Workspace/paper4/code/test_m1_audit.py
```
