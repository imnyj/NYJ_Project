from modules.engine.live_learning_simulator import get_live_simulator, ActionType

sim = get_live_simulator(initial_cash=1000000)
print(f"초기 상태: {sim.get_state('005930')}")

print("\n--- 매수 테스트 (삼성전자 1주) ---")
state, reward, done, info = sim.step(symbol="005930", action=ActionType.BUY, quantity=1)
print(f"Reward: {reward}")
print(f"Info: {info['trade']}")
print(f"State: {state}")

print("\n--- HOLD 테스트 ---")
state, reward, done, info = sim.step(symbol="005930", action=ActionType.HOLD, quantity=0)
print(f"Reward: {reward}")
print(f"Info: {info['trade']}")
print(f"State: {state}")

print("\n--- 매도 테스트 (삼성전자 1주) ---")
state, reward, done, info = sim.step(symbol="005930", action=ActionType.SELL, quantity=1)
print(f"Reward: {reward}")
print(f"Info: {info['trade']}")
print(f"State: {state}")
