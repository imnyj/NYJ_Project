---
name: error-logging-best-practices
description: 사소한 에러 반복 방지 및 로깅 누락을 방지하기 위한 마이너 안티패턴 예방 스킬입니다.
---

# Error and Logging Best Practices

- **목적**: 시스템 실행 중 반복되는 사소한 에러를 방지하고, 에러 원인을 추적할 수 있도록 체계적인 로깅 기준을 확립하여 디버깅 용이성을 확보합니다.
- **주요 안티패턴 (해결 대상)**:
    - **에러 묵살 (Silent Failures)**: 예외 발생 시 `try-except` 블록에 `pass`만 남기거나 에러의 상세 원인(Traceback)을 생략하고 넘어가는 행위.
    - **광범위한 예외 처리 (Broad Exception Catching)**: 구체적인 예외 상황을 구분하지 않고 `except Exception:`으로 묶어 처리하여 잠재적인 다른 버그를 숨기는 행위.
    - **컨텍스트 없는 로깅 (Contextless Logging)**: 에러 발생 시 단순 'Failed' 메시지만 남기고, 어떤 함수, 어떤 변수값, 어떤 상황에서 발생했는지 맥락을 기록하지 않는 행위.
- **행동 지침 (Best Practices)**:
    - **구체적 예외 처리**: `FileNotFoundError`, `KeyError` 등 구체적인 예외 타입을 명시하여 각각의 상황에 맞는 처리 로직을 구현합니다.
    - **상세 로그 기록**: 에러 발생 시 `logging` 모듈을 활용하거나 시스템 로거(`audit_logger.py`)를 통해 발생 위치(모듈, 함수명), 입력값, 에러 메시지(Traceback)를 함께 기록해야 합니다.
    - **재시도 제한(Retry Limit) 적용**: 네트워크 요청이나 외부 리소스 접근 실패 시 반복 재시도를 할 경우 무한 루프를 막기 위한 횟수 제한(Max Retries)을 반드시 두고, 이를 초과하면 명확히 실패를 보고합니다.
    - **의도적 에러 발생 장려**: 치명적인 에러이거나 복구 불가능한 상태라면 숨기지 말고, 상위 에이전트에 에러를 던져(raise) 문제를 즉시 드러나게 합니다.
