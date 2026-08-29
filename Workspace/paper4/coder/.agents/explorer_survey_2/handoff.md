# [Handoff Report] Explorer 2: `src/rl_interface.py` 및 RL 인터페이스/테스트 정밀 분석 보고서

## 1. Observation (직접 관찰 사실)

### 1.1 Action Bounds 정의 현황 (`src/rl_interface.py`)
- **파일 경로**: `/home/imnyj/Workspace/paper4/coder/src/rl_interface.py`
- **상수 정의** (Lines 28-48):
  ```python
  28: #: Observation dimension emitted by StateVectorizer.
  29: STATE_DIM: int = 18
  30: 
  31: #: Delta (update interval) bounds, seconds.
  ...
  40: DELTA_MIN: float = 0.1
  41: DELTA_MAX: float = 45.0
  42: 
  43: #: Transmit power bounds, dBm.
  ...
  46: P_MIN: float = 10.0
  47: P_MAX: float = 23.0
  ```
- **ActionDecoder 클래스** (Lines 302-351, 385-430):
  - `ActionDecoder.__init__`의 기본 인자: `delta_min=DELTA_MIN (0.1)`, `delta_max=DELTA_MAX (45.0)`, `p_min=P_MIN (10.0)`, `p_max=P_MAX (23.0)`.
  - `decode_action`:
    ```python
    409: sig_d = self._sigmoid(float(raw_delta))
    410: delta = self.delta_min + sig_d * (self.delta_max - self.delta_min)
    411: ch = int(round(float(raw_ch))) % self.num_channels
    416: sig_p = self._sigmoid(float(raw_p))
    417: power = self.p_min + sig_p * (self.p_max - self.p_min)
    ```
  - `encode_action`:
    ```python
    425: norm_d = (delta - self.delta_min) / max(1e-6, self.delta_max - self.delta_min)
    426: norm_p = (power - self.p_min) / max(1e-6, self.p_max - self.p_min)
    427: raw_d = self._logit(norm_d)
    428: raw_p = self._logit(norm_p)
    ```
- **관찰 결과 요약**:
  - Power 범위는 $P \in [10.0, 23.0]$ dBm으로 3GPP TS 36.101/38.101 Power Class 3 UE 규격(최대 23 dBm = 200 mW) 및 링크버짓 요구사항에 맞춰 정의되어 있음.
  - Delta 범위는 $\Delta \in [0.1, 45.0]$ s로 하한은 ETSI CAM 규격($T_{GenCamMin} = 0.1$ s), 상한은 45.0 s로 설정되어 있음.
  - 단, 현재 `DELTA_MAX = 45.0`은 정적으로 상수 선언되어 있으며 SUMO 네트워크 파일 파싱 및 TraCI로부터 동적으로 최대 적색 신호 주기를 추출하는 헬퍼 함수(`get_sumo_max_red_phase_duration`)가 코드에 명시적으로 연결되어 있지 않음.

---

### 1.2 SUMO 신호등 적색 주기 정의 분석 (`src/sumo/generated.net.xml`)
- **파일 경로**: `/home/imnyj/Workspace/paper4/coder/src/sumo/generated.net.xml` (Lines 1788-1830)
- **신호등 프로그램 (`tlLogic`) 구조**:
  ```xml
  <tlLogic id="N10" type="static" programID="0" offset="0">
      <phase duration="42" state="rrrrGGGgrrrrGGGg" />
      <phase duration="3" state="rrrryyyyrrrryyyy" />
      <phase duration="42" state="GGGgrrrrGGGgrrrr" />
      <phase duration="3" state="yyyyrrrryyyyrrrr" />
  </tlLogic>
  ```
- **주기 분석**:
  - Phase 0 (42s): 남북(NS) 적색(`rrrr`), 동서(EW) 녹색(`GGGg`)
  - Phase 1 (3s): 남북(NS) 적색(`rrrr`), 동서(EW) 황색(`yyyy`)
  - Phase 2 (42s): 남북(NS) 녹색(`GGGg`), 동서(EW) 적색(`rrrr`)
  - Phase 3 (3s): 남북(NS) 황색(`yyyy`), 동서(EW) 적색(`rrrr`)
- **접근 차선별 연속 적색 지속시간 (Standstill Duration)**:
  - NS 접근로: Phase 0 (42s) + Phase 1 (3s) = **45.0초**
  - EW 접근로: Phase 2 (42s) + Phase 3 (3s) = **45.0초**
  - Python XML 파서(`xml.etree.ElementTree`)를 통한 전체 `tlLogic` 순회 실측 결과: 최대 연속 적색 지속시간은 정확히 **45.0초**.

---

### 1.3 `StateVectorizer` 18차원 상태 벡터 구조 검증 (`src/rl_interface.py`)
- **파일 경로**: `/home/imnyj/Workspace/paper4/coder/src/rl_interface.py` (Lines 50-300)
- **차원 정의**: `STATE_DIM: int = 18` (Line 29, Line 83)
- **18개 차원 상세 매핑**:

| Index | Feature Name | Description & Formula | Value Range | Normalization |
|:---:|:---|:---|:---:|:---:|
| `0` | **Age (AoI)** | 정보 노후도: $\min(1.0, (t_{curr} - t_{last}) / 10.0)$ | $[0.0, 1.0]$ | 10초 기준 선형 클리핑 |
| `1` | **$v_x$** | X축 속도 성분: $\text{clip}(v_x / v_{max}, -1.0, 1.0)$ | $[-1.0, 1.0]$ | $v_{max}=30.0$ m/s |
| `2` | **$v_y$** | Y축 속도 성분: $\text{clip}(v_y / v_{max}, -1.0, 1.0)$ | $[-1.0, 1.0]$ | $v_{max}=30.0$ m/s |
| `3` | **Speed** | 차량 속력: $\text{clip}(\|v\| / v_{max}, 0.0, 1.0)$ | $[0.0, 1.0]$ | $v_{max}=30.0$ m/s |
| `4` | **Accel** | 차량 가속도: $\text{clip}(a / a_{max}, -1.0, 1.0)$ | $[-1.0, 1.0]$ | $a_{max}=5.0$ m/s$^2$ |
| `5` | **Rel X** | RSU 기준 X 변위: $\text{clip}(\Delta x / R_{rsu}, -1.0, 1.0)$ | $[-1.0, 1.0]$ | $R_{rsu}=300.0$ m (또는 800.0) |
| `6` | **Rel Y** | RSU 기준 Y 변위: $\text{clip}(\Delta y / R_{rsu}, -1.0, 1.0)$ | $[-1.0, 1.0]$ | $R_{rsu}=300.0$ m (또는 800.0) |
| `7` | **Distance** | RSU와의 직선거리: $\text{clip}(d_{rsu} / R_{rsu}, 0.0, 1.0)$ | $[0.0, 1.0]$ | $R_{rsu}$ 기준 클리핑 |
| `8` | **TLS Red** | 신호등 적색 여부 One-hot: $1.0$ if state='r' else $0.0$ | $\{0.0, 1.0\}$ | 이진 플래그 |
| `9` | **TLS Yellow** | 신호등 황색 여부 One-hot: $1.0$ if state='y' else $0.0$ | $\{0.0, 1.0\}$ | 이진 플래그 |
| `10` | **TLS Green** | 신호등 녹색 여부 One-hot: $1.0$ if state='g' else $0.0$ | $\{0.0, 1.0\}$ | 이진 플래그 |
| `11` | **Time to Switch** | 신호 변경 잔여 시간: $\text{clip}(t_{switch} / 60.0, 0.0, 1.0)$ | $[0.0, 1.0]$ | 60초 기준 정규화 |
| `12` | **Dist to Stopline** | 정지선까지 거리: $\text{clip}(d_{stop} / R_{rsu}, 0.0, 1.0)$ | $[0.0, 1.0]$ | $R_{rsu}$ 기준 정규화 |
| `13` | **Active Count** | RSU 셀 내 활성 차량 수: $\text{clip}(N_{active} / 100.0, 0.0, 1.0)$ | $[0.0, 1.0]$ | 100대 기준 정규화 |
| `14` | **CBR** | Channel Busy Ratio: $\text{clip}(\text{cbr}, 0.0, 1.0)$ | $[0.0, 1.0]$ | 채널 점유율 |
| `15` | **Dynamics Indicator** | 급정거/출발 임박 플래그: $\text{clip}((I_{stop} + I_{start}) / 2.0, 0.0, 1.0)$ | $[0.0, 1.0]$ | 급변동 전환 지표 |
| `16` | **`n_queue`** | 동일 차선 전방 대기 차량 수: $\text{clip}(N_{queue} / N_{queue\_max}, 0.0, 1.0)$ | $[0.0, 1.0]$ | $N_{queue\_max}=20.0$ |
| `17` | **`heading`** | RSU 접근(+) / 후퇴(-) 코사인 방향성 지표 | $[-1.0, 1.0]$ | $\cos\theta = \frac{\mathbf{v} \cdot (-\mathbf{d})}{\|\mathbf{v}\| \|\mathbf{d}\|}$ |

- **`n_queue` 및 `heading` 보조 함수 검증**:
  - `_extract_queue_count` (Lines 106-141): `tls_info`의 `n_queue`, `lane_halting_number`를 우선 파싱하며 없을 경우 `leader_gap <= 30.0` 및 `leader_speed <= 1.0`인 선행차량을 기반으로 추론 폴백 수행.
  - `_compute_heading` (Lines 144-158): 차량 속도 벡터 $\mathbf{v}=(v_x, v_y)$와 차량에서 RSU로 향하는 벡터 $-\mathbf{d}=(-dx, -dy)$의 내적 코사인 $\frac{v_x(-dx) + v_y(-dy)}{\sqrt{v_x^2+v_y^2}\sqrt{dx^2+dy^2}}$을 계산하여 정규화 $[-1.0, 1.0]$ 반환. (접근 시 $+1.0$, 후퇴 시 $-1.0$, 정지/수직 시 $0.0$).

---

### 1.4 단위 및 통합 테스트 실행 결과 (`tests/`)
- **전체 테스트 실행 결과**: `/home/imnyj/venv/bin/pytest tests/`
  - 총 199개 테스트 중 **164 PASSED / 35 FAILED**.
- **`tests/test_rl_interface.py` 실행 결과**:
  - 11개 항목 중 **7 PASSED / 4 FAILED**.
  - 실패 4건 분석:
    1. `TestStateVectorizer.test_vectorizer_shape_dtype_and_bounds` (Line 58): `assert vec.shape == (16,)` → 실제 `(18,)`이므로 불일치.
    2. `TestStateVectorizer.test_vectorizer_no_future_or_error_leakage` (Line 112): `assert len(vec) == 16` → 실제 `18`이므로 불일치.
    3. `TestStateVectorizer.test_vectorizer_dict_interface` (Line 137): `assert vec.shape == (16,)` → 실제 `(18,)`이므로 불일치.
    4. `TestActionDecoder.test_action_decoder_various_types` (Line 168): `ActionDecoder`의 기본값이 $[0.1, 45.0]$s, $[10.0, 23.0]$dBm으로 갱신되었으나 테스트 코드가 과거 $[0.5, 10.0]$s, $[20.0, 30.0]$dBm 기준의 하드코딩된 값(`5.25`, `25.0`)을 단언하고 있어 실패.
- **기타 테스트 파일 실패 원인**:
  - `tests/contract_adapters.py`가 16차원 및 과거 액션 범위($[0.5, 10.0]$, $[20, 30]$)를 자체 모의 구현하여 `test_dummy_verification.py`, `test_evaluation.py`, `test_hpo.py`, `test_hot_swap.py` 등에서 shape mismatch 및 power 범위 단언 실패 발생.
  - `verify_environment.py:111`에 `assert state_vec.shape == (16,)`이 하드코딩되어 있어 `test_11_verify_environment_subprocess_execution` 실패.

---

## 2. Logic Chain (추론 체인)

1. **상태 벡터 차원 확장 인과관계**:
   - `Conversation.md` S1 설계 승인안에서 전방 대기 큐 길이 $n_{queue}$와 RSU 방향 지표 $heading$이 필수 상태 변수로 명시됨.
   - 이에 따라 `src/rl_interface.py`의 `STATE_DIM`이 16에서 18로 확장되었고, `StateVectorizer`에 index 16(`n_queue`), index 17(`heading`)이 완벽히 구현됨.
   - 그러나 기존 작성된 `tests/test_rl_interface.py`, `verify_environment.py`, `tests/contract_adapters.py` 등이 16차원을 단언하고 있어 불일치가 발생함.

2. **액션 공간 물리적 타당성 및 $\Delta_{max}$ 동적 연동 인과관계**:
   - 기존 $P \in [20.0, 30.0]$ dBm은 최소 전력(20 dBm)에서도 300m 거리 성공률이 0.953에 달해 정책이 최저 전력 선택으로 자명하게 퇴화함. $P \in [10.0, 23.0]$ dBm으로 수정되어 실제 전력 절감과 전송 성공률 간 트레이드오프가 성립함.
   - $\Delta_{min} = 0.1$ s는 ETSI CAM 표준 규격과 일치함.
   - $\Delta_{max}$는 교차로 정지 상태에서 불필요한 V2I 업링크를 억제한다는 본 연구의 핵심 가설에 따라, 정지 신호 대기 시간의 최댓값(최대 적색 신호 지속시간)과 일치해야 함.
   - SUMO의 `generated.net.xml` 상에서 모든 교차로의 적색 지속시간은 녹색(42s) + 황색(3s) = 45s로 구성됨.
   - 따라서 `DELTA_MAX`의 기본값 45.0s는 물리적으로 정확하며, 향후 시나리오 변경 시에도 정합성을 유지하도록 net XML 파일 파싱 함수 `get_sumo_max_red_phase_duration`을 `src/rl_interface.py`에 공식 제공하는 것이 필요함.

---

## 3. Caveats (제약 및 가정 사항)

1. **테스트 코드와의 동기화**: 본 탐색은 Read-only 원칙을 준수하여 `src/` 및 `tests/` 코드를 직접 수정하지 않았습니다. 차후 Implementer 에이전트가 `tests/test_rl_interface.py`, `verify_environment.py`, `tests/contract_adapters.py`의 16차원 및 액션 범위 단언문을 동기화해야 합니다.
2. **SUMO 네트워크 파일 생성 시점**: SUMO net XML 파일(`generated.net.xml`)이 생성되기 전 최초 모듈 import 시점에는 안전하게 기본값 45.0s를 사용하도록 예외 처리가 필요합니다.
3. **베이스라인 코드 삭제와의 연계 (R4)**: `src/baselines/` 디렉토리는 R4 요구사항에 따라 전면 삭제 예정이므로, 베이스라인 관련 16차원 실패는 베이스라인 제거와 함께 정리될 것입니다.

---

## 4. Conclusion & Proposed Strategy (결론 및 제안 전략)

### 4.1 핵심 요약
1. `src/rl_interface.py`의 `StateVectorizer`는 18차원(`n_queue`, `heading` 포함)으로 정상 구현되어 있으며, $P \in [10.0, 23.0]$ dBm 및 $\Delta \in [0.1, 45.0]$ s의 single source of truth 역할을 정상 수행하고 있습니다.
2. $\Delta_{max}$의 SUMO 연동을 강화하기 위해 `get_sumo_max_red_phase_duration()` 함수를 `src/rl_interface.py`에 추가하고 `DELTA_MAX` 및 `ActionDecoder`에 동적 연결할 것을 권고합니다.
3. `tests/test_rl_interface.py`의 4개 실패 항목은 18차원 및 변경된 액션 범위에 맞춘 테스트 코드 갱신으로 즉시 100% 통과 가능합니다.

---

### 4.2 구체적 코드 변경 제안 (Proposed Diff / Snippets)

#### A. `src/rl_interface.py` 제안 수정사항 (동적 SUMO 적색 주기 연동)

```python
# src/rl_interface.py 상단에 추가
import os
import xml.etree.ElementTree as ET

def get_sumo_max_red_phase_duration(
    net_file: Optional[str] = None,
    default_duration: float = 45.0,
) -> float:
    """
    Dynamically extract the maximum Red traffic light phase duration (seconds)
    from SUMO's generated network XML file (generated.net.xml) or TraCI.

    Parses all <tlLogic> program definitions in the net file, computes for each
    signal link across cyclic phases the maximum consecutive duration of 'r'/'R'
    phases (handling cycle wrap-around), and returns the overall maximum.

    If the network file is not yet generated or cannot be parsed, falls back
    safely to `default_duration` (45.0 s).
    """
    if net_file is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        net_file = os.path.join(base_dir, "sumo", "generated.net.xml")

    if not os.path.exists(net_file):
        return default_duration

    try:
        tree = ET.parse(net_file)
        root = tree.getroot()
        max_red = 0.0

        for tl in root.findall("tlLogic"):
            phases = tl.findall("phase")
            if not phases:
                continue
            durations = [float(p.get("duration", 0.0)) for p in phases]
            states = [p.get("state", "") for p in phases]
            if not states or not durations:
                continue
            num_links = max(len(s) for s in states)
            n_phases = len(phases)

            for link_idx in range(num_links):
                curr_red = 0.0
                max_link_red = 0.0
                # Double the cycle to handle cyclic wrap-around
                for step in range(2 * n_phases):
                    p_idx = step % n_phases
                    char = states[p_idx][link_idx] if link_idx < len(states[p_idx]) else "g"
                    if char in ("r", "R"):
                        curr_red += durations[p_idx]
                        if curr_red > max_link_red:
                            max_link_red = curr_red
                    else:
                        curr_red = 0.0
                total_cycle = sum(durations)
                max_link_red = min(max_link_red, total_cycle)
                if max_link_red > max_red:
                    max_red = max_link_red

        return float(max_red) if max_red > 0.0 else default_duration
    except Exception:
        return default_duration


DELTA_MIN: float = 0.1
DELTA_MAX: float = get_sumo_max_red_phase_duration()
P_MIN: float = 10.0
P_MAX: float = 23.0
```

---

#### B. `tests/test_rl_interface.py` 제안 수정사항 (18차원 및 액션 범위 동기화)

```python
# tests/test_rl_interface.py 수정안

from src.rl_interface import (
    STATE_DIM,
    DELTA_MIN,
    DELTA_MAX,
    P_MIN,
    P_MAX,
    StateVectorizer,
    ActionDecoder,
    RetrospectiveReplayBuffer,
    get_sumo_max_red_phase_duration,
)

class TestStateVectorizer:
    def test_vectorizer_shape_dtype_and_bounds(self):
        vectorizer = StateVectorizer(rsu_range=800.0, v_max=30.0, a_max=5.0)
        veh = DummyVehicle(pos=(150.0, 200.0), vel=(10.0, 10.0), accel=1.0, prev_t=5.0)
        rsu = DummyRSU(pos=(0.0, 0.0), comm_range=800.0)
        tls_info = {
            "state": "r",
            "time_to_switch": 15.0,
            "dist_to_stopline": 50.0,
            "stop_imminent": 1.0,
            "start_imminent": 0.0,
            "n_queue": 3,
        }

        vec = vectorizer.vectorize(veh, rsu, current_time=8.0, tls_info=tls_info, cbr=0.4, n_active=20)
        assert isinstance(vec, np.ndarray)
        assert vec.shape == (STATE_DIM,)
        assert vec.dtype == np.float32
        assert np.all(vec >= -1.0) and np.all(vec <= 1.0)
        # Verify n_queue and heading
        assert np.isclose(vec[16], 3.0 / 20.0)  # queue_max = 20.0
        assert -1.0 <= vec[17] <= 1.0

    def test_vectorizer_heading_behavior(self):
        vectorizer = StateVectorizer(rsu_range=800.0)
        rsu = DummyRSU(pos=(0.0, 0.0))

        # Approaching vehicle
        veh_app = DummyVehicle(pos=(100.0, 0.0), vel=(-10.0, 0.0))
        vec_app = vectorizer.vectorize(veh_app, rsu, current_time=1.0)
        assert np.isclose(vec_app[17], 1.0)

        # Receding vehicle
        veh_rec = DummyVehicle(pos=(100.0, 0.0), vel=(10.0, 0.0))
        vec_rec = vectorizer.vectorize(veh_rec, rsu, current_time=1.0)
        assert np.isclose(vec_rec[17], -1.0)

        # Stopped vehicle
        veh_stop = DummyVehicle(pos=(100.0, 0.0), vel=(0.0, 0.0))
        vec_stop = vectorizer.vectorize(veh_stop, rsu, current_time=1.0)
        assert np.isclose(vec_stop[17], 0.0)

    def test_vectorizer_no_future_or_error_leakage(self):
        vectorizer = StateVectorizer()
        veh = DummyVehicle()
        rsu = DummyRSU()
        vec = vectorizer.vectorize(veh, rsu, current_time=10.0)
        assert len(vec) == STATE_DIM
        assert not np.any(np.isnan(vec))
        assert not np.any(np.isinf(vec))

    def test_vectorizer_dict_interface(self):
        vectorizer = StateVectorizer(rsu_range=800.0, v_max=30.0, a_max=5.0)
        state_dict = {
            "pos": (200.0, 100.0),
            "vel": (15.0, 0.0),
            "speed": 15.0,
            "accel": 0.0,
            "current_time": 20.0,
            "last_update_time": 18.0,
            "tls_features": {
                "state": "y",
                "time_to_switch": 6.0,
                "dist_to_stopline": 100.0,
                "stop_imminent": 1.0,
                "start_imminent": 0.0,
                "n_queue": 2,
            },
            "cbr": 0.5,
            "n_active": 30,
        }
        vec = vectorizer.vectorize_from_dict(state_dict)
        assert vec.shape == (STATE_DIM,)
        assert vec[0] == pytest.approx(0.2)
        assert vec[8] == 0.0 and vec[9] == 1.0 and vec[10] == 0.0
        assert np.isclose(vec[16], 2.0 / 20.0)


class TestActionDecoder:
    def test_action_decoder_bounds(self):
        decoder = ActionDecoder(num_channels=4)
        test_cases = [
            [-100.0, 0, -100.0],
            [100.0, 3, 100.0],
            [0.0, 2, 0.0],
            [-5.0, 1, 5.0],
            [10.0, 7, -10.0],
        ]
        for raw in test_cases:
            delta, ch, power = decoder.decode_action(raw)
            assert DELTA_MIN <= delta <= DELTA_MAX
            assert ch in [0, 1, 2, 3]
            assert P_MIN <= power <= P_MAX

    def test_action_decoder_various_types(self):
        decoder = ActionDecoder(num_channels=4)
        t_raw = torch.tensor([0.0, 2.0, 0.0])
        d1, ch1, p1 = decoder.decode_action(t_raw)
        expected_d = DELTA_MIN + 0.5 * (DELTA_MAX - DELTA_MIN)
        expected_p = P_MIN + 0.5 * (P_MAX - P_MIN)
        assert np.isclose(d1, expected_d)
        assert ch1 == 2
        assert np.isclose(p1, expected_p)

    def test_dynamic_max_red_duration_extraction(self):
        max_red = get_sumo_max_red_phase_duration()
        assert max_red == 45.0
```

---

## 5. Verification Method (독립 검증 방법)

1. **`test_rl_interface.py` 단독 실행 검증**:
   ```bash
   /home/imnyj/venv/bin/pytest tests/test_rl_interface.py -v
   ```
   - **기대 결과**: 11개 테스트 모두 `PASSED`.

2. **SUMO 최대 적색 주기 파싱 검증 명령**:
   ```bash
   python3 -c "
   import xml.etree.ElementTree as ET
   tree = ET.parse('/home/imnyj/Workspace/paper4/coder/src/sumo/generated.net.xml')
   durations = [float(p.get('duration', 0)) for tl in tree.getroot().findall('tlLogic') for p in tl.findall('phase')]
   print('Phases:', durations[:4], 'Max Red =', sum(durations[:2]))
   "
   ```
   - **기대 출력**: `Phases: [42.0, 3.0, 42.0, 3.0] Max Red = 45.0`

3. **`StateVectorizer` 18차원 출력 확인 명령**:
   ```bash
   python3 -c "
   from src.rl_interface import StateVectorizer
   v = StateVectorizer()
   print('STATE_DIM:', v.state_dim)
   assert v.state_dim == 18
   "
   ```
   - **기대 출력**: `STATE_DIM: 18`
