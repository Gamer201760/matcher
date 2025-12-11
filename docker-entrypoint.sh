#!/bin/bash

# Удаляем кавычки из CRON_SCHEDULE
CRON_SCHEDULE="${CRON_SCHEDULE%\"}"
CRON_SCHEDULE="${CRON_SCHEDULE#\"}"

# Пример entrypoint-скрипта
cat > /tmp/crontab << EOF
NEO4J_URI=$NEO4J_URI
NEO4J_USERNAME=$NEO4J_USERNAME
NEO4J_PASSWORD=$NEO4J_PASSWORD
NEO4J_DATABASE=$NEO4J_DATABASE
KAFKA_BOOTSTRAP_SERVERS=$KAFKA_BOOTSTRAP_SERVERS
REDIS_HOST=$REDIS_HOST
REDIS_PORT=$REDIS_PORT

$CRON_SCHEDULE /bin/bash -c 'cd /app && /app/.venv/bin/python3 -m adapter.calc.main >> /proc/1/fd/1 2>> /proc/1/fd/2'
EOF

crontab /tmp/crontab
cron -f
