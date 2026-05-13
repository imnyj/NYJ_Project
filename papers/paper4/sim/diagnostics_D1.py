import os, sys, json, importlib
SIM_DIR = "/home/imnyj/papers/paper4/sim"
# Drop stale pyc to force recompile
pyc_path = os.path.join(SIM_DIR, "__pycache__", "etsi_cam_layer.cpython-312.pyc")
if os.path.exists(pyc_path):
    os.remove(pyc_path)
if SIM_DIR not in sys.path:
    sys.path.insert(0, SIM_DIR)
import etsi_cam_layer
importlib.reload(etsi_cam_layer)
from etsi_cam_layer import VehicleCAMState
v_default = VehicleCAMState("vDef", method="BL-B", method_params={})
v_03 = VehicleCAMState("v03", method="BL-B", method_params={"cbr_target": 0.30})
v_07 = VehicleCAMState("v07", method="BL-B", method_params={"cbr_target": 0.70})
result = {
    "default": v_default.blb_CBR_target,
    "cbr_target=0.30": v_03.blb_CBR_target,
    "cbr_target=0.70": v_07.blb_CBR_target,
}
print("RESULT:", json.dumps(result))
expected = {"default": 0.60, "cbr_target=0.30": 0.30, "cbr_target=0.70": 0.70}
verdict = "PASS" if all(abs(result[k] - expected[k]) < 1e-9 for k in expected) else "FAIL"
print("VERDICT:", verdict)
with open("/home/imnyj/papers/paper4/sim/diagnostics_D1_report.json", "w") as f:
    json.dump({"result": result, "verdict": verdict}, f)
