import json
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
        
    match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
    if match:
        try:
            _config_cache = json.loads(match.group(1))
        except:
            _config_cache = {}
    else:
        _config_cache = {}
        
    return _config_cache
