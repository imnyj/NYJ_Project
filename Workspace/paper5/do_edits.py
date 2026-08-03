import sys
import os
import json
import re

sys.path.append(os.path.abspath("/home/imnyj/Command/core"))
from lock_manager import LockManager
from audit_logger import AuditLogger

lm = LockManager()
logger = AuditLogger()
agent_id = "agent_editor"

def edit_file(filepath, callback, description):
    if lm.acquire(filepath, agent_id, timeout=10):
        try:
            with open(filepath, "r") as f:
                content = f.read()
            new_content = callback(content)
            with open(filepath, "w") as f:
                f.write(new_content)
            logger.log_action(agent_id, "MODIFY", filepath, description)
            print(f"Successfully modified {filepath}")
        finally:
            lm.release(filepath, agent_id)
    else:
        print(f"Failed to acquire lock for {filepath}")

def mod_env(content):
    if "from config_loader import load_config" not in content:
        content = content.replace("import math\n", "import math\nfrom config_loader import load_config\n")
        
    old_init = """    def __init__(
        self,
        width: float = 20000.0,
        height: float = 20000.0,
        first_road_offset: float = 1500.0,
        road_interval: float = 3000.0,
        road_width: float = 30.0,"""
    new_init = """    def __init__(
        self,
        width: Optional[float] = None,
        height: Optional[float] = None,
        first_road_offset: Optional[float] = None,
        road_interval: Optional[float] = None,
        road_width: Optional[float] = None,"""
    
    old_body = """        self.width = width
        self.height = height
        self.first_road_offset = first_road_offset
        self.road_interval = road_interval
        self.road_width = road_width"""
    new_body = """        cfg = load_config().get("ENVIRONMENT", {})
        self.width = width if width is not None else cfg.get("WIDTH", 20000.0)
        self.height = height if height is not None else cfg.get("HEIGHT", 20000.0)
        self.first_road_offset = first_road_offset if first_road_offset is not None else cfg.get("FIRST_ROAD_OFFSET", 1500.0)
        self.road_interval = road_interval if road_interval is not None else cfg.get("ROAD_INTERVAL", 3000.0)
        self.road_width = road_width if road_width is not None else cfg.get("ROAD_WIDTH", 30.0)"""
    
    content = content.replace(old_init, new_init).replace(old_body, new_body)
    
    old_rsu = """class RSU:
    \"\"\"Roadside Unit (RSU) at an intersection providing V2X/U2X wireless communications.\"\"\"
    id: str
    position: Tuple[float, float, float]  # (x, y, z) in meters
    coverage_radius: float = 500.0        # meters
    tx_power_dbm: float = 30.0           # dBm
    frequency_ghz: float = 5.9           # GHz (C-V2X / 802.11p)
    bandwidth_mhz: float = 20.0          # MHz
    max_data_rate_mbps: float = 100.0    # Mbps"""
    new_rsu = """class RSU:
    \"\"\"Roadside Unit (RSU) at an intersection providing V2X/U2X wireless communications.\"\"\"
    id: str
    position: Tuple[float, float, float]  # (x, y, z) in meters
    coverage_radius: float = field(default_factory=lambda: load_config().get("RSU", {}).get("COVERAGE_RADIUS", 500.0))
    tx_power_dbm: float = field(default_factory=lambda: load_config().get("RSU", {}).get("TX_POWER_DBM", 30.0))
    frequency_ghz: float = field(default_factory=lambda: load_config().get("RSU", {}).get("FREQUENCY_GHZ", 5.9))
    bandwidth_mhz: float = field(default_factory=lambda: load_config().get("RSU", {}).get("BANDWIDTH_MHZ", 20.0))
    max_data_rate_mbps: float = field(default_factory=lambda: load_config().get("RSU", {}).get("MAX_DATA_RATE_MBPS", 100.0))"""
    
    content = content.replace(old_rsu, new_rsu)
    
    old_cell = """class CellularBaseStation:
    \"\"\"5G Macro Cellular Base Station.\"\"\"
    id: str
    position: Tuple[float, float, float]  # (x, y, z) in meters
    coverage_radius: float = 3500.0       # meters
    tx_power_dbm: float = 46.0           # dBm
    frequency_ghz: float = 3.5           # GHz
    bandwidth_mhz: float = 100.0         # MHz
    max_data_rate_mbps: float = 1000.0   # Mbps"""
    new_cell = """class CellularBaseStation:
    \"\"\"5G Macro Cellular Base Station.\"\"\"
    id: str
    position: Tuple[float, float, float]  # (x, y, z) in meters
    coverage_radius: float = field(default_factory=lambda: load_config().get("CELLULAR", {}).get("COVERAGE_RADIUS", 3500.0))
    tx_power_dbm: float = field(default_factory=lambda: load_config().get("CELLULAR", {}).get("TX_POWER_DBM", 46.0))
    frequency_ghz: float = field(default_factory=lambda: load_config().get("CELLULAR", {}).get("FREQUENCY_GHZ", 3.5))
    bandwidth_mhz: float = field(default_factory=lambda: load_config().get("CELLULAR", {}).get("BANDWIDTH_MHZ", 100.0))
    max_data_rate_mbps: float = field(default_factory=lambda: load_config().get("CELLULAR", {}).get("MAX_DATA_RATE_MBPS", 1000.0))"""
    
    content = content.replace(old_cell, new_cell)
    
    old_star = """class StarlinkSatellite:
    \"\"\"Starlink LEO Satellite Communication layer.\"\"\"
    id: str = "Starlink_LEO_Constellation"
    altitude_km: float = 550.0            # km
    latency_ms: float = 30.0              # ms
    max_data_rate_mbps: float = 200.0     # Mbps
    coverage_radius: float = 50000.0      # meters"""
    new_star = """class StarlinkSatellite:
    \"\"\"Starlink LEO Satellite Communication layer.\"\"\"
    id: str = "Starlink_LEO_Constellation"
    altitude_km: float = field(default_factory=lambda: load_config().get("STARLINK", {}).get("ALTITUDE_KM", 550.0))
    latency_ms: float = field(default_factory=lambda: load_config().get("STARLINK", {}).get("LATENCY_MS", 30.0))
    max_data_rate_mbps: float = field(default_factory=lambda: load_config().get("STARLINK", {}).get("MAX_DATA_RATE_MBPS", 200.0))
    coverage_radius: float = field(default_factory=lambda: load_config().get("STARLINK", {}).get("COVERAGE_RADIUS", 50000.0))"""
    
    content = content.replace(old_star, new_star)
    return content

def mod_models(content):
    if "from config_loader import load_config" not in content:
        content = content.replace("import math\n", "import math\nfrom config_loader import load_config\n")
        
    old_evtol_init = """    def __init__(
        self,
        vehicle_id: str,
        max_horizontal_speed: float = 50.0,  # ~180 km/h (Realistic cruise speed)
        max_climb_rate: float = 5.0,         # ~300 m/min (Realistic climb speed)
        max_descent_rate: float = 3.0,       # ~180 m/min (Realistic descent speed)
        acceleration: float = 2.5,           # m/s^2
        waypoint_arrival_radius: float = 5.0  # meters
    ):"""
    new_evtol_init = """    def __init__(
        self,
        vehicle_id: str,
        max_horizontal_speed: Optional[float] = None,
        max_climb_rate: Optional[float] = None,
        max_descent_rate: Optional[float] = None,
        acceleration: Optional[float] = None,
        waypoint_arrival_radius: Optional[float] = None
    ):"""
    
    old_evtol_body = """        self.max_h_speed = max_horizontal_speed
        self.max_climb_rate = max_climb_rate
        self.max_descent_rate = max_descent_rate
        self.acceleration = acceleration
        self.arrival_radius = waypoint_arrival_radius"""
    new_evtol_body = """        cfg = load_config().get("VEHICLE", {})
        self.max_h_speed = max_horizontal_speed if max_horizontal_speed is not None else cfg.get("MAX_HORIZONTAL_SPEED", 50.0)
        self.max_climb_rate = max_climb_rate if max_climb_rate is not None else cfg.get("MAX_CLIMB_RATE", 5.0)
        self.max_descent_rate = max_descent_rate if max_descent_rate is not None else cfg.get("MAX_DESCENT_RATE", 3.0)
        self.acceleration = acceleration if acceleration is not None else cfg.get("ACCELERATION", 2.5)
        self.arrival_radius = waypoint_arrival_radius if waypoint_arrival_radius is not None else cfg.get("ARRIVAL_RADIUS", 5.0)"""
    
    content = content.replace(old_evtol_init, new_evtol_init).replace(old_evtol_body, new_evtol_body)
    return content

def mod_main(content):
    content = content.replace("width=4000.0, height=4000.0", "width=None, height=None")
    return content

config_loader_content = """import json
import os
import re

_config_cache = None

def load_config():
    global _config_cache
    if _config_cache is not None:
        return _config_cache
    
    config_path = os.path.join(os.path.dirname(__file__), "config.md")
    if not os.path.exists(config_path):
        _config_cache = {}
        return _config_cache
        
    with open(config_path, "r") as f:
        content = f.read()
        
    match = re.search(r"```json\\s*(.*?)\\s*```", content, re.DOTALL)
    if match:
        try:
            _config_cache = json.loads(match.group(1))
        except:
            _config_cache = {}
    else:
        _config_cache = {}
        
    return _config_cache
"""

cl_path = "/home/imnyj/Workspace/paper5/config_loader.py"
if lm.acquire(cl_path, agent_id, timeout=10):
    try:
        with open(cl_path, "w") as f:
            f.write(config_loader_content)
        logger.log_action(agent_id, "CREATE", cl_path, "Created config_loader.py")
        print("Created config_loader.py")
    finally:
        lm.release(cl_path, agent_id)

edit_file("/home/imnyj/Workspace/paper5/environment.py", mod_env, "Extracted env vars to config.md")
edit_file("/home/imnyj/Workspace/paper5/models.py", mod_models, "Extracted vehicle env vars to config.md")
edit_file("/home/imnyj/Workspace/paper5/main_sim.py", mod_main, "Use config for environment dimensions")
