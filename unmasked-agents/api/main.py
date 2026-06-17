import os
import threading
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv("../.env")

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.pipeline import run_investigation
from services.celery_app import start_queue_consumer
from services.db import update_case_status, get_connection
from services.pdf_report import generate_pdf


@asynccontextmanager
async def lifespan(app: FastAPI):
    consumer_thread = threading.Thread(target=start_queue_consumer, daemon=True)
    consumer_thread.start()
    print("[FastAPI] Queue consumer started")
    yield
    print("[FastAPI] Shutting down")


app = FastAPI(
    title="UNMASKED Agent Pipeline",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "unmasked-agents"}


class ManualInvestigationRequest(BaseModel):
    case_id: str
    victim_vpa: str
    fraud_vpa: str
    amount: float
    transaction_ref: str


@app.post("/investigate")
async def manual_investigate(request: ManualInvestigationRequest):
    try:
        await update_case_status(request.case_id, "processing")
        result = await run_investigation(request.model_dump())
        return {
            "case_id": request.case_id,
            "status": "complete",
            "confidence": result.get("confidence_overall", 0),
            "trail_status": result.get("trail_status", "unknown"),
            "network_size": result.get("network_size", 0),
            "agents_completed": result.get("completed_agents", []),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/report/{case_id}/pdf")
async def download_pdf(case_id: str):
    """Generate and download a professional PDF evidence report."""
    try:
        async with get_connection() as conn:
            # Fetch report
            report_row = await conn.fetchrow(
                "SELECT * FROM case_reports WHERE case_id = $1::uuid", case_id
            )
            if not report_row:
                raise HTTPException(status_code=404, detail="Report not found")

            # Fetch case
            case_row = await conn.fetchrow(
                "SELECT * FROM cases WHERE case_id = $1::uuid", case_id
            )

            report_data = {
                'report_markdown': report_row['report_markdown'],
                'confidence_overall': float(report_row['confidence_overall']) if report_row['confidence_overall'] else 0,
                'scam_pattern': report_row['scam_pattern'],
                'matched_advisory': report_row['matched_advisory'],
                'network_size': report_row['network_size'],
                'trail_status': report_row['trail_status'],
                'graph_json': report_row['graph_json'],
            }

            case_data = {
                'case_id': str(case_row['case_id']),
                'fraud_vpa': case_row['fraud_vpa'],
                'victim_vpa': case_row['victim_vpa'],
                'amount': float(case_row['amount']),
                'transaction_ref': case_row['transaction_ref'],
            } if case_row else {}

        pdf_bytes = generate_pdf(report_data, case_data)

        filename = f"UNMASKED_Report_{case_id[:8].upper()}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
