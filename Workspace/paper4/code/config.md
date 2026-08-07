# SUMO Environment Configuration

This file configures the SUMO network environment. If you set `AV_SPEED` or `DENSITY` to 0, they will be randomly selected per simulation run.

| Variable | Value | Description |
|---|---|---|
| AV_SPEED | 60 | Average vehicle speed (km/h). 0 for random. |
| DENSITY | 0 | Vehicle density (/1km-lane). 0 for random. |
| NUM_BLOCKS | 6 | Number of grid blocks. |
| MAX_STEPS | 3600.0 | Maximum simulation steps. |
| OUTAGE_ZONE | 800 | Outage zone size. |
| RSU_RANGE | 800.0 | Communication range of RSU. |
