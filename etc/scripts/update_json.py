import json

with open("trajectory_baselines.json", "r") as f:
    data = json.load(f)

for item in data:
    if item["type"] == "Journal":
        item["vol"] = "N/A"
        item["no"] = "N/A"
        item["pages"] = "N/A"
    else:
        item["location"] = "N/A"
        item["pages"] = "N/A"

with open("trajectory_baselines.json", "w") as f:
    json.dump(data, f, indent=4)
print("Updated successfully.")
