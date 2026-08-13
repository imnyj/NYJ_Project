# Handoff Report: R2 Mortgage Mathematical Formulation & Python Engine Architecture

**Agent**: teamwork_preview_explorer_m1_2  
**Milestone**: M1 (Financial Data Engine & Analysis)  
**Date**: 2026-08-12  

---

## 1. Observation (직접 관측 정보)

- **참고 문서 및 세부 규정**:
  - `/home/imnyj/Workspace/House/ORIGINAL_REQUEST.md` (Lines 19-21): R2 대출 시나리오 보유 현금 2.3억 원, 3.5억/3.75억/4.0억 아파트 필요 대출금 산출, 디딤돌 vs 시중은행 주담대 비교, 대출 부대비용(근저당 설정비, 대출 인지세, 보증료) 산출 요구.
  - `/home/imnyj/Workspace/House/PROJECT.md` (Lines 28-30): 보유 현금 2.3억 원 (본인 3천만 + 본인 부모님 1억 + 여자친구 부모님 1억), 디딤돌대출 금리 3.0~3.3%, 대출 부대비용 명세.
  - `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_survey_1/survey_budget.md` (Lines 148-152): 3.5억 시나리오 필요 대출금 1.2억 원 (LTV 34.29%), 3.75억 시나리오 1.45억 원 (LTV 38.67%), 4.0억 시나리오 1.7억 원 (LTV 42.50%). 연간 보너스 총 1,200만 원 (1/7월 특강비 100만, 2/8월 교연비 500만).
  - `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_survey_3/survey_legal_mortgage.md` (Lines 130-144): 근저당권 설정비 은행 100% 부담 (차주 잡비 ~2만 원), 대출 인지세 15만 원 split 50:50 (차주 실부담 75,000원 고정), HF/HUG 보증료 연 0.05%~0.10%.

---

## 2. Logic Chain (논리 추론 과정)

1. **대출 원금 산출**:
   - $\text{필요 대출금 } P = \max(0, \text{매매가 } S - \text{보유현금 } 2.3\text{억})$.
   - 3.5억 매매 시 $P = 1.2\text{억}$, 3.75억 매매 시 $P = 1.45\text{억}$, 4.0억 매매 시 $P = 1.7\text{억}$.
2. **대출 상품 상환액 비교 수식 도출**:
   - 표준 원리금균등상환(CPM) 수식: $M = P \cdot \frac{r(1+r)^N}{(1+r)^N - 1}$.
   - 디딤돌대출(신혼부부 특례 3.15%)과 시중은행 주담대(4.25%) 적용 시 30년 월 상환액:
     - 1.2억: 디딤돌 515,643원 vs 시중은행 590,266원 (차액: 월 74,623원 디딤돌 우세)
     - 1.45억: 디딤돌 623,068원 vs 시중은행 713,239원 (차액: 월 90,171원 디딤돌 우세)
     - 1.7억: 디딤돌 730,494원 vs 시중은행 836,211원 (차액: 월 105,717원 디딤돌 우세)
3. **보너스 투입 원금 조기상환 알고리즘**:
   - 매월 이자 $I_m = B_{m-1} \cdot r$ 차감 후 정기 원금 $A_m$ 차감.
   - 1월/7월 100만 원, 2월/8월 500만 원 보너스를 대출 원금 차감 $B_m = \max(0, B_{m-1} - A_m - S_{\text{bonus}})$에 직접 적용.
   - 약정 월 상환액 $M$을 유지함으로써 상환 소요 기간(만기)을 가속 단축함.
4. **대출 부대비용 법적 분담 수식화**:
   - 근저당 설정비: 은행 100% 부담 (차주 실부담 잡비 2만 원 고정).
   - 대출 인지세: 인지세법상 1억~10억 구간 15만 원의 50% = 차주 실부담 75,000원 고정.
   - 보증료: HF/HUG MCG 보증료 연 0.05%~0.10% 수식화.
5. **파이썬 계산 엔진 아키텍처 설계**:
   - `OneTimeCostCalculator`, `MortgageLoanCalculator`, `FinancialSimulationEngine` 클래스로 책임 분리.
   - 단독 실행 API 함수(`calculate_r1_costs`, `calculate_r2_loans`, `run_all_scenarios`) 및 CLI `argparse` 옵션 설계.

---

## 3. Caveats (한계 및 주의사항)

- **금리 변동성**: 디딤돌대출 금리는 3.0~3.3%, 시중은행 금리는 3.9~4.6% 범위를 가집니다. 본 모델 기본값은 각각 3.15% 및 4.25%를 적용하였으며, 시뮬레이터 파라미터를 통해 가변 조정할 수 있도록 설계되었습니다.
- **보증료 납부 방식**: 보증료는 연단위 분납(잔액 연동) 또는 일시납 선택이 가능합니다. 엔진 아키텍처는 두 방식을 모두 수용 가능하도록 연율 매개변수를 지원합니다.

---

## 4. Conclusion (최종 결론)

- R2 대출 시나리오 수식 모델 및 대출 부대비용 법정 분담 수식이 완전하게 명세화되었습니다.
- `etc/scripts/calc_engine.py` 모듈 및 클래스 아키텍처 설계가 완료되어 M1 파이썬 개발 단계로 즉시 이관 가능합니다.

---

## 5. Verification Method (독립적 검증 방법)

1. **문서 검증**:
   - `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_m1_2/explorer_m1_2.md` 파일을 통해 수식 및 클래스 구조 확인.
2. **수식 검증**:
   - 1.2억 대출, 금리 3.15%, 360개월 CPM 공식 적용 시 월 515,643원 출력 여부 확인.
   - 대출 인지세 차주 부담액이 1.2억/1.45억/1.7억 대출 모두 75,000원으로 일치하는지 확인.
