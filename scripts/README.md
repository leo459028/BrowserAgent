# Scripts

- `bootstrap.py`：建立 SQLAlchemy tables、seed local dev tenant/users，並在 `BOOTSTRAP_KAFKA_TOPICS=true` 時建立 Kafka topics。
- `create_topics.sh`：在本機 Docker Compose Kafka 環境中建立 topics 的 shell helper。
