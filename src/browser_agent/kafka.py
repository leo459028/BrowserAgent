import json
import logging
from dataclasses import dataclass
from confluent_kafka import Producer, Consumer

logger = logging.getLogger(__name__)

@dataclass
class KafkaConfig:
    bootstrap_servers: str

class KafkaBus:
    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers
        self._producer = Producer({"bootstrap.servers": bootstrap_servers})

    def publish(self, topic: str, key: str, payload: dict) -> None:
        self._producer.produce(
            topic=topic,
            key=key.encode("utf-8"),
            value=json.dumps(payload).encode("utf-8"),
        )
        self._producer.flush()

    def consumer(self, group_id: str, topics: list[str]) -> Consumer:
        c = Consumer({
            "bootstrap.servers": self.bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        })
        c.subscribe(topics)
        return c

class NullBus:
    def publish(self, topic: str, key: str, payload: dict) -> None:
        logger.info("null-bus publish", extra={"topic": topic, "key": key, "payload": payload})

    def consumer(self, group_id: str, topics: list[str]):
        raise RuntimeError("NullBus does not support consuming")

def get_bus(bootstrap_servers: str | None):
    if not bootstrap_servers:
        return NullBus()
    return KafkaBus(bootstrap_servers)
