---
name: gpu-balancer
description: Skill to manage and distribute GPU workloads across a 4-GPU workstation.
---
# GPU Balancer Skill

- **하드웨어 인지 (Hardware Awareness)**: 본 시스템은 4개의 GPU가 장착된 고성능 원격 워크스테이션입니다. 사용자는 Tailscale 등을 통해 원격으로 접속하여 작업을 지시하고 있습니다.
- **부하 분산 (Load Balancing)**: 시뮬레이션, 딥러닝 모델 학습, 하이퍼파라미터 튜닝 등의 무거운 작업을 실행할 때, 절대로 단일 GPU(예: `cuda:0`)에만 모든 프로세스를 몰아넣지 마십시오. 이는 국지적 과열(Overheating)을 유발합니다.
- **실행 규칙 (Execution Rule)**: 
  - 병렬 시뮬레이션이나 다중 워커를 가동할 때는 `CUDA_VISIBLE_DEVICES=0,1,2,3` 환경 변수를 사용하거나, 스크립트 내부에서 `cuda:0`부터 `cuda:3`까지 자원을 균등하게 할당(Round-robin 방식 등)하여 가동하십시오.
  - 파이토치(PyTorch) 코드 작성 시 `DataParallel`이나 `DistributedDataParallel`을 적극 활용하도록 코더에게 지시하십시오.
