(1) UAM 시뮬레이션 환경(environment), 모델(models), 메인 시뮬레이션(main_sim) 구현 완료.
(2) 서브에이전트 병렬 생성(env_builder, vehicle_comm_builder, sim_manager)을 통한 효율적 구조화 성공.
(3) 루트 경로 디렉토리 청결 유지를 위해 생성된 시뮬레이션 로그들을 etc/logs/로 이동함.
- Developed proactive handover algorithm minimizing ping-pong & latency using Optuna parameter tuning in `handover_optimization.py`.
- Fixed object mismatch during initial execution: converted `environment.Building` to `models.Building` to allow `intersects_segment_3d`.
- Completed parameter tuning with Optuna, storing temporary scripts and logs in `etc/` and results in `logs/` to maintain workspace cleanliness.
