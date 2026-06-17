from dotenv import load_dotenv
load_dotenv("../.env")
import os
import json
import asyncio
import redis
from celery import Celery

from services.pipeline import run_investigation
from services.db import update_case_status
from services.ws_emitter import emit_agent_event

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Celery app
celery_app = Celery("unmasked", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,
    worker_concurrency=4,
)

INVESTIGATION_QUEUE = "unmasked:investigation_queue"


@celery_app.task(name="run_investigation_task", bind=True, max_retries=2)
def run_investigation_task(self, job_json: str):
    """
    Celery task that runs the LangGraph investigation pipeline.
    Producer-consumer pattern: Spring Boot pushes to Redis list,
    this worker pops and processes.
    """
    try:
        job = json.loads(job_json)
        case_id = job["case_id"]

        # Update status to processing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        loop.run_until_complete(update_case_status(case_id, "processing"))
        emit_agent_event(case_id, "pipeline", "started")

        # Run the full pipeline
        result = loop.run_until_complete(run_investigation(job))

        emit_agent_event(case_id, "pipeline", "completed", {
            "confidence_overall": result.get("confidence_overall", 0),
            "agents_completed": result.get("completed_agents", []),
        })

        loop.close()
        return {"case_id": case_id, "status": "complete"}

    except Exception as e:
        case_id = json.loads(job_json).get("case_id", "unknown")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(update_case_status(case_id, "failed"))
        loop.close()

        emit_agent_event(case_id, "pipeline", "failed", {"error": str(e)})
        raise self.retry(exc=e, countdown=10)


def start_queue_consumer():
    """
    Background thread that pops jobs from the Redis list
    and dispatches them as Celery tasks.
    """
    r = redis.from_url(REDIS_URL)
    print(f"[Queue Consumer] Listening on {INVESTIGATION_QUEUE}...")

    while True:
        try:
            # BRPOP blocks until a job is available (producer-consumer pattern)
            result = r.brpop(INVESTIGATION_QUEUE, timeout=5)
            if result:
                _, job_json = result
                job_str = job_json.decode("utf-8") if isinstance(job_json, bytes) else job_json
                job = json.loads(job_str)
                print(f"[Queue Consumer] Received job for case: {job['case_id']}")

                # Dispatch to Celery
                run_investigation_task.delay(job_str)
        except Exception as e:
            print(f"[Queue Consumer] Error: {e}")
