import os
import asyncpg
from contextlib import asynccontextmanager

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://unmasked:unmasked_dev@localhost:5432/unmasked"
)


@asynccontextmanager
async def get_connection():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        await conn.close()


async def update_case_status(case_id: str, status: str):
    async with get_connection() as conn:
        await conn.execute(
            "UPDATE cases SET status = $1 WHERE case_id = $2::uuid",
            status, case_id
        )


async def save_report(case_id: str, report_data: dict):
    async with get_connection() as conn:
        await conn.execute("""
            INSERT INTO case_reports
                (case_id, report_markdown, confidence_overall, scam_pattern,
                 matched_advisory, network_size, trail_status, graph_json)
            VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8::jsonb)
            ON CONFLICT (case_id) DO UPDATE SET
                report_markdown = $2,
                confidence_overall = $3,
                scam_pattern = $4,
                matched_advisory = $5,
                network_size = $6,
                trail_status = $7,
                graph_json = $8::jsonb,
                generated_at = NOW()
        """,
            case_id,
            report_data.get("report_markdown", ""),
            report_data.get("confidence_overall", 0.0),
            report_data.get("scam_pattern", "unknown"),
            report_data.get("matched_advisory", ""),
            report_data.get("network_size", 0),
            report_data.get("trail_status", "unknown"),
            report_data.get("graph_json", "{}"),
        )

        await conn.execute(
            "UPDATE cases SET status = 'complete', completed_at = NOW() WHERE case_id = $1::uuid",
            case_id
        )