#!bin/bash

FORCE_TEST_OTP=""
for arg in "$@"; do
  if [ "$arg" = "--force-test-otp" ]; then
    FORCE_TEST_OTP="--force-test-otp"
  fi
done

cd securityController
npm install
npm run build

tmux new-session -d "ring-server"
tmux send-keys "npm run start -- ${FORCE_TEST_OTP}" C-m

# Add the cron job for restarting the browser at 3:15 AM daily
CRON_JOB="15 3 * * * /usr/bin/curl -X POST http://localhost:3000/restart-browser >/tmp/ring-restart.log 2>&1"
( crontab -l 2>/dev/null | grep -F -q "$CRON_JOB" ) || ( crontab -l 2>/dev/null; echo "$CRON_JOB" ) | crontab -

cd ../facialRecognition
source venv/bin/activate
pip install -r server-requirements.txt
tmux new-session -d "facial-recognition"
tmux send-keys "python main.py" C-m
