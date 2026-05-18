#!/bin/sh
set -e

if [ "$RUN_STARTUP_TASKS" != "false" ]; then
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput --clear
fi

exec "$@"
