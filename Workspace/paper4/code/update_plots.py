import glob

files = glob.glob("/home/imnyj/papers/paper4/sim/plot_*.py")

for filepath in files:
    with open(filepath, "r") as f:
        content = f.read()

    # Replace old map
    old_map_1 = """name_map = {
    'ReactDCC': 'ETSI-Reactive',
    'AdaptDCC': 'Adaptive-DCC',
    'Heuristic': 'Stat-DCC',
    'Fixed10Hz': 'Fixed-10Hz',
    'Proposed': 'Proposed (TinyMLP)'
}"""
    
    new_map = """name_map = {
    'ReactDCC': 'ReactDCC',
    'AdaptDCC': 'AdaptDCC',
    'Heuristic': 'Heuristic',
    'Fixed10Hz': 'Fixed10Hz',
    'DecTree': 'DecTree',
    'StdMLP': 'StdMLP',
    'Proposed': 'TinyMLP'
}"""

    content = content.replace(old_map_1, new_map)

    # For plot_bubble.py colors
    old_colors_bubble = """colors = {
    'Fixed-10Hz': '#cccccc',
    'Stat-DCC': '#aaaaaa',
    'Adaptive-DCC': '#777777',
    'ETSI-Reactive': '#444444',
    'Proposed (TinyMLP)': '#cc0000'
}"""
    
    new_colors_bubble = """colors = {
    'Fixed10Hz': '#cccccc',
    'Heuristic': '#aaaaaa',
    'AdaptDCC': '#777777',
    'ReactDCC': '#444444',
    'DecTree': '#1f77b4',
    'StdMLP': '#ff7f0e',
    'TinyMLP': '#cc0000'
}"""
    content = content.replace(old_colors_bubble, new_colors_bubble)
    
    # For plot_radar.py colors
    old_colors_radar = """colors = {
    'Fixed-10Hz': '#cccccc',
    'Stat-DCC': '#aaaaaa',
    'Adaptive-DCC': '#777777',
    'ETSI-Reactive': '#444444',
    'Proposed (TinyMLP)': 'red'
}"""
    new_colors_radar = """colors = {
    'Fixed10Hz': '#cccccc',
    'Heuristic': '#aaaaaa',
    'AdaptDCC': '#777777',
    'ReactDCC': '#444444',
    'DecTree': '#1f77b4',
    'StdMLP': '#ff7f0e',
    'TinyMLP': 'red'
}"""
    content = content.replace(old_colors_radar, new_colors_radar)
    
    # plot_sweep.py styles
    old_styles = """styles = {
    'Fixed-10Hz': ('#cccccc', '--'),
    'Stat-DCC': ('#aaaaaa', '-.'),
    'Adaptive-DCC': ('#777777', '--'),
    'ETSI-Reactive': ('#444444', ':'),
    'Proposed (TinyMLP)': ('#cc0000', '-')
}"""
    new_styles = """styles = {
    'Fixed10Hz': ('#cccccc', '--'),
    'Heuristic': ('#aaaaaa', '-.'),
    'AdaptDCC': ('#777777', '--'),
    'ReactDCC': ('#444444', ':'),
    'DecTree': ('#1f77b4', '-.'),
    'StdMLP': ('#ff7f0e', '--'),
    'TinyMLP': ('#cc0000', '-')
}"""
    content = content.replace(old_styles, new_styles)

    with open(filepath, "w") as f:
        f.write(content)
