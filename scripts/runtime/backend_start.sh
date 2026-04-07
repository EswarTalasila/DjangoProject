#!/bin/sh
set -eu

mkdir -p /app/media /app/media/assessments /app/media/submissions /app/traces

# Dev/test bind mounts come from the host, so fix ownership at container startup.
chown -R django:django /app/media /app/traces

run_as_django() {
  su -s /bin/sh django -c "$1"
}

run_as_django "python src/manage.py migrate"

if [ "${ENVIRONMENT:-development}" = "production" ]; then
  run_as_django "python src/manage.py collectstatic --noinput"
fi

run_as_django "python src/manage.py ensure_admin"

if [ "${ENVIRONMENT:-development}" = "testing" ]; then
  run_as_django "python src/manage.py seed_e2e"
fi

exec su -s /bin/sh django -c "python src/manage.py runserver 0.0.0.0:8000"
