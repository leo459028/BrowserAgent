#!/usr/bin/env bash
set -euo pipefail

KAFKA_CONTAINER=${KAFKA_CONTAINER:-kafka}
docker exec -i "${KAFKA_CONTAINER}" bash -lc '
  kafka-topics.sh --bootstrap-server kafka:9092 --create --if-not-exists --topic agent.tasks.created --partitions 3 --replication-factor 1
  kafka-topics.sh --bootstrap-server kafka:9092 --create --if-not-exists --topic agent.tasks.queued --partitions 3 --replication-factor 1
  kafka-topics.sh --bootstrap-server kafka:9092 --create --if-not-exists --topic agent.tasks.failed --partitions 3 --replication-factor 1
  kafka-topics.sh --bootstrap-server kafka:9092 --create --if-not-exists --topic agent.tasks.completed --partitions 3 --replication-factor 1
'
