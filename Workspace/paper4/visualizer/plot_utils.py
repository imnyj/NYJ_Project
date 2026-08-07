import matplotlib.pyplot as plt

# Mapping: Model Name -> (Color, Line Style, Marker, Line Width, Z-order)
STYLE_MAP = {
    "Fixed 10Hz": ("#000000", "--", "x", 1.5, 1),
    "ReactDCC": ("#8B4513", "-", "v", 1.5, 2),
    "AdaptDCC": ("#FF0000", "-", "^", 1.5, 3),
    "TinyMLP": ("#FF69B4", "-", "<", 1.5, 4),
    "Q-Learning": ("#D3D3D3", "-", ".", 1.5, 5),
    "SARSA": ("#A9A9A9", "-", ",", 1.5, 6),
    "Actor-Critic": ("#808080", "-", "1", 1.5, 7),
    "Vanilla DQN": ("#87CEEB", "-", "s", 1.5, 8),
    "PPO": ("#0000FF", "-", "p", 1.5, 9),
    "DDPG": ("#000080", "-", "h", 1.5, 10),
    "Double DQN": ("#00FFFF", "-", "+", 1.5, 11),
    "TD3": ("#008080", "-", "d", 1.5, 12),
    "Decision Transformer": ("#90EE90", "-", "*", 1.5, 13),
    "SAC": ("#FFA500", "-", "D", 1.5, 14),
    "MAPPO": ("#808000", "-", "o", 1.5, 15),
    "REMO-DQN": ("#FF0000", "-", "*", 3.0, 99)
}

DATA_TO_CONFIG = {
    "Fixed10Hz": "Fixed 10Hz",
    "ReactDCC": "ReactDCC",
    "AdaptDCC": "AdaptDCC",
    "Heuristic": "Heuristic",
    "StdMLP": "StdMLP",
    "Proposed": "REMO-DQN",
    "DecTree": "Decision Tree",
    "TinyMLP": "TinyMLP"
}

def get_style(data_name):
    config_name = DATA_TO_CONFIG.get(data_name, data_name)
    if config_name in STYLE_MAP:
        return STYLE_MAP[config_name]
    
    # Fallback
    if config_name == "Heuristic": return ("#2E8B57", "-", "H", 1.5, 3) 
    if config_name == "Decision Tree": return ("#DAA520", "-", "v", 1.5, 4) 
    if config_name == "StdMLP": return ("#800080", "-", "p", 1.5, 4.5)
    
    return ("#000000", "-", "", 1.0, 1)

def apply_legend(ax):
    handles, labels = ax.get_legend_handles_labels()
    order_dict = {
        "Fixed 10Hz": 1, "ReactDCC": 2, "AdaptDCC": 3, "Heuristic": 3.5,
        "TinyMLP": 4, "Decision Tree": 4.2, "StdMLP": 4.5, "Q-Learning": 5, "SARSA": 6, 
        "Actor-Critic": 7, "Vanilla DQN": 8, "PPO": 9, "DDPG": 10,
        "Double DQN": 11, "TD3": 12, "Decision Transformer": 13, 
        "SAC": 14, "MAPPO": 15, "REMO-DQN": 16
    }
    sorted_pairs = sorted(zip(handles, labels), key=lambda x: order_dict.get(x[1], 99))
    s_handles = [h for h, l in sorted_pairs]
    s_labels = [l for h, l in sorted_pairs]
    ax.legend(s_handles, s_labels, bbox_to_anchor=(1.05, 1), loc='upper left', ncol=1)

