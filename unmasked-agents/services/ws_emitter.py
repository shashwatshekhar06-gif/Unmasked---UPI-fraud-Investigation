import os
import json
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_redis_client = None


def get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL)
    return _redis_client


def emit_agent_event(case_id: str, agent_name: str, status: str, data: dict = None):
    """
    Publish event to Redis pub/sub channel.
    Spring Boot subscribes to 'unmasked:ws:*' pattern and forwards to STOMP WebSocket.
    Frontend receives live updates as agents complete.
    """
    event = {
        "case_id": case_id,
        "agent": agent_name,
        "status": status,
        "data": data or {},
    }
    channel = f"unmasked:ws:{case_id}"
    get_redis().publish(channel, json.dumps(event))
