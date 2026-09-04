# -*- coding: utf-8 -*-
import sys, os, re
sys.path.insert(0, "/home/imnyj/Command/core")
from lock_manager import LockManager
from audit_logger import AuditLogger

AGENT = "p2-librarian"
p = "/home/imnyj/Workspace/paper2/librarian/parameter_sources.md"
txt = open(p).read()

# --- 0절 1차 자료 표에 TR 36.839 추가 ---
row_anchor = "| EN 302 571 |"
new_row = ("| TR 36.839 | 3GPP TR 36.839, Mobility enhancements in heterogeneous networks | "
           "V11.0.0, 2012-09 (Release 11) | 3GPP 원문 확인 |\n")
txt = txt.replace(row_anchor, new_row + row_anchor, 1)

# --- 7절 보강: TR 36.777의 항공 기체 전제 값 ---
anchor7 = "### 비지상망의 경우"
add7 = """### 항공 기체를 전제한 값

TR 36.777은 공중 단말의 이동성을 평가하면서 핸드오버 지연을 두 항목으로 나누어 가정하였다.

| 항목 | 값 | 비고 |
|---|---|---|
| 핸드오버 준비 지연 (HOPreparationDelay) | 50 ms | 원 기지국과 타겟 기지국 사이의 준비 절차 |
| 핸드오버 실행 지연 (HOExecutionDelay) | 40 ms | 단말이 타겟 셀로 옮겨 가는 실행 구간 |
| RSRP 측정 오차 표준편차 | 1.22 dB | 측정 불확실성 |

같은 표에서 단말 고도는 0 m, 50 m, 100 m, 300 m AGL로, 수평 속도는 3 km/h, 30 km/h, 60 km/h, 160 km/h로 두었으며 0 m는 지상 단말을 의미한다.
TR 36.881의 45.5 ms에서 49.5 ms는 실행 구간만을 분해한 값이고, TR 36.777의 50 ms와 40 ms는 준비 구간과 실행 구간을 나눈 값이므로 두 자료를 합쳐 쓰면 중복 계산이 된다.
항공 기체를 전제한 값이 필요하다면 TR 36.777의 두 값을 쓰고, 실행 구간의 내부 분해가 필요하다면 TR 36.881의 표를 쓰는 편이 일관된다.

"""
txt = txt.replace(anchor7, add7 + anchor7, 1)

# --- 8절 신설: 핑퐁 판정 시간 창 ---
anchor8 = "## 8. 미확인 항목 종합"
sec8 = """## 8. 핑퐁 판정에 쓰는 시간 창

이 항목은 `/home/imnyj/Workspace/paper2/visualizer/config.md` 3.2절의 핑퐁 횟수 $N_{PP}$와 핑퐁 비율 $r_{PP}$에 대응한다.

### 표준의 정의

3GPP는 핑퐁 판정을 **최소 체류 시간(MTS, minimum-time-of-stay)** 이라는 파라미터로 규정하며, 그 정의는 TR 36.839 5.2.2절에 있다.
체류 시간(ToS, time-of-stay)의 정의가 먼저 나온다.

> The "Time of stay" in a cell A is the duration from when the UE successfully sends a "handover complete" (i.e. RRCConnectionReconfigurationComplete)-message to the cell A, to when the UE successfully sends a "handover complete" message to another cell B.

즉 체류 시간은 단말이 셀 A에 핸드오버 완료 메시지를 성공적으로 보낸 시점부터 다른 셀 B에 핸드오버 완료 메시지를 성공적으로 보낸 시점까지의 구간이다.
최소 체류 시간의 의미는 같은 절에 명시되어 있다. 단말이 셀과 신뢰할 수 있는 연결을 확립하는 데 필요한 시간에, 효율적인 데이터 전송을 수행하는 데 필요한 시간을 더한 값을 모형화한 것이다.

핑퐁의 정의와 핑퐁률의 정의는 다음과 같다.

> Definition 5: A handover from cell B to cell A then handover back to cell B is defined as a ping-pong if the time-of-stay connected in cell A is less than a pre-determined MTS.

> Definition 6: Ping-pong rate is defined as (number of ping-pongs)/(total number of successful handovers excl. handover failures).

즉 셀 B에서 셀 A로 갔다가 다시 셀 B로 되돌아온 핸드오버는, 셀 A에서의 체류 시간이 미리 정한 최소 체류 시간보다 짧으면 핑퐁으로 센다.
핑퐁률의 분모는 전체 핸드오버가 아니라 핸드오버 실패를 제외한 성공 핸드오버의 총수이다.

또한 같은 절은 핸드오버 실패가 발생한 경우에는 체류 시간을 기록하지 않는다고 규정하며, 핑퐁 거동을 연구할 때는 체류 시간의 누적 분포를 함께 수집하라고 요구한다.

### 권고값과 그 전제

> Recommended MTS value to be used for the simulation is 1 second.

TR 36.839가 모의실험에 쓰도록 권고한 최소 체류 시간은 **1초**이다.

이 값이 전제한 시나리오는 다음과 같다.
TR 36.839는 지상 이종망의 이동성 개선을 다루는 문서이며, 매크로 셀과 피코 셀이 혼재하는 지상 배치를 상정한다.
단말 속도는 3 km/h, 30 km/h, 60 km/h, 120 km/h로 두었고, 대규모 영역 보정에는 30 km/h를 채택하였다.
즉 1초라는 값은 보행자에서 도심 차량에 이르는 지상 이동체를 전제한 값이다.

### 항공 이동체를 전제한 값

공중 단말을 다루는 TR 36.777도 핑퐁률을 성능 지표로 두며, 그 정의는 TR 36.839를 그대로 참조한다.

> NOTE: The definition of Ping-pong and examples of counting method are given in TR 36.839, subclause 5.2.2.

TR 36.777의 이동성 평가 가정 표에도 "Minimum time to stay for ping-pong metric" 항목이 있으나, 원문 표가 서식 문제로 추출되지 않아 그 값을 확인하지 못하였다.
다만 이 문서가 판정 정의를 TR 36.839에서 그대로 가져온다는 점, 그리고 학술 문헌들이 3GPP 관행으로 1초를 일관되게 인용한다는 점을 함께 고려하면 1초를 따랐을 가능성이 높다.
TR 36.777의 공중 단말 속도 가정은 3 km/h에서 160 km/h까지이므로 지상 단말과 같은 속도 구간을 상당 부분 공유한다.

### 대응 기호와 권고

| 기호 | 의미 | 권고 설정 | 근거 |
|---|---|---|---|
| 핑퐁 판정 시간 창 | $N_{PP}$ 계수의 기준이 되는 최소 체류 시간 | 1 s | TR 36.839 5.2.2절의 권고값 |
| $N_{PP}$ | 핑퐁 횟수 | 직전 망으로 되돌아온 전환 가운데 중간 망에서의 체류 시간이 1초 미만인 것의 수 | TR 36.839 Definition 5 |
| $r_{PP}$ | 핑퐁 비율 | $N_{PP}$를 성공한 핸드오버 총수로 나눈 값 | TR 36.839 Definition 6 |

### `config.md` 3.2절과의 차이 두 가지

첫째, `config.md`는 $r_{PP}$의 분모를 핸드오버 횟수 $N_{HO}$로 두었으나, 표준은 분모를 핸드오버 실패를 제외한 성공 핸드오버의 수로 한정한다.
paper2의 시뮬레이터가 핸드오버 실패를 별도로 모형화한다면 분모를 표준에 맞추어 정정해야 하고, 실패를 모형화하지 않아 모든 전환이 성공한다면 두 정의가 일치하므로 그대로 두어도 된다. 어느 쪽인지 본문에 밝히는 편이 좋다.

둘째, 표준은 체류 시간의 시작과 끝을 핸드오버 완료 메시지의 송신 시점으로 규정한다.
paper2의 시뮬레이터가 전환 개시 시점을 기준으로 체류 시간을 재면 핸드오버 지연만큼의 차이가 생긴다.
1초라는 시간 창에 견주면 49.5 ms의 차이는 작으므로 결과를 크게 바꾸지는 않겠으나, 어느 시점을 기준으로 쟀는지 명시해야 재현이 가능하다.

### 유의 사항

1초라는 값이 지상 이동체를 전제한다는 점은 그대로 인용할 때 약점이 될 수 있다.
UAM 기체는 회랑을 따라 예측 가능한 경로로 움직이고 속도도 일정한 편이므로 지상 차량과 이동 특성이 다르다.
값을 그대로 쓰되 전제가 다르다는 사실을 본문에 밝히고, 시간 창을 0.5초와 1초, 2초로 바꾸어 가며 핑퐁 지표가 어떻게 달라지는지 민감도 분석을 함께 제시하는 방법을 권고한다.
그렇게 하면 특정 값을 임의로 골랐다는 지적을 피할 수 있고, 비교 방안 사이의 상대적 우열이 시간 창 선택에 좌우되지 않는다는 점도 보일 수 있다.

## 9. 다중 기체 실험을 위한 부가 조사

이 절은 여러 기체가 같은 기지국 자원을 두고 경합하는 실험을 위한 것이며, 앞선 여덟 항목보다 우선순위가 낮다는 전제로 조사하였다.

### 9.1 공중 단말과 지상 단말의 자원 공유

TR 36.777이 이 문제를 정면으로 다룬다. 공중 단말의 비율이 높아지면 지상 단말의 하향 링크 처리량이 감소한다는 것이 일관된 관찰이다.
섹터당 지상 단말 15기로 이루어진 경우를 기준 사례로 두고, 공중 단말 5기와 지상 단말 10기로 이루어진 경우를 비교 사례로 둔 결과는 다음과 같다.

| 조건 | 지상 단말 성능 변화 | 출처 |
|---|---|---|
| 자원 활용률 20% | 평균 처리량 6.06% 손실, 50퍼센타일 6.45% 손실, 5퍼센타일 14.92% 손실 (기고 1) / 50퍼센타일 23.5% 손실 (기고 2) | TR 36.777 |
| 높은 트래픽 부하, 공중 단말이 무지향 안테나 사용 | 평균 처리량 49% 손실 | TR 36.777 |
| 높은 트래픽 부하, 공중 단말이 반치각 65도 지향 안테나와 정렬 사용 | 평균 처리량 손실이 26%로 제한 | TR 36.777 |

자원 분배 방식으로 표준이 언급한 기법은 두 가지이다.
하나는 공중 트래픽에 전용 무선 자원을 할당하는 방식이고, 다른 하나는 공유 자원에서 비례 공정 스케줄러로 공중 트래픽과 지상 트래픽을 함께 서비스하는 방식이다.
전용 자원 방식의 정량적 결과도 함께 제시되어 있다. 전용 물리 자원 블록 15개로 공중 C2 트래픽에 99퍼센트 신뢰도를 제공할 때, 자원 활용률은 고도 30 m에서 11.26퍼센트이고 고도 100 m에서 29.77퍼센트이다.
같은 신뢰도를 같은 자원 수로 달성하려면 고도가 높을수록 자원 활용률이 높아진다는 관찰도 함께 기술되어 있다.
자원 활용률이 30퍼센트 미만이면 30 m에서 300 m에 이르는 고도에서 99퍼센트 신뢰도를 달성할 수 있고, 활용률이 낮으면 공중 C2 패킷을 50 ms 지연 범위 안에서 높은 신뢰도로 전송할 수 있다.

**권고.** 다중 기체 실험에서 자원 분배 모형이 필요하다면 비례 공정 스케줄러를 기본으로 두는 편이 표준의 관행에 부합한다.
그리고 고도가 높아질수록 같은 신뢰도를 얻는 데 더 많은 자원이 필요하다는 관찰은, 고도를 자원 소모의 함수로 연결하는 근거가 된다.

### 9.2 공정성 지표

통신 분야에서 처리량 분배의 균등성을 재는 표준 지표는 **Jain 공정성 지수**이다.
$n$개 단말의 처리량을 $x_1, \\dots, x_n$이라 할 때 지수는 $\\left(\\sum_i x_i\\right)^2 / \\left(n \\sum_i x_i^2\\right)$로 정의되며 값은 0과 1 사이에 놓인다.
모든 단말이 같은 처리량을 얻으면 1이 되고, 소수에게 자원이 몰릴수록 0에 가까워진다.

이 지수의 원전은 R. Jain, D. Chiu, W. Hawe가 1984년에 낸 DEC Research Report TR-301이며 제목은 A Quantitative Measure of Fairness and Discrimination for Resource Allocation in Shared Computer Systems이다.
그런데 이 보고서는 기업 기술 보고서여서 DOI가 부여되어 있지 않고 arXiv에만 사본이 올라와 있다.
따라서 P-DQN 원전과 같은 이유로 인덱스에 넣지 못하였으며 `unverified.md`에 기록하였다.

**권고.** 지수 자체는 통신 분야에서 표기법이 확립되어 있으므로 정의를 본문에 직접 적고, 인용은 이 지수를 사용한 검증 가능한 문헌으로 대신하는 방법이 현실적이다.
대안 인용으로 확인한 문헌은 M. Dianati, X. Shen, S. Naik의 A new fairness index for radio resource allocation in wireless networks(IEEE WCNC 2005, DOI 10.1109/WCNC.2005.1424595)이며, 이 논문은 Jain 지수를 논한 뒤 새로운 지수를 제안한다.
다만 이 문헌은 2005년 자료여서 3년 및 5년 조건을 크게 벗어나므로, 인덱스에 넣을지는 사용자 확인이 필요하여 이번에는 넣지 않았다.

"""
txt = txt.replace(anchor8, sec8 + anchor8, 1)

# 절 번호 재정렬: 기존 8절과 9절을 10절과 11절로 민다
txt = txt.replace("## 8. 미확인 항목 종합", "## 10. 미확인 항목 종합", 1)
txt = txt.replace("## 9. 보상 가중치에 관하여", "## 11. 보상 가중치에 관하여", 1)

# --- 미확인 종합 표에 신규 항목 추가 ---
anchor10 = "| C2 데이터 링크 최소 운용 성능 표준 |"
add10 = ("| TR 36.777의 핑퐁 판정 최소 체류 시간 | 핑퐁 판정 시간 창 | 3GPP TR 36.777 원문 | "
         "원문 표가 서식 문제로 추출되지 않음. TR 36.839의 권고값 1초를 따랐을 가능성이 높으나 확인하지 못함 |\n"
         "| Jain 공정성 지수의 원전 | 공정성 지표 | DEC Research Report TR-301 (1984)의 제목과 저자 | "
         "기업 기술 보고서여서 DOI가 없고 arXiv 사본만 존재 |\n")
txt = txt.replace(anchor10, add10 + anchor10, 1)

lm, al = LockManager(), AuditLogger()
assert lm.acquire(p, AGENT)
open(p, "w").write(txt)
lm.release(p, AGENT)
al.log_action(AGENT, "MODIFY", p, "핑퐁 판정 시간 창(8절)과 다중 기체 부가 조사(9절) 추가. 7절에 항공 기체 전제 값 보강.")
print("updated", p)
