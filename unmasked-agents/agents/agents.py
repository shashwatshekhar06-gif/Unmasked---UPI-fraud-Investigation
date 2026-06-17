import os
import json
import asyncio
from datetime import datetime

from openai import OpenAI
from models.investigation_state import InvestigationState
from services.db import get_connection
from services.vpa_utils import extract_bank, compute_mule_confidence, extract_naming_pattern
from services.embeddings import search_knowledge_base
from services.ws_emitter import emit_agent_event

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
llm_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

MAX_HOP_DEPTH = 4
CASH_OUT_THRESHOLD = 10.0  # amount drops >90% = cash out


# ============================================================
# AGENT 1 — Transaction Tracer
# DSA: Iterative graph traversal (BFS over transaction edges)
# ============================================================

async def transaction_tracer_agent(state: InvestigationState) -> dict:
    case_id = state["case_id"]
    fraud_vpa = state["fraud_vpa"]

    emit_agent_event(case_id, "transaction_tracer", "started")

    chain = []
    trail_status = "complete"

    try:
        async with get_connection() as conn:
            # Get all transactions for this case, ordered by hop
            rows = await conn.fetch("""
                SELECT sender_vpa, receiver_vpa, amount, timestamp,
                       hop_number, time_delta_seconds, amount_drop_pct,
                       is_cash_out
                FROM transactions
                WHERE case_id = $1::uuid
                ORDER BY hop_number ASC
            """, case_id)

            if not rows:
                # No pre-existing transactions — do live BFS traversal
                # Start from fraud_vpa and walk outward
                rows = await conn.fetch("""
                    SELECT sender_vpa, receiver_vpa, amount, timestamp,
                           time_delta_seconds
                    FROM transactions
                    WHERE sender_vpa = $1
                    ORDER BY timestamp ASC
                    LIMIT 20
                """, fraud_vpa)

            for row in rows:
                hop = {
                    "sender_vpa": row["sender_vpa"],
                    "receiver_vpa": row["receiver_vpa"],
                    "amount": float(row["amount"]),
                    "timestamp": str(row["timestamp"]),
                    "hop_number": row.get("hop_number", 0),
                    "time_delta_seconds": row.get("time_delta_seconds"),
                    "receiver_bank": extract_bank(row["receiver_vpa"]),
                    "amount_drop_pct": float(row["amount_drop_pct"]) if row.get("amount_drop_pct") else None,
                    "is_cash_out": row.get("is_cash_out", False),
                }
                chain.append(hop)

                # Detect cash-out
                if hop["is_cash_out"] or (hop["amount_drop_pct"] and hop["amount_drop_pct"] > 90):
                    trail_status = "cash_out_detected"

            # If chain is short and no cash-out, trail went cold
            if len(chain) <= 1 and trail_status == "complete":
                trail_status = f"cold_at_hop_{len(chain)}"

    except Exception as e:
        return {
            "transaction_chain": chain,
            "chain_depth": len(chain),
            "trail_status": "error",
            "errors": state.get("errors", []) + [f"transaction_tracer: {str(e)}"],
            "completed_agents": state.get("completed_agents", []) + ["transaction_tracer"],
        }

    emit_agent_event(case_id, "transaction_tracer", "completed", {
        "chain_depth": len(chain),
        "trail_status": trail_status,
    })

    return {
        "transaction_chain": chain,
        "chain_depth": len(chain),
        "trail_status": trail_status,
        "completed_agents": state.get("completed_agents", []) + ["transaction_tracer"],
    }


# ============================================================
# AGENT 2 — Identity Intelligence
# DSA: Pattern matching, weighted scoring, fuzzy VPA match
# Runs PARALLEL with Agent 1
# ============================================================

async def identity_intelligence_agent(state: InvestigationState) -> dict:
    case_id = state["case_id"]
    fraud_vpa = state["fraud_vpa"]

    emit_agent_event(case_id, "identity_intelligence", "started")

    vpa_intel = []
    identity_flags = []

    try:
        async with get_connection() as conn:
            # Get all VPAs involved in this case
            vpas_in_case = await conn.fetch("""
                SELECT DISTINCT vpa FROM (
                    SELECT sender_vpa AS vpa FROM transactions WHERE case_id = $1::uuid
                    UNION
                    SELECT receiver_vpa AS vpa FROM transactions WHERE case_id = $1::uuid
                ) sub
            """, case_id)

            vpa_list = [row["vpa"] for row in vpas_in_case]

            for vpa in vpa_list:
                # Look up in VPA registry
                reg = await conn.fetchrow(
                    "SELECT * FROM vpa_registry WHERE vpa = $1", vpa
                )

                if reg:
                    age = reg["account_age_days"]
                    cases = reg["total_cases_involved"]
                    risk = float(reg["risk_score"])
                    flags = list(reg["flags"]) if reg["flags"] else []
                else:
                    age = None
                    cases = 1
                    risk = 0.0
                    flags = []

                mule_conf = compute_mule_confidence(age, cases, risk)

                intel = {
                    "vpa": vpa,
                    "registrar_bank": extract_bank(vpa),
                    "account_age_days": age,
                    "total_cases_involved": cases,
                    "risk_score": risk,
                    "mule_confidence": mule_conf,
                    "flags": flags,
                }
                vpa_intel.append(intel)

                # Flag high-confidence mules
                if mule_conf > 0.6:
                    identity_flags.append(f"HIGH_MULE_CONFIDENCE: {vpa} ({mule_conf})")

                # Flag new accounts
                if age is not None and age < 7:
                    identity_flags.append(f"NEW_ACCOUNT: {vpa} ({age} days old)")

                # Flag repeat offenders
                if cases > 2:
                    identity_flags.append(f"REPEAT_OFFENDER: {vpa} (seen in {cases} cases)")

            # Fuzzy match: find VPAs with similar naming patterns
            similar = await conn.fetch("""
                SELECT vpa, similarity(vpa, $1) AS sim, risk_score, total_cases_involved
                FROM vpa_registry
                WHERE vpa != $1
                  AND similarity(vpa, $1) > 0.3
                ORDER BY sim DESC
                LIMIT 10
            """, fraud_vpa)

            for row in similar:
                identity_flags.append(
                    f"SIMILAR_VPA: {row['vpa']} (similarity: {round(float(row['sim']), 2)}, "
                    f"risk: {float(row['risk_score'])})"
                )

            # Update VPA registry risk scores
            for intel in vpa_intel:
                if intel["mule_confidence"] > 0.5:
                    new_risk = max(intel["risk_score"], intel["mule_confidence"])
                    new_flags = list(set(intel["flags"] + ["investigated"]))
                    await conn.execute("""
                        INSERT INTO vpa_registry (vpa, registrar_bank, risk_score, flags, vpa_type, naming_pattern)
                        VALUES ($1, $2, $3, $4, 'personal', $5)
                        ON CONFLICT (vpa) DO UPDATE SET
                            risk_score = GREATEST(vpa_registry.risk_score, $3),
                            flags = ARRAY(SELECT DISTINCT unnest(vpa_registry.flags || $4)),
                            last_seen_at = NOW()
                    """,
                        intel["vpa"], intel["registrar_bank"], new_risk,
                        new_flags, extract_naming_pattern(intel["vpa"])
                    )

    except Exception as e:
        return {
            "vpa_intelligence": vpa_intel,
            "identity_flags": identity_flags,
            "errors": state.get("errors", []) + [f"identity_intelligence: {str(e)}"],
            "completed_agents": state.get("completed_agents", []) + ["identity_intelligence"],
        }

    emit_agent_event(case_id, "identity_intelligence", "completed", {
        "vpas_analyzed": len(vpa_intel),
        "flags_found": len(identity_flags),
    })

    return {
        "vpa_intelligence": vpa_intel,
        "identity_flags": identity_flags,
        "completed_agents": state.get("completed_agents", []) + ["identity_intelligence"],
    }


# ============================================================
# AGENT 3 — Scam Pattern Classifier
# DSA: Cosine similarity / approximate nearest-neighbor search
# Runs AFTER Agents 1+2 complete (fan-in)
# ============================================================

async def scam_classifier_agent(state: InvestigationState) -> dict:
    case_id = state["case_id"]

    emit_agent_event(case_id, "scam_classifier", "started")

    # Build query text from case facts for RAG search
    chain = state.get("transaction_chain", [])
    flags = state.get("identity_flags", [])
    amount = state.get("amount", 0)

    query_parts = [
        f"UPI fraud amount Rs {amount}",
        f"Transaction chain depth: {len(chain)} hops",
        f"Trail status: {state.get('trail_status', 'unknown')}",
    ]

    if chain:
        avg_delta = sum(
            h.get("time_delta_seconds", 0) or 0 for h in chain
            if h.get("time_delta_seconds")
        )
        hop_count = sum(1 for h in chain if h.get("time_delta_seconds"))
        if hop_count > 0:
            avg_delta = avg_delta / hop_count
            query_parts.append(f"Average time between hops: {avg_delta:.0f} seconds")

        if any(h.get("is_cash_out") for h in chain):
            query_parts.append("Cash-out detected at end of chain")

    for flag in flags[:5]:  # top 5 flags
        query_parts.append(flag)

    query_text = ". ".join(query_parts)

    try:
        # RAG search over knowledge base
        results = await search_knowledge_base(query_text, top_k=3, threshold=0.4)

        rag_context = [r["content"] for r in results]

        if results:
            best = results[0]
            metadata = json.loads(best["metadata"]) if isinstance(best["metadata"], str) else best["metadata"]
            classification = {
                "pattern_name": metadata.get("pattern_name", "Unknown Pattern"),
                "confidence": best["similarity"],
                "matched_advisory": best["source"],
                "evidence_points": metadata.get("evidence_points", []),
                "source": best["source"],
            }
        else:
            classification = {
                "pattern_name": "Unclassified",
                "confidence": 0.0,
                "matched_advisory": "No matching advisory found",
                "evidence_points": [],
                "source": "none",
            }

    except Exception as e:
        return {
            "scam_classification": {"pattern_name": "Error", "confidence": 0.0,
                                     "matched_advisory": "", "evidence_points": [], "source": ""},
            "rag_context": [],
            "errors": state.get("errors", []) + [f"scam_classifier: {str(e)}"],
            "completed_agents": state.get("completed_agents", []) + ["scam_classifier"],
        }

    emit_agent_event(case_id, "scam_classifier", "completed", {
        "pattern": classification["pattern_name"],
        "confidence": classification["confidence"],
    })

    return {
        "scam_classification": classification,
        "rag_context": rag_context,
        "completed_agents": state.get("completed_agents", []) + ["scam_classifier"],
    }


# ============================================================
# AGENT 4 — Network Expansion
# DSA: BFS encoded in PostgreSQL recursive CTE
# ============================================================

async def network_expansion_agent(state: InvestigationState) -> dict:
    case_id = state["case_id"]
    fraud_vpa = state["fraud_vpa"]

    emit_agent_event(case_id, "network_expansion", "started")

    nodes = []
    edges = []

    try:
        async with get_connection() as conn:
            # Call the recursive CTE BFS function
            bfs_rows = await conn.fetch(
                "SELECT * FROM fraud_network_bfs($1, 3)",
                fraud_vpa
            )

            # Build node set (deduplicate)
            seen_vpas = set()

            # Add root node
            root_reg = await conn.fetchrow(
                "SELECT * FROM vpa_registry WHERE vpa = $1", fraud_vpa
            )
            root_risk = float(root_reg["risk_score"]) if root_reg else 0.5
            root_flags = list(root_reg["flags"]) if root_reg and root_reg["flags"] else []

            nodes.append({
                "id": fraud_vpa,
                "label": fraud_vpa,
                "risk_score": root_risk,
                "depth": 0,
                "bank": extract_bank(fraud_vpa),
                "flags": root_flags,
            })
            seen_vpas.add(fraud_vpa)

            for row in bfs_rows:
                vpa = row["vpa"]
                if vpa not in seen_vpas:
                    nodes.append({
                        "id": vpa,
                        "label": vpa,
                        "risk_score": float(row["risk_score"]),
                        "depth": row["depth"],
                        "bank": row["registrar_bank"] or extract_bank(vpa),
                        "flags": list(row["flags"]) if row["flags"] else [],
                    })
                    seen_vpas.add(vpa)

                edges.append({
                    "source": row["connected_from"],
                    "target": vpa,
                    "amount": float(row["amount"]),
                    "time_delta_seconds": row["time_delta_seconds"],
                })

    except Exception as e:
        return {
            "fraud_network_nodes": nodes,
            "fraud_network_edges": edges,
            "network_size": len(nodes),
            "errors": state.get("errors", []) + [f"network_expansion: {str(e)}"],
            "completed_agents": state.get("completed_agents", []) + ["network_expansion"],
        }

    emit_agent_event(case_id, "network_expansion", "completed", {
        "network_size": len(nodes),
        "edges": len(edges),
        "nodes": [{"id": n["id"], "risk": n["risk_score"], "depth": n["depth"]} for n in nodes[:10]],
    })

    return {
        "fraud_network_nodes": nodes,
        "fraud_network_edges": edges,
        "network_size": len(nodes),
        "completed_agents": state.get("completed_agents", []) + ["network_expansion"],
    }


# ============================================================
# AGENT 5 — Case Report Generator
# Constrained LLM output — no free generation, only cited facts
# ============================================================

REPORT_SYSTEM_PROMPT = """You are a forensic evidence report generator for UPI fraud investigations in India.

STRICT RULES:
1. ONLY use facts from the FACTS section — each is numbered F1, F2, etc.
2. NEVER show fact numbers (F1, F2) in your output. Use the data, don't cite the labels.
3. NEVER infer beyond provided data.
4. NEVER claim to know the real identity behind a VPA.
5. Use confidence scores exactly as provided.
6. Separate VERIFIED FINDINGS from INFERRED SIGNALS clearly.
7. If trail_status says "cold" but network_size is large, explain that the direct money trail went cold but network intelligence from prior investigations revealed connected accounts.

OUTPUT FORMAT (markdown):

# Investigation Report

## Case overview
One paragraph summarizing victim VPA, fraud VPA, amount, and what was found. No bullet points.

## Money trail
Describe each hop naturally: "The money moved from [sender] to [receiver] (₹amount) within [time] seconds via [bank]." If trail went cold, explain what that means. If cash-out detected, highlight it.

## Mule account analysis
For each suspicious account, describe: the VPA, why it's suspicious (account age, cases involved, flags), and the mule confidence percentage. Write as prose, not a list.

## Scam classification
State the pattern name, confidence percentage, and which advisory it matched. Briefly describe what this scam type involves.

## Connected fraud network
State the network size. Explain that this represents ALL accounts connected to this fraud VPA across all investigations, not just this case. Mention key high-risk nodes if any. If trail was cold but network is large, explain this clearly.

## Legal basis
List applicable IT Act and IPC/BNS sections WITH their descriptions (e.g. "Section 66C of the IT Act — identity theft using another person's credentials, punishable by up to 3 years"). Be specific based on the scam type.

## Confidence assessment
Overall confidence percentage. What is verified vs what is inferred. Be honest about limitations.

## Recommended next steps
Specific, actionable steps for law enforcement. Include which banks to contact, what to freeze, what evidence to preserve.
"""


async def report_generator_agent(state: InvestigationState) -> dict:
    case_id = state["case_id"]

    emit_agent_event(case_id, "report_generator", "started")

    # Build numbered facts from state
    facts = []
    fact_num = 1

    # Case basics
    facts.append(f"F{fact_num}: Victim VPA is {state['victim_vpa']}")
    fact_num += 1
    facts.append(f"F{fact_num}: Fraud VPA is {state['fraud_vpa']}")
    fact_num += 1
    facts.append(f"F{fact_num}: Fraud amount is Rs {state['amount']}")
    fact_num += 1
    facts.append(f"F{fact_num}: Transaction reference is {state['transaction_ref']}")
    fact_num += 1

    # Transaction chain facts
    chain = state.get("transaction_chain", [])
    facts.append(f"F{fact_num}: Transaction chain has {len(chain)} hops")
    fact_num += 1
    facts.append(f"F{fact_num}: Trail status is {state.get('trail_status', 'unknown')}")
    fact_num += 1

    for hop in chain:
        facts.append(
            f"F{fact_num}: Hop {hop.get('hop_number', '?')}: "
            f"{hop['sender_vpa']} → {hop['receiver_vpa']}, "
            f"Rs {hop['amount']}, time delta: {hop.get('time_delta_seconds', 'N/A')}s, "
            f"bank: {hop.get('receiver_bank', 'unknown')}"
            f"{', CASH-OUT' if hop.get('is_cash_out') else ''}"
        )
        fact_num += 1

    # VPA intelligence facts
    for intel in state.get("vpa_intelligence", []):
        if intel.get("mule_confidence", 0) > 0.3:
            facts.append(
                f"F{fact_num}: VPA {intel['vpa']} — mule confidence: {intel['mule_confidence']}, "
                f"account age: {intel.get('account_age_days', 'unknown')} days, "
                f"seen in {intel.get('total_cases_involved', 1)} cases, "
                f"flags: {', '.join(intel.get('flags', []))}"
            )
            fact_num += 1

    # Scam classification facts
    classification = state.get("scam_classification", {})
    if classification:
        facts.append(
            f"F{fact_num}: Scam classified as '{classification.get('pattern_name', 'unknown')}' "
            f"with confidence {classification.get('confidence', 0)}"
        )
        fact_num += 1
        facts.append(
            f"F{fact_num}: Matched advisory: {classification.get('matched_advisory', 'none')}"
        )
        fact_num += 1

    # Network facts
    facts.append(f"F{fact_num}: Fraud network contains {state.get('network_size', 0)} nodes")
    fact_num += 1

    # Identity flags
    for flag in state.get("identity_flags", [])[:10]:
        facts.append(f"F{fact_num}: {flag}")
        fact_num += 1

    facts_text = "\n".join(facts)

    # Generate report via LLM
    report_markdown = ""
    confidence_overall = 0.0

    if llm_client:
        try:
            response = llm_client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.1,  # factual, not creative
                messages=[
                    {"role": "system", "content": REPORT_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Generate the investigation report.\n\nFACTS:\n{facts_text}"},
                ],
                max_tokens=3000,
            )
            report_markdown = response.choices[0].message.content
        except Exception as e:
            report_markdown = f"# Report Generation Error\n\nFailed to generate report: {str(e)}\n\n## Raw Facts\n\n{facts_text}"
    else:
        report_markdown = f"# UNMASKED Investigation Report\n\n## Raw Facts (LLM not configured)\n\n{facts_text}"

    # Calculate overall confidence as weighted average
    chain_confidence = 0.8 if len(chain) > 2 else 0.5 if len(chain) > 0 else 0.2
    classification_confidence = classification.get("confidence", 0) if classification else 0
    intel_count = len([i for i in state.get("vpa_intelligence", []) if i.get("mule_confidence", 0) > 0.5])
    intel_confidence = min(0.9, intel_count * 0.15) if intel_count > 0 else 0.3
    network_confidence = 0.8 if state.get("network_size", 0) > 3 else 0.5

    confidence_overall = round(
        chain_confidence * 0.30 +
        classification_confidence * 0.25 +
        intel_confidence * 0.25 +
        network_confidence * 0.20,
        2
    )

    # Save report to database
    from services.db import save_report
    graph_json = json.dumps({
        "nodes": state.get("fraud_network_nodes", []),
        "edges": state.get("fraud_network_edges", []),
    })

    await save_report(case_id, {
        "report_markdown": report_markdown,
        "confidence_overall": confidence_overall,
        "scam_pattern": classification.get("pattern_name", "unknown") if classification else "unknown",
        "matched_advisory": classification.get("matched_advisory", "") if classification else "",
        "network_size": state.get("network_size", 0),
        "trail_status": state.get("trail_status", "unknown"),
        "graph_json": graph_json,
    })

    emit_agent_event(case_id, "report_generator", "completed", {
        "confidence_overall": confidence_overall,
    })

    return {
        "report_markdown": report_markdown,
        "confidence_overall": confidence_overall,
        "completed_agents": state.get("completed_agents", []) + ["report_generator"],
    }
