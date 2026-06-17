from typing import TypedDict, List, Optional, Annotated
import operator


def merge_lists(a: list, b: list) -> list:
    return a + b


class InvestigationState(TypedDict):
    # Input — set once
    case_id: str
    victim_vpa: str
    fraud_vpa: str
    amount: float
    transaction_ref: str

    # Agent 1 — Transaction Tracer
    transaction_chain: Annotated[List[dict], merge_lists]
    chain_depth: int
    trail_status: str

    # Agent 2 — Identity Intelligence
    vpa_intelligence: Annotated[List[dict], merge_lists]
    identity_flags: Annotated[List[str], merge_lists]

    # Agent 3 — Scam Classifier
    scam_classification: Optional[dict]
    rag_context: Annotated[List[str], merge_lists]

    # Agent 4 — Network Expansion
    fraud_network_nodes: Annotated[List[dict], merge_lists]
    fraud_network_edges: Annotated[List[dict], merge_lists]
    network_size: int

    # Agent 5 — Report Generator
    report_markdown: Optional[str]
    confidence_overall: float

    # Meta — these get written by multiple agents in parallel, so they need merge
    errors: Annotated[List[str], merge_lists]
    completed_agents: Annotated[List[str], merge_lists]
    websocket_events: Annotated[List[dict], merge_lists]