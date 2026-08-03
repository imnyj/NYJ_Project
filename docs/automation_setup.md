# Automation Setup

To enable the headless automation pipeline, add the following to your crontab (`crontab -e`):

```bash
# Run nightly simulation at 2 AM every day
0 2 * * * /bin/bash /home/imnyj/scripts/nightly_sim.sh

# Run weekly digest every Friday at 5 PM
0 17 * * 5 /bin/bash /home/imnyj/scripts/weekly_digest.sh
```
