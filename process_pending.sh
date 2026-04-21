#!/bin/bash
# NightWatch Cron Setup
# Add to crontab: 0 3 * * * /home/alethia/never-sleep/research/process_pending.sh
cd /home/alethia/never-sleep/research
python3 process_pending.py >> /tmp/nightwatch-cron.log 2>&1
