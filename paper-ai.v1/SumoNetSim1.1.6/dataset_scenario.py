from __future__ import annotations
import os, csv, time, math, random
from typing import Dict, List, Tuple, Any, Optional
import src.NetSim as net
os.environ.setdefault("SUMO_USE_LIBSUMO", "1")
import libsumo as sumo

BUFFER_SIZE = 1  # 즉시 flush (WSL 프로세스 비정상 종료 대비)
T_INIT = 0.0
PER_REQ = 300
netsim = None

T_INIT_OVERRIDE = 300.0  # 네트워크 warm-up 후 조기 수집 시작 (원래 ~1056s → 300s)

def start_message(sim: net.EventSimulator, vehicles: Dict[str, net.Node], rsu_list: List[net.Node], t_init) -> None:
    global T_INIT
    T_INIT = T_INIT_OVERRIDE  # override: 300s부터 수집 시작
    def print_start():
        print(f"Start to record {sim.current_time} s")
    sim.schedule_event(T_INIT_OVERRIDE, print_start)


class VehicleNode(net.Node):
    def __init__(self, node_id: str, pos: Tuple[float, float] = (0.0, 0.0)) -> None:
        super().__init__(node_id, pos=pos, comm_range=200.0)
        self.cur_rsu: Optional[net.Node] = None
        self.prev_rsu: Optional[net.Node] = None
        self.entry_time: Optional[float] = None
        self.dwell_time: Optional[float] = None
        self.next_entry_time: Optional[float] = None
        self.exit_time: Optional[float] = None
        self.req_time: Optional[float] = None
        self.report_sent: bool = False
        self.mode = None
        self.b_log = True

    def at_created(self) -> None:
        def enter_request_mode():
            self.mode = "REQUEST"
            self.sim.schedule_event(self.sim.current_time + random.uniform(0, PER_REQ), self.send_request)

        if self.sim.current_time < T_INIT:
            self.sim.schedule_event(T_INIT, enter_request_mode)
        else:
            enter_request_mode()

    def send_request(self) -> None:
        if self.mode == "REQUEST":
            self.finding_rsu(net.PacketType.REQUEST, payload={'veh_id': self.id}, size_bytes=32)
            self.entry_time = self.sim.current_time
            self.sim.schedule_event(self.sim.current_time + 1, self.send_request)

    def handle_ack(self, pkt: net.Packet) -> None:
        self.mode = "DOWNLOAD"
        rsu = pkt.src
        if self.cur_rsu is None and self.prev_rsu is None:
            if self.b_log: print(f"A {self.id} < {rsu.id:<5}\t{self.sim.current_time}\t+++++")
            self.cur_rsu = rsu
            self.req_time = self.sim.current_time
            self.sim.schedule_event(self.sim.current_time + self.sim.step, self.check_range)
            return
        if self.cur_rsu is None and self.prev_rsu is not None:
            if rsu == self.prev_rsu:
                if self.b_log: print(f"R {self.id} < {rsu.id:<5}\t{self.sim.current_time}\t--REENTRY--")
                self.cur_rsu = rsu
                self.prev_rsu = None
                self.exit_time = None
                self.next_entry_time = None
                self.report_sent = False
                self.req_time = self.sim.current_time  # 재진입: req_time 재설정
                self.sim.schedule_event(self.sim.current_time + self.sim.step, self.check_range)
                return
            if self.b_log: print(f"C {self.id} < {rsu.id:<5}\t{self.sim.current_time}\t+++++++++++++++")
            self.cur_rsu = rsu
            self.next_entry_time = self.sim.current_time - self.req_time
            if self.exit_time is not None and self.b_log:
                print(f"TRANSITION {self.id} < {self.prev_rsu.id}->{rsu.id} dt = {self.next_entry_time:.2f}")
            self.report_sent = False
            self.sim.schedule_event(self.sim.current_time + self.sim.step, self.check_range)
            return
        self.cur_rsu = rsu
        self.sim.schedule_event(self.sim.current_time + self.sim.step, self.check_range)

    def check_range(self) -> None:
        if self.sim is None or self.cur_rsu is None:
            return
        if self.cur_rsu is None:
            return
        dist = self.distance_to(self.cur_rsu)
        if dist > self.cur_rsu.comm_range:
            self.mode = "REQUEST"
            if self.prev_rsu is None:
                if self.b_log: print(f"B {self.id} from {self.cur_rsu.id}\t{self.sim.current_time}\t++++++++++")
                self.dwell_time = self.sim.current_time - self.req_time
                self.exit_time = self.sim.current_time
                self.prev_rsu = self.cur_rsu
                self.cur_rsu = None
                self.sim.schedule_event(self.sim.current_time + 1, self.send_request)
                return
            if not self.report_sent:
                if self.b_log: print(f"D {self.id} from {self.cur_rsu.id}\t{self.sim.current_time}\t++++++++++++++++++++")
                exit_time = self.sim.current_time - self.req_time
                payload = {'veh_id': self.id, 'prev_rsu': self.prev_rsu.id, 'dwell_time': self.dwell_time, 'next_entry_time': self.next_entry_time, 'exit_time': exit_time}
                self.send_direct(net.Packet(pkt_type=net.PacketType.REPORT, src=self, dst=self.cur_rsu, payload=payload, size_bytes=128))
                self.report_sent = True
                self.prev_rsu = None
                self.next_entry_time = None
            self.dwell_time = None
            self.cur_rsu = None
            self.sim.schedule_event(self.sim.current_time + 1, self.send_request)
            return
        self.sim.schedule_event(self.sim.current_time + 1, self.check_range)

class RSUNode(net.Node):
    def __init__(self, node_id: str, pos: Tuple[float, float] = (0.0, 0.0)) -> None:
        super().__init__(node_id, pos=pos, comm_range=800.0)
        self.is_rsu = True
        self.pending_records: Dict[str, Dict[str, Any]] = {}
        self.buffer: List[Dict[str, Any]] = []
        self.buffer_size = BUFFER_SIZE
        self._dwell_map: Dict[str, float] = {}
        # dwell_queue는 상위 net.Node에서 deque(maxlen=1000)으로 관리 → 재선언 제거
        self.b_log = True

    def handle_request(self, pkt: net.Packet) -> None:
        veh_node = pkt.src
        veh_id = veh_node.id
        route_rsus = net.GetRoutes(veh_id)
        if self.id in route_rsus:
            idx = route_rsus.index(self.id)
        else:
            idx = 0
        remaining = [r for r in route_rsus[idx + 1:] if r in net.rsu_dict]
        if len(remaining) < 2:
            return
        # next RSU 이웃 RSU(N/W/S) 전체 존재 여부 확인 — 외곽 RSU를 next RSU에서 배제
        _next_rsu_id = net.GetNextRSU(veh_id)
        _next_rsu_node = net.rsu_dict.get(_next_rsu_id) if _next_rsu_id else None
        if _next_rsu_node is None:
            return
        _grid = getattr(netsim, 'rsu_grid', None)
        if _grid is None:
            return  # rsu_grid 미초기화 → 이웃 RSU 확인 불가 → 배제
        if not (hasattr(_next_rsu_node, 'rsu_row') and hasattr(_next_rsu_node, 'rsu_col')):
            return  # 격자 좌표 없음 → 외곽 여부 판단 불가 → 배제
        _br, _bc = _next_rsu_node.rsu_row, _next_rsu_node.rsu_col
        if any(_grid.get((_br + dr, _bc + dc)) is None for dr, dc in [(-1, 0), (0, -1), (1, 0)]):
            return  # 외곽 RSU: N/W/S 이웃 중 하나라도 없으면 배제
        features = self._compute_features(veh_node)
        next_rsu = net.GetNextRSU(veh_id)
        record = {
            'veh_id': veh_id,
            'cur_rsu': self.id,
            'next_rsu': next_rsu,
            'features': features,
            'targets': {}
        }
        self.pending_records[veh_id] = record
        self.send_direct(net.Packet(pkt_type=net.PacketType.ACK, src=self, dst=veh_node, payload={'reply': True}, size_bytes=32))

    def handle_report(self, pkt: net.Packet) -> None:
        data = pkt.payload
        prev_rsu_id = data.get('prev_rsu')
        veh_id = data.get('veh_id')
        if not veh_id:
            return
        if self.b_log: print(f"REPORT   {self.id} < {veh_id}\t{self.sim.current_time}")
        if prev_rsu_id != self.id:
            prev_node = net.rsu_dict.get(prev_rsu_id)
            if prev_node:
                self.send_packet(net.Packet(pkt_type=net.PacketType.REPORT, src=self, dst=prev_node, payload=data, size_bytes=128))
            return
        record = self.pending_records.pop(veh_id, None)
        if not record:
            return
        dwell_time = data.get('dwell_time') or 0.0
        next_entry_time = data.get('next_entry_time')
        exit_time = data.get('exit_time')
        dwell_nxt = (exit_time - next_entry_time) if (exit_time is not None and next_entry_time is not None) else None
        record['targets'] = {
            'dwell_cur': dwell_time,
            'dwell_nxt': dwell_nxt
        }
        self.buffer.append(record)
        if self.b_log: print(f"{self.id}+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        if len(self.buffer) >= self.buffer_size:
            self.flush_buffer()

    def _ensure_output_dir(self) -> str:
        data_dir = os.path.join(os.getcwd(), "data")
        os.makedirs(data_dir, exist_ok=True)
        return data_dir

    def flush_buffer(self, force: bool = False) -> None:
        if not self.buffer:
            return
        if not force and len(self.buffer) < self.buffer_size:
            return
        data_dir = self._ensure_output_dir()
        fname = f"rsu_{self.id}.csv"
        file_path = os.path.join(data_dir, fname)
        file_exists = os.path.exists(file_path)
        with open(file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                header = ['veh_id', 'cur_rsu', 'next_rsu']
                feat_names = list(self.buffer[0]['features'].keys())
                header.extend(feat_names)
                header.extend(['dwell_cur', 'dwell_nxt'])
                writer.writerow(header)
            for rec in self.buffer:
                row = [rec['veh_id'], rec['cur_rsu'], rec['next_rsu']]
                for k in rec['features']:
                    v = rec['features'][k]
                    row.append('' if v is None else v)
                dwell_cur = rec['targets'].get('dwell_cur')
                dwell_nxt = rec['targets'].get('dwell_nxt')
                row.append('' if dwell_cur is None else dwell_cur)
                row.append('' if dwell_nxt is None else dwell_nxt)
                writer.writerow(row)
        self.buffer = []

    def reset_runtime(self) -> None:
        try:
            self.flush_buffer(force=True)
        except Exception as flush_err:
            print(f"Error flushing buffer for RSU {self.id}: {flush_err}")
        super().reset_runtime()
        self.pending_records.clear()
        self.buffer = []
        self._dwell_map.clear()

    def _compute_features(self, veh_node: net.Node) -> Dict[str, Any]:
        features: Dict[str, Any] = {}
        features['r_cov'] = self.comm_range
        next_rsu_id: Optional[str] = net.GetNextRSU(veh_node.id)
        next_rsu = net.rsu_dict.get(next_rsu_id) if next_rsu_id else None
        dir_flag = 0
        try:
            lane_id = sumo.vehicle.getLaneID(veh_node.id)
            edge_id = sumo.lane.getEdgeID(lane_id)
            to_node_id = None
            try:
                edge_obj = net._network_cache.getEdge(edge_id) if net._network_cache else None
                if edge_obj is not None:
                    to_node_id = edge_obj.getToNode().getID()
            except Exception:
                to_node_id = None
            if next_rsu and to_node_id == next_rsu_id:
                dir_flag = -1
            else:
                dir_flag = 1
        except Exception:
            dir_flag = 0
        features['dirct'] = dir_flag
        # [K] d_rsu: RSU 간 물리적 거리
        if next_rsu:
            features['d_rsu'] = math.hypot(self.pos[0] - next_rsu.pos[0], self.pos[1] - next_rsu.pos[1])
        else:
            features['d_rsu'] = float('inf')
        # [K] d_e_n: 다음 RSU 통신범위 진입까지 잔여 거리
        if next_rsu:
            dist_v_to_next = math.hypot(veh_node.pos[0] - next_rsu.pos[0], veh_node.pos[1] - next_rsu.pos[1])
            dist_v_to_cur = math.hypot(veh_node.pos[0] - self.pos[0], veh_node.pos[1] - self.pos[1])
            dist_cur_to_next = math.hypot(self.pos[0] - next_rsu.pos[0], self.pos[1] - next_rsu.pos[1])
            if dir_flag == -1:
                features['d_e_n'] = max(dist_v_to_next - next_rsu.comm_range, 0.0)
            else:
                features['d_e_n'] = max(dist_v_to_cur + dist_cur_to_next - next_rsu.comm_range, 0.0)
        else:
            features['d_e_n'] = float('inf')
        # Counts for vehicles heading to next RSU: current RSU (n_t_0) + 3 neighboring RSUs (n_t_1~3)
        if next_rsu is not None and hasattr(next_rsu, "rsu_row") and hasattr(next_rsu, "rsu_col"):
            base_r = next_rsu.rsu_row
            base_c = next_rsu.rsu_col
        else:
            base_r = None
            base_c = None
        grid = getattr(netsim, "rsu_grid", None)
        # n_t_0: vehicles at current RSU heading to next RSU
        features['n_t_0'] = self._count_vehicles_to_next(next_rsu_id)
        # n_t_1~3: vehicles at 3 neighboring RSUs of next RSU heading to next RSU
        neighbors = [(-1, 0), (0, -1), (1, 0)]  # N, W, S (3 neighbors)
        for idx, (dr, dc) in enumerate(neighbors):
            key = f"n_t_{idx + 1}"   # n_t_1, n_t_2, n_t_3
            if base_r is None or base_c is None or grid is None:
                features[key] = 0
                continue
            nb = grid.get((base_r + dr, base_c + dc))
            if nb is None:
                features[key] = 0
            else:
                features[key] = self._count_vehicles_in_range_to_next(nb, next_rsu_id)
        # [K] d_l_c: 현재 RSU 통신범위 경계까지 잔여 거리 (경계 = 중심에서 comm_range)
        _dist_v_to_cur_raw = math.hypot(veh_node.pos[0] - self.pos[0], veh_node.pos[1] - self.pos[1])
        features['d_l_c'] = max(0.0, self.comm_range - _dist_v_to_cur_raw)
        # [K] d_l_n: 다음 RSU 통신범위 이탈 경계까지 거리 (진입 후 반대편 경계)
        if next_rsu:
            dist_v_to_next = math.hypot(veh_node.pos[0] - next_rsu.pos[0], veh_node.pos[1] - next_rsu.pos[1])
            dist_v_to_cur = math.hypot(veh_node.pos[0] - self.pos[0], veh_node.pos[1] - self.pos[1])
            dist_cur_to_next = math.hypot(self.pos[0] - next_rsu.pos[0], self.pos[1] - next_rsu.pos[1])
            if dir_flag == -1:
                features['d_l_n'] = dist_v_to_next + next_rsu.comm_range
            else:
                features['d_l_n'] = dist_v_to_cur + dist_cur_to_next + next_rsu.comm_range
        else:
            features['d_l_n'] = float('inf')
        features['v_c_a'] = self.GetAvgSpeed()
        if next_rsu:
            features['v_n_a'] = next_rsu.GetAvgSpeed()
        else:
            features['v_n_a'] = 0.0
        #features['tls_c'] = self._map_signal_state(net.GetSignalState(self.id))
        #features['tls_n'] = self._map_signal_state(net.GetSignalState(next_rsu_id)) if next_rsu_id else 0
        tls_c_state = net.GetSignalState(self.id, veh_node.id, dir_flag=dir_flag)
        features['tls_c'] = self._map_signal_state(tls_c_state)
        tls_n_state = net.GetSignalState(next_rsu_id, veh_node.id, dir_flag=None) if next_rsu_id else 0.0
        features['tls_n'] = self._map_signal_state(tls_n_state)
        # Time to next signal change
        features['tlt_c'] = net.GetSignalChangeTime(self.id)
        features['tlt_n'] = net.GetSignalChangeTime(next_rsu_id) if next_rsu_id else 0.0
        # Number of vehicles within current and next RSUs
        features['n_cur'] = len(self.GetVehiclesInRange())
        features['n_nxt'] = len(next_rsu.GetVehiclesInRange()) if next_rsu else 0

        # ── 신규 변수 (SUMO 기반 Micro/Macro 지표) ──────────────────────────────

        # [K] v_ahead_avg: 현재 차량 앞 동일 차선 차량들의 평균 속도
        try:
            cur_lane_id = sumo.vehicle.getLaneID(veh_node.id)
            cur_edge_id = sumo.lane.getEdgeID(cur_lane_id)
            veh_pos = sumo.vehicle.getLanePosition(veh_node.id)
            ahead_speeds = []
            for vid in sumo.edge.getLastStepVehicleIDs(cur_edge_id):
                if vid != veh_node.id:
                    try:
                        if (sumo.vehicle.getLaneID(vid) == cur_lane_id and
                                sumo.vehicle.getLanePosition(vid) > veh_pos):
                            ahead_speeds.append(sumo.vehicle.getSpeed(vid))
                    except Exception:
                        continue
            features['v_ahead_avg'] = sum(ahead_speeds) / len(ahead_speeds) if ahead_speeds else sumo.vehicle.getSpeed(veh_node.id)
        except Exception:
            features['v_ahead_avg'] = 0.0

        # [K] dist_leader, v_leader: 선행 차량까지 거리 및 속도
        try:
            leader_info = sumo.vehicle.getLeader(veh_node.id, 200.0)
            if leader_info is not None and leader_info[0]:
                features['dist_leader'] = leader_info[1]
                features['v_leader'] = sumo.vehicle.getSpeed(leader_info[0])
            else:
                features['dist_leader'] = 200.0
                features['v_leader'] = sumo.vehicle.getSpeed(veh_node.id)
        except Exception:
            features['dist_leader'] = 200.0
            features['v_leader'] = 0.0

        # [K] est_travel_time: 현재 edge 예상 통과 시간
        try:
            cur_lane_id = sumo.vehicle.getLaneID(veh_node.id)
            cur_edge_id = sumo.lane.getEdgeID(cur_lane_id)
            features['est_travel_time'] = sumo.edge.getTraveltime(cur_edge_id)
        except Exception:
            features['est_travel_time'] = 0.0

        # [K] route_lane_changes: next RSU까지 필요 차선 변경 횟수
        try:
            best_lanes = sumo.vehicle.getBestLanes(veh_node.id)
            features['route_lane_changes'] = sum(abs(lane.bestLaneOffset) for lane in best_lanes)
        except Exception:
            features['route_lane_changes'] = 0

        # [T] q_len_cur: 현재 교차로 접근 edge 전체 정지 차량 수
        try:
            _cur_lane_id = sumo.vehicle.getLaneID(veh_node.id)
            _cur_edge_id = sumo.lane.getEdgeID(_cur_lane_id)
            features['q_len_cur'] = sumo.edge.getLastStepHaltingNumber(_cur_edge_id)
        except Exception:
            features['q_len_cur'] = 0

        # next RSU 진입 edge 특정: 차량 route에서 next RSU junction으로 직접 연결되는 edge ID를 반환
        def _get_nxt_approach_edge(veh_id: str, nxt_rsu_id: str) -> Optional[str]:
            """차량 현재 위치 이후 route에서 next RSU junction으로 직접 연결되는 edge ID를 반환."""
            try:
                route_edges = sumo.vehicle.getRoute(veh_id)
                if net._network_cache is None:
                    return None
                # 현재 차량이 있는 edge부터 탐색 (이미 지나간 edge 제외)
                try:
                    current_road = sumo.vehicle.getRoadID(veh_id)
                except Exception:
                    current_road = None
                found_current = (current_road is None)  # 현재 위치 모르면 전체 탐색
                for edge_id in route_edges:
                    if not found_current:
                        if edge_id == current_road:
                            found_current = True
                        else:
                            continue  # 현재 edge 이전은 건너뜀
                    try:
                        edge_obj = net._network_cache.getEdge(edge_id)
                        if edge_obj.getToNode().getID() == nxt_rsu_id:
                            return edge_id
                    except Exception:
                        continue
            except Exception:
                pass
            return None

        # [T] q_len_nxt: 다음 RSU 진입 edge의 정지 차량 수
        try:
            if next_rsu is not None:
                _nxt_approach_edge = _get_nxt_approach_edge(veh_node.id, next_rsu.id)
                if _nxt_approach_edge:
                    features['q_len_nxt'] = sumo.edge.getLastStepHaltingNumber(_nxt_approach_edge)
                else:
                    features['q_len_nxt'] = 0
            else:
                features['q_len_nxt'] = 0
        except Exception:
            features['q_len_nxt'] = 0

        # [S] n_ahead_cur: 현재 차량 앞 동일 차선 차량 수
        try:
            _cur_lane_id = sumo.vehicle.getLaneID(veh_node.id)
            _cur_edge_id = sumo.lane.getEdgeID(_cur_lane_id)
            _veh_pos = sumo.vehicle.getLanePosition(veh_node.id)
            _n_ahead_cur = 0
            for vid in sumo.edge.getLastStepVehicleIDs(_cur_edge_id):
                if vid == veh_node.id:
                    continue
                try:
                    if (sumo.vehicle.getLaneID(vid) == _cur_lane_id and
                            sumo.vehicle.getLanePosition(vid) > _veh_pos):
                        _n_ahead_cur += 1
                except Exception:
                    continue
            features['n_ahead_cur'] = _n_ahead_cur
        except Exception:
            features['n_ahead_cur'] = 0

        # [S] n_ahead_nxt: 요청차 전방 동일 차선에서 next RSU로 향하는 차량 수
        try:
            _cur_lane_id = sumo.vehicle.getLaneID(veh_node.id)
            _cur_edge_id = sumo.lane.getEdgeID(_cur_lane_id)
            _veh_pos = sumo.vehicle.getLanePosition(veh_node.id)
            _n_ahead_nxt = 0
            if next_rsu_id:
                for vid in sumo.edge.getLastStepVehicleIDs(_cur_edge_id):
                    if vid == veh_node.id:
                        continue
                    try:
                        if (sumo.vehicle.getLaneID(vid) == _cur_lane_id and
                                sumo.vehicle.getLanePosition(vid) > _veh_pos and
                                net.GetNextRSU(vid) == next_rsu_id):
                            _n_ahead_nxt += 1
                    except Exception:
                        continue
            features['n_ahead_nxt'] = _n_ahead_nxt
        except Exception:
            features['n_ahead_nxt'] = 0

        # [S] n_merge_nxt: next RSU로 합류 예정인 인접 RSU 차량 수 (n_t_1+n_t_2+n_t_3)
        try:
            features['n_merge_nxt'] = (
                features.get('n_t_1', 0) +
                features.get('n_t_2', 0) +
                features.get('n_t_3', 0)
            )
        except Exception:
            features['n_merge_nxt'] = 0

        # [S] occ_cur: 현재 차량 lane 점유율
        try:
            cur_lane_id = sumo.vehicle.getLaneID(veh_node.id)
            features['occ_cur'] = sumo.lane.getLastStepOccupancy(cur_lane_id)
        except Exception:
            features['occ_cur'] = 0.0

        # [S] occ_nxt: 다음 RSU 진입 edge의 차선 평균 점유율
        try:
            if next_rsu is not None:
                _nxt_approach_edge = _get_nxt_approach_edge(veh_node.id, next_rsu.id)
                if _nxt_approach_edge:
                    _lane_count = sumo.edge.getLaneNumber(_nxt_approach_edge)
                    if _lane_count > 0:
                        _occ_sum = sum(
                            sumo.lane.getLastStepOccupancy(f"{_nxt_approach_edge}_{i}")
                            for i in range(_lane_count)
                        )
                        features['occ_nxt'] = _occ_sum / _lane_count
                    else:
                        features['occ_nxt'] = 0.0
                else:
                    features['occ_nxt'] = 0.0
            else:
                features['occ_nxt'] = 0.0
        except Exception:
            features['occ_nxt'] = 0.0

        return features

    def _map_signal_state(self, state: float) -> int:
        if state == 1.0: return -1
        if state == 2.0: return 0
        if state == 3.0: return 1
        return -2

    def _count_vehicles_to_next(self, next_rsu_id: Optional[str]) -> int:
        if not next_rsu_id:
            return 0
        count = 0
        for vid in self.GetVehiclesInRange():
            try:
                nxt = net.GetNextRSU(vid)
                if nxt == next_rsu_id:
                    count += 1
            except Exception:
                continue
        return count

    def _count_vehicles_in_range_to_next(self, rsu_node: net.Node, next_rsu_id: Optional[str]) -> int:
        if not next_rsu_id:
            return 0
        count = 0
        for vid in rsu_node.GetVehiclesInRange():
            try:
                nxt = net.GetNextRSU(vid)
                if nxt == next_rsu_id:
                    count += 1
            except Exception:
                continue
        return count
    
    def update_dwell(self, current_time: float) -> None:
        current_in_range = set(self.GetVehiclesInRange())
        for vid in current_in_range:
            if vid not in self._dwell_map:
                self._dwell_map[vid] = current_time
        for vid in list(self._dwell_map.keys()):
            if vid not in current_in_range:
                start_time = self._dwell_map.pop(vid)
                dwell_time = current_time - start_time
                self.dwell_queue.append(dwell_time)

###################################### Simulation Entry ######################################

# 진행 상황 파일 (watchdog-runner.py 가 읽어 진행바 갱신)
_PROGRESS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".sim_progress")

if __name__ == "__main__":
    # 진행 파일 초기화
    try:
        with open(_PROGRESS_FILE, 'w') as _f: _f.write("0")
    except Exception: pass

    net.InitSumoNetSim(VehicleClass=VehicleNode, RSUClass=RSUNode, mode = 1)
    netsim = net.SumoNetSim(VehicleClass=VehicleNode, RSUClass=RSUNode, start_message_fn=start_message)

    # 10초 간격으로 현재 step을 파일에 기록하는 이벤트 등록
    def _write_sim_progress():
        try:
            with open(_PROGRESS_FILE, 'w') as _f:
                _f.write(str(int(netsim.sim.current_time)))
        except Exception:
            pass
        netsim.sim.schedule_event(netsim.sim.current_time + 10, _write_sim_progress)

    netsim.sim.schedule_event(10.0, _write_sim_progress)
    netsim.run()

    # 완료 기록
    try:
        with open(_PROGRESS_FILE, 'w') as _f: _f.write("3600")
    except Exception: pass
    # Force-flush all RSU buffers after simulation ends
    for rsu in net.rsu_list:
        if isinstance(rsu, RSUNode):
            try:
                rsu.flush_buffer(force=True)
                print(f"Flushed buffer for RSU {rsu.id}: {len(rsu.buffer)} remaining")
            except Exception as e:
                print(f"Error flushing RSU {rsu.id}: {e}")
    print("Dataset collection complete.")