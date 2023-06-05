#!/bin/sh

# starts the development server using gunicorn
# NEVER run production with the --reload option command
echo "Starting gunicorn"
export PYTHONWARNINGS=always
prefix=""
if [ -f "/usr/local/bin/berglas" ]; then
  prefix="berglas exec --"
fi
suffix=""
if [[ "$STATSD_HOST" ]]; then
  suffix="--statsd-host ${STATSD_HOST}:${STATSD_PORT}"
fi
reload=""
if [[ "$RUN_ENV" = "staging" ]]; then
  reload="--reload"
fi
$prefix gunicorn codecov_slack_app.wsgi:application $reload --workers=${GUNICORN_WORKERS:-2} --threads=${GUNICORN_THREADS:-1} --bind 0.0.0.0:8000 --access-logfile '-' --timeout "${GUNICORN_TIMEOUT:-600}" $suffix
