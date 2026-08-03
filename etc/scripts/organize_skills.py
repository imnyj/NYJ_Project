import os
import shutil

base_dir = "/home/imnyj/.agents/skills"
plugins = {
    "paper-writing": ["academic-writer", "academic-critic", "academic-librarian", "academic-idea"],
    "sumo-sim": ["academic-coder", "academic-visualizer", "simulation-tuner", "gpu-balancer"],
    "admin-proposal": ["instructional-designer"]
}

for plugin, skills in plugins.items():
    plugin_path = os.path.join(base_dir, plugin)
    os.makedirs(plugin_path, exist_ok=True)
    
    # Create README.md
    with open(os.path.join(plugin_path, "README.md"), "w") as f:
        f.write(f"# {plugin} Plugin Bundle\n")
        f.write("Contains domain-specific skills.\n")
        f.write("Dependencies: None extra.\n")
        f.write("Permissions: Default workspace read/write.\n\n")
        f.write("## Skills Included:\n")
        for s in skills:
            f.write(f"- {s}\n")
            
    # Move skills
    for s in skills:
        src = os.path.join(base_dir, s)
        dst = os.path.join(plugin_path, s)
        if os.path.exists(src):
            shutil.move(src, dst)

print("Skills organized.")
