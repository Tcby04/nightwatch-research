#!/bin/bash
# NightWatch Overnight Cron Job
# Runs at 3 AM CDT daily via cron-job.org
# Set URL to your Render backend: https://your-app.onrender.com
curl -s https://nightwatch-research.onrender.com/pending || echo "NightWatch pending check complete"
