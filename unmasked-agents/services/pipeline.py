import asyncio
from langgraph.graph import StateGraph, START, END
from models.investigation_state import InvestigationState
from agents.agents import (
    transaction_tracer_agent,
    identity_intelligence_agent,
    scam_classifier_agent,
    network_expansion_agent,
    report_generator_agent,
)


def build_pipeline():
    """
    Build the LangGraph investigation pipeline.

    Flow:
        START
          ├──► transaction_tracer ──┐
          └──► identity_intelligence──┤  (parallel fan-out)
                                     ▼
                              scam_classifier  (fan-in join)
                                     │
                                     ▼
                            network_expansion
                                     │
                                     ▼
                            report_generator
                                     │
                                    END
    """
    graph = StateGraph(InvestigationState)

    # Add all agent nodes
    graph.add_node("transaction_tracer", transaction_tracer_agent)
    graph.add_node("identity_intelligence", identity_intelligence_agent)
    graph.add_node("scam_classifier", scam_classifier_agent)
    graph.add_node("network_expansion", network_expansion_agent)
    graph.add_node("report_generator", report_generator_agent)

    # Parallel fan-out from START: Agents 1 and 2 run simultaneously
    graph.add_edge(START, "transaction_tracer")
    graph.add_edge(START, "identity_intelligence")

    # Fan-in: both feed into Agent 3 (LangGraph handles the join)
    graph.add_edge("transaction_tracer", "scam_classifier")
    graph.add_edge("identity_intelligence", "scam_classifier")

    # Sequential from here
    graph.add_edge("scam_classifier", "network_expansion")
    graph.add_edge("network_expansion", "report_generator")
    graph.add_edge("report_generator", END)

    return graph.compile()


# Singleton pipeline instance
pipeline = build_pipeline()


async def run_investigation(case_data: dict) -> dict:
    """Run the full investigation pipeline for a case."""
    initial_state = {
        "case_id": case_data["case_id"],
        "victim_vpa": case_data["victim_vpa"],
        "fraud_vpa": case_data["fraud_vpa"],
        "amount": float(case_data["amount"]),
        "transaction_ref": case_data["transaction_ref"],
        # Initialize empty collections
        "transaction_chain": [],
        "chain_depth": 0,
        "trail_status": "pending",
        "vpa_intelligence": [],
        "identity_flags": [],
        "scam_classification": None,
        "rag_context": [],
        "fraud_network_nodes": [],
        "fraud_network_edges": [],
        "network_size": 0,
        "report_markdown": None,
        "confidence_overall": 0.0,
        "errors": [],
        "completed_agents": [],
        "websocket_events": [],
    }

    result = await pipeline.ainvoke(initial_state)
    return result
