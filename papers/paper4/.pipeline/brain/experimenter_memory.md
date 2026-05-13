# Experimenter Memory

(첫 작업 수행 시 자동으로 채워집니다)

## [2026-05-08] [Stage 1: design] scenarios 패치
- SumoNetSim 1.1.5 파라미터 채택
- urban_grid: 3x3 RSU grid (NUM_BLOCKS=3, EDGE_LENGTH=2400m, 그리드 7200m)
- V2V_COMM_RANGE=200m, RSU_COMM_RANGE=800m 분리
- DENSITY 단위: veh/km/lane (기본 20)
- seeds 5→3으로 축소 (시뮬 시간 절감)
- SA3 cbr_target: [0.4,0.5,0.6,0.7,0.8] → [0.50,0.55,0.60,0.65,0.70] (idea_spec §10.2 일치)
- SA4 hidden_width: [16,24,32,48,64] default=32 → [4,6,8,12,16] default=8 (idea_spec §10.2 일치)
- 그 외 섹션은 보존 (algorithms, metrics, modules_to_implement 변경 없음)
- total_sensitivity_runs: 90 → 54, total_main_runs: 420 → 126, grand_total: 510 → 180
