"""
UNMASKED — RAG Knowledge Base Seeder
=====================================
Seeds the knowledge_base table with fraud pattern descriptions,
RBI/NPCI advisory summaries, IT Act sections, and investigation
procedures.

These are factual descriptions of publicly documented scam patterns
and regulatory guidance, written as chunked knowledge for RAG retrieval.

Usage:
  python seed_knowledge_base.py
  # Requires: OPENAI_API_KEY and DATABASE_URL env vars
"""

import os
import json
import asyncio
import uuid
from typing import Optional

import asyncpg
from openai import OpenAI

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://unmasked:unmasked_dev@localhost:5432/unmasked"
)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

# ============================================================
# KNOWLEDGE BASE ENTRIES
# ============================================================
# Each entry is a self-contained chunk (~300-500 tokens) optimized
# for RAG retrieval. Categories: scam_pattern, advisory, legal, procedure

KNOWLEDGE_ENTRIES = [
    # ─── SCAM PATTERNS ───────────────────────────────────────
    {
        "source": "NPCI UPI Fraud Advisory 2024",
        "category": "scam_pattern",
        "metadata": {
            "pattern_name": "OLX/Marketplace Buyer Scam",
            "severity": "high",
            "evidence_points": [
                "Item listed at below-market price",
                "Seller insists on UPI payment before shipping",
                "VPA created within last 7 days",
                "Money forwarded to 2-4 accounts within minutes",
                "Final account shows ATM cash withdrawal"
            ]
        },
        "content": (
            "OLX and marketplace buyer scam pattern: A fraudster lists an item "
            "(typically electronics, vehicles, or furniture) at an attractive below-market "
            "price on OLX, Facebook Marketplace, or similar platforms. The victim is asked "
            "to pay via UPI before delivery. Once paid, the fraudster immediately forwards "
            "the money through a chain of 2-4 mule accounts. Key indicators include: the "
            "seller's UPI account is less than 7 days old, money moves through the chain "
            "in under 10 minutes per hop, amounts decrease by 5-15% at each hop (mule "
            "commission), and the final recipient withdraws cash via ATM within 30 minutes. "
            "The seller's account is typically abandoned after 1-3 transactions. Common VPA "
            "patterns show random alphanumeric handles on PhonePe or Paytm."
        ),
    },
    {
        "source": "RBI Circular on Digital Payment Fraud 2023",
        "category": "scam_pattern",
        "metadata": {
            "pattern_name": "Fake Refund / Wrong Transfer Scam",
            "severity": "medium",
            "evidence_points": [
                "Small initial credit to victim's account",
                "Phone call claiming accidental transfer",
                "Request to return money via UPI collect",
                "Returned amount exceeds received amount",
                "Original credit was from a stolen account"
            ]
        },
        "content": (
            "Fake refund or wrong transfer scam pattern: The fraudster sends a small "
            "amount (typically Rs 500-2000) to the victim's UPI account, then calls "
            "claiming it was sent by mistake and requests the money back. The victim "
            "is asked to send a larger amount back (claiming the original was split "
            "across transactions) or is sent a UPI collect request for a higher amount. "
            "The initial money sent to the victim often comes from another victim's "
            "stolen account. Key signals: the time between receiving money and the "
            "phone call is under 5 minutes, the caller creates urgency and emotional "
            "pressure, the return amount requested exceeds what was received, and "
            "the VPA requesting the return is different from the one that sent the money."
        ),
    },
    {
        "source": "Cybercrime.gov.in Scam Database 2024",
        "category": "scam_pattern",
        "metadata": {
            "pattern_name": "Investment / Crypto Pool Scam",
            "severity": "critical",
            "evidence_points": [
                "Promise of 30-100% returns",
                "Money collected into aggregator account",
                "Multiple victims paying into same VPA",
                "Aggregator splits to 5+ withdrawal accounts",
                "Fake trading platform screenshots shared via WhatsApp"
            ]
        },
        "content": (
            "Investment and cryptocurrency pool scam pattern: Victims are recruited "
            "via WhatsApp groups, Telegram channels, or social media ads promising "
            "guaranteed high returns (30-100% monthly) through stock trading, crypto "
            "trading, or forex. Victims are asked to send money via UPI to an 'investment "
            "account'. Initial small investments may receive actual returns to build trust "
            "(Ponzi structure). When larger amounts are deposited, money is aggregated in "
            "a collector account and then split (fan-out pattern) to 5-8 withdrawal accounts. "
            "Key indicators: multiple unrelated victims paying the same VPA, collector account "
            "has very high inflow volume over a short period, fan-out happens within 1-2 hours "
            "of collection, withdrawal accounts are newly created with no prior legitimate "
            "transaction history, and amounts are often round numbers (Rs 25000, 50000, 100000)."
        ),
    },
    {
        "source": "RBI Advisory on Vishing Attacks 2024",
        "category": "scam_pattern",
        "metadata": {
            "pattern_name": "KYC Phishing / OTP Theft",
            "severity": "critical",
            "evidence_points": [
                "Call claiming to be from bank/RBI",
                "Request for OTP or UPI PIN",
                "Unauthorized transaction within seconds",
                "Multiple rapid debits in succession",
                "Money moves to 2-4 accounts in under 3 minutes"
            ]
        },
        "content": (
            "KYC phishing and OTP theft scam pattern: The fraudster calls the victim "
            "impersonating a bank official, RBI representative, or telecom company. "
            "The caller claims the victim's KYC is expiring, account will be blocked, "
            "or SIM will be deactivated. Under this pretext, they extract the victim's "
            "UPI PIN or OTP. Once obtained, unauthorized transactions are executed "
            "immediately — often within 10-30 seconds. This is the fastest scam type: "
            "money typically moves through 2-4 mule accounts in under 3 minutes total. "
            "Key signals: transaction initiated from a device not previously associated "
            "with the victim's UPI account, multiple debits in rapid succession (draining "
            "the account in increments just below daily limits), time deltas between hops "
            "consistently under 60 seconds, and the first mule account was created within "
            "the last 48 hours."
        ),
    },
    {
        "source": "Cybercrime.gov.in Advisory 2024",
        "category": "scam_pattern",
        "metadata": {
            "pattern_name": "Fake Job / Registration Fee Scam",
            "severity": "medium",
            "evidence_points": [
                "Job posting on social media or messaging apps",
                "Registration or processing fee demanded",
                "Company name doesn't match any registered entity",
                "Same collector VPA used across multiple victims",
                "Amounts typically Rs 1000-15000"
            ]
        },
        "content": (
            "Fake job and registration fee scam pattern: Fraudsters post job openings "
            "for well-known companies on social media, WhatsApp groups, or fake websites. "
            "Victims are asked to pay a registration fee, training fee, or 'refundable "
            "security deposit' via UPI. The amounts are relatively small (Rs 1000-15000) "
            "to keep each transaction below scrutiny thresholds. Key indicators: the same "
            "collector VPA receives payments from many different accounts over days or weeks, "
            "the VPA does not belong to any registered merchant, the company name in "
            "communications doesn't match MCA records, and money from the collector "
            "is moved in batches every 2-3 days to withdrawal accounts."
        ),
    },
    {
        "source": "RBI Warning on Digital Lending Apps 2023",
        "category": "scam_pattern",
        "metadata": {
            "pattern_name": "Fake Loan App Scam",
            "severity": "high",
            "evidence_points": [
                "Unregistered lending app on Play Store",
                "Processing fee collected before loan disbursement",
                "Loan never actually disbursed",
                "Multiple fee collections: processing, insurance, GST",
                "Collector VPA changes frequently"
            ]
        },
        "content": (
            "Fake loan app scam pattern: Fraudulent lending applications are distributed "
            "via Google Play Store, APK files, or social media links. They promise instant "
            "loans with minimal documentation. Once the victim applies, they are asked to "
            "pay a 'processing fee', then an 'insurance fee', then 'GST charges' — each "
            "via UPI. The loan is never disbursed. Amounts range from Rs 3000-50000 across "
            "multiple fee collections. Key indicators: the lending app is not registered "
            "with RBI as an NBFC, the collector VPA rotates (changes every few days to "
            "avoid detection), fees are collected in stages to extract maximum money, "
            "and the app requests excessive device permissions (contacts, gallery, SMS) "
            "which are later used for harassment and blackmail if the victim complains."
        ),
    },
    {
        "source": "NPCI Merchant Fraud Advisory 2024",
        "category": "scam_pattern",
        "metadata": {
            "pattern_name": "QR Code Scam",
            "severity": "high",
            "evidence_points": [
                "Victim shown QR code 'to receive money'",
                "QR actually triggers a debit (collect request)",
                "Scammer poses as buyer on marketplace",
                "Transaction happens during phone call (social engineering)",
                "Money immediately forwarded to mule chain"
            ]
        },
        "content": (
            "QR code payment scam pattern: The fraudster contacts the victim (often "
            "as a buyer on OLX or a customer service agent) and sends a QR code claiming "
            "it will credit money to the victim's account. Scanning the QR code actually "
            "initiates a debit (UPI collect request). The victim enters their PIN thinking "
            "they are confirming a credit, but money is debited instead. Key indicators: "
            "the transaction occurs during an active phone call (scammer keeps victim "
            "on the line to prevent them from reading the screen carefully), the debit "
            "amount matches a previously discussed sale price, money is forwarded to "
            "mule accounts within 2-5 minutes, and the scammer's VPA is typically "
            "name-based to appear legitimate."
        ),
    },
    {
        "source": "I4C Analysis Report 2024",
        "category": "scam_pattern",
        "metadata": {
            "pattern_name": "Mule Account Network Pattern",
            "severity": "critical",
            "evidence_points": [
                "Multiple accounts opened within same week",
                "Same naming prefix pattern across accounts",
                "Accounts registered at same bank branch",
                "No legitimate transaction history",
                "Used as intermediate hops for 3+ fraud cases"
            ]
        },
        "content": (
            "Mule account network identification pattern: Professional fraud syndicates "
            "maintain networks of 10-50 mule accounts used to launder money from multiple "
            "fraud operations. Key identification signals: accounts share naming patterns "
            "(same prefix with sequential numbering like rk01, rk02, rk03), all accounts "
            "opened within the same 1-2 week period, registered via the same bank or "
            "payment platform, zero legitimate transaction history before fraud involvement, "
            "account holders are often unaware their identity was used (identity theft or "
            "rented accounts). Network behavior: each mule is used for 3-7 days then "
            "abandoned, money never stays in any account for more than 30 minutes, "
            "time deltas between hops are consistently under 10 minutes, and total "
            "throughput per mule account is typically Rs 5-20 lakh before abandonment."
        ),
    },

    # ─── REGULATORY ADVISORIES ────────────────────────────────
    {
        "source": "RBI Master Direction on Digital Payment Security 2024",
        "category": "advisory",
        "metadata": {
            "pattern_name": "RBI Zero Liability Framework",
            "severity": "info",
            "evidence_points": [
                "Customer not liable for unauthorized electronic transactions if reported within 3 days",
                "Bank must credit amount within 10 days of complaint",
                "Liability shifts to bank if fraud due to third-party breach"
            ]
        },
        "content": (
            "RBI's zero liability and limited liability framework for unauthorized "
            "electronic banking transactions: If a customer reports an unauthorized "
            "transaction within 3 working days, the customer bears zero liability and "
            "the bank must reverse the amount within 10 working days. If reported between "
            "4-7 working days, the customer liability is capped at Rs 10,000 for basic "
            "savings accounts and Rs 25,000 for other accounts. Beyond 7 days, the bank's "
            "board-approved policy determines liability. The burden of proof is on the bank "
            "to show the transaction was authorized. This framework is critical for fraud "
            "investigations because it creates a time-sensitive imperative: the faster an "
            "investigation produces evidence, the stronger the victim's claim for reversal. "
            "Banks must also report all fraud cases to RBI within 21 days."
        ),
    },
    {
        "source": "NPCI UPI Dispute Resolution Framework 2024",
        "category": "advisory",
        "metadata": {
            "pattern_name": "UPI Dispute Resolution TAT",
            "severity": "info",
            "evidence_points": [
                "Remitter bank must acknowledge complaint within 24 hours",
                "Beneficiary bank must respond within 5 days",
                "NPCI escalation available after 15 days",
                "Ombudsman route available after 30 days"
            ]
        },
        "content": (
            "NPCI UPI Dispute Resolution mechanism and timelines: When a UPI fraud "
            "complaint is filed, the remitter bank (victim's bank) must acknowledge "
            "within 24 hours and initiate a chargeback to the beneficiary bank (fraudster's "
            "bank). The beneficiary bank has 5 working days to respond with evidence. "
            "If unresolved, the case escalates to NPCI's dispute resolution system after "
            "15 days. If still unresolved after 30 days, the victim can approach the "
            "Banking Ombudsman. Critical timeline: money in the fraudster's account can "
            "be frozen by the beneficiary bank only if reported quickly — most mule "
            "accounts are emptied within 30 minutes of receiving funds. An automated "
            "investigation that maps the mule chain in minutes gives law enforcement "
            "the best chance of issuing freeze orders before cash-out."
        ),
    },
    {
        "source": "DPDP Act 2023 — Fraud Investigation Implications",
        "category": "advisory",
        "metadata": {
            "pattern_name": "DPDP Act Data Processing",
            "severity": "info",
            "evidence_points": [
                "Lawful processing allowed for law enforcement purposes",
                "Data fiduciary must report breaches to DPBI",
                "Consent not required for fraud prevention"
            ]
        },
        "content": (
            "Digital Personal Data Protection Act 2023 implications for UPI fraud "
            "investigation: Section 7 allows processing of personal data without explicit "
            "consent when it is necessary for compliance with law or for fraud prevention. "
            "This means investigation tools that analyze transaction patterns and VPA "
            "metadata do not require individual consent when operating under a legal "
            "authority (police FIR, bank fraud operations team, or CERT-In directive). "
            "However, any investigation tool must implement data minimization — only "
            "process data directly relevant to the fraud trail. Retention limits apply: "
            "investigation data should be purged once the case is resolved unless required "
            "for ongoing legal proceedings. The DPDP Act also requires data fiduciaries "
            "(banks) to report data breaches to the Data Protection Board of India."
        ),
    },
    {
        "source": "BNSS 2024 — e-FIR and Digital Evidence",
        "category": "advisory",
        "metadata": {
            "pattern_name": "BNSS 2024 e-FIR Provisions",
            "severity": "info",
            "evidence_points": [
                "Zero FIR can be filed at any police station",
                "e-FIR allowed for certain offenses",
                "Digital evidence admissible under Section 63 BSA",
                "Electronic records as primary evidence"
            ]
        },
        "content": (
            "Bharatiya Nagarik Suraksha Sanhita 2024 provisions relevant to cyber fraud: "
            "Zero FIR can now be filed at any police station regardless of jurisdiction, "
            "which is critical for UPI fraud where victim, fraudster, and mule accounts "
            "may be in different states. e-FIR (electronic First Information Report) is "
            "allowed for offenses where punishment is up to 3 years. Digital evidence "
            "including transaction logs, VPA metadata, and automated investigation reports "
            "is admissible under Section 63 of the Bharatiya Sakshya Adhiniyam (Indian "
            "Evidence Act replacement). For fraud investigation tools, this means: "
            "generated reports should include hash verification of source data, clear "
            "chain of custody for digital evidence, timestamp authentication, and "
            "separation of verified facts from algorithmic inferences."
        ),
    },

    # ─── IT ACT SECTIONS ──────────────────────────────────────
    {
        "source": "Information Technology Act 2000 — Relevant Sections for UPI Fraud",
        "category": "legal",
        "metadata": {
            "pattern_name": "IT Act Sections for UPI Fraud",
            "severity": "info",
            "evidence_points": [
                "Section 43 — Unauthorized access to computer system",
                "Section 66 — Computer related offences (3 years + fine)",
                "Section 66C — Identity theft (3 years + Rs 1 lakh)",
                "Section 66D — Cheating by personation using computer (3 years + Rs 1 lakh)",
                "Section 43A — Compensation for failure to protect data"
            ]
        },
        "content": (
            "Information Technology Act 2000 sections applicable to UPI fraud cases: "
            "Section 66 covers computer-related offences including unauthorized access "
            "to payment systems, punishable by up to 3 years imprisonment and fine. "
            "Section 66C specifically addresses identity theft — using another person's "
            "identity credentials (UPI PIN, OTP) — with penalty of 3 years and Rs 1 lakh "
            "fine. Section 66D covers cheating by personation using computer resources, "
            "applicable when scammers impersonate bank officials or create fake merchant "
            "identities. Section 43 provides civil remedies for unauthorized access. "
            "Section 43A mandates compensation from entities that fail to implement "
            "reasonable security practices leading to data breach. For investigation "
            "reports, citing the specific applicable sections strengthens the FIR filing."
        ),
    },
    {
        "source": "Indian Penal Code / BNS Sections for Financial Fraud",
        "category": "legal",
        "metadata": {
            "pattern_name": "IPC/BNS Sections for Financial Fraud",
            "severity": "info",
            "evidence_points": [
                "Section 420 IPC / 318 BNS — Cheating and dishonestly inducing delivery",
                "Section 468 IPC / 336 BNS — Forgery for purpose of cheating",
                "Section 471 IPC / 338 BNS — Using forged document as genuine",
                "Section 120B IPC / 61 BNS — Criminal conspiracy"
            ]
        },
        "content": (
            "Indian Penal Code (and equivalent Bharatiya Nyaya Sanhita 2023) sections "
            "for UPI fraud: Section 420 IPC (318 BNS) — cheating and dishonestly inducing "
            "delivery of property, the primary section for all UPI scams, punishable up to "
            "7 years. Section 468 IPC (336 BNS) — forgery for purpose of cheating, applicable "
            "when fake documents or identities are used. Section 120B IPC (61 BNS) — criminal "
            "conspiracy, applicable when mule networks are operated by organized syndicates. "
            "For investigation reports, the presence of multiple coordinated mule accounts "
            "strengthens the conspiracy charge. Evidence of pre-planning (accounts opened "
            "days before the fraud) supports establishing criminal intent."
        ),
    },

    # ─── INVESTIGATION PROCEDURES ─────────────────────────────
    {
        "source": "I4C Standard Operating Procedure for Cyber Fraud",
        "category": "procedure",
        "metadata": {
            "pattern_name": "Golden Hour Response",
            "severity": "critical",
            "evidence_points": [
                "First 1-2 hours are critical for fund freezing",
                "1930 helpline initiates immediate account freeze",
                "Banks must freeze suspected accounts within 2 hours of LEA request",
                "Evidence preservation must begin immediately"
            ]
        },
        "content": (
            "Indian Cyber Crime Coordination Centre (I4C) golden hour response protocol: "
            "The first 1-2 hours after a UPI fraud are critical because most mule accounts "
            "are emptied within 30-60 minutes. The 1930 cyber crime helpline can initiate "
            "an immediate account freeze request to the beneficiary bank. Banks are required "
            "to freeze suspected accounts within 2 hours of receiving a law enforcement "
            "agency (LEA) request. For this to work, the investigation must identify the "
            "mule chain quickly. A manual investigation typically takes days to map even "
            "the first hop. Automated investigation tools that map the complete chain in "
            "minutes enable freeze orders to be issued while money is still in transit. "
            "Evidence preservation: transaction logs, VPA registration data, IP addresses "
            "of UPI app sessions, and device fingerprints must be preserved by the bank "
            "for at least 5 years under RBI guidelines."
        ),
    },
    {
        "source": "Cyber Cell Investigation Workflow",
        "category": "procedure",
        "metadata": {
            "pattern_name": "FIR Filing Requirements for UPI Fraud",
            "severity": "high",
            "evidence_points": [
                "Transaction receipts or UPI app screenshots",
                "Complete chain of VPAs involved",
                "Timeline of transactions with amounts",
                "Bank statement showing debit",
                "Communication evidence (call records, chat screenshots)"
            ]
        },
        "content": (
            "Standard FIR filing requirements for UPI fraud cases at cyber crime cells: "
            "A complete FIR package must include: the victim's bank statement showing "
            "the unauthorized debit(s), UPI transaction ID and reference numbers, the "
            "fraud VPA and any intermediate VPAs in the mule chain, timeline of all "
            "transactions with exact amounts and timestamps, any communication evidence "
            "(call recordings, WhatsApp chats, SMS messages), and the victim's statement "
            "describing how the fraud occurred. Investigation dossiers that automatically "
            "map the transaction chain, identify mule patterns, classify the scam type, "
            "and cite applicable legal sections significantly accelerate the FIR process. "
            "Without automated investigation, a single UPI fraud case can take 3-6 months "
            "for the cyber cell to manually trace through bank correspondence."
        ),
    },

    # ─── MULE BEHAVIOR SIGNALS ────────────────────────────────
    {
        "source": "Financial Intelligence Unit Analysis 2024",
        "category": "scam_pattern",
        "metadata": {
            "pattern_name": "Mule Account Velocity Signals",
            "severity": "high",
            "evidence_points": [
                "Time between receiving and forwarding < 10 minutes",
                "No legitimate incoming transactions",
                "Account age < 30 days at time of fraud",
                "Multiple rapid outgoing transactions to different VPAs",
                "Total account lifetime < 2 weeks"
            ]
        },
        "content": (
            "Mule account velocity and behavioral signals: The strongest mule indicator "
            "is the time delta between receiving and forwarding funds. Legitimate accounts "
            "hold received funds for hours to days. Mule accounts forward within 1-10 "
            "minutes. A time delta under 600 seconds (10 minutes) combined with an account "
            "age under 30 days gives a mule confidence score above 0.7 in most scoring "
            "models. Additional signals: the account has zero or near-zero balance before "
            "the fraud transaction, no prior incoming transactions from employers or "
            "family, multiple outgoing transactions within minutes of each other (fan-out "
            "pattern), and the UPI handle uses random characters rather than a real name. "
            "Sophisticated syndicates may use 'seasoned' mule accounts that have 2-3 months "
            "of simulated legitimate activity before being activated for fraud."
        ),
    },
    {
        "source": "NPCI Transaction Monitoring Advisory 2024",
        "category": "scam_pattern",
        "metadata": {
            "pattern_name": "Cash-Out Detection Signals",
            "severity": "high",
            "evidence_points": [
                "Amount drops more than 90% at final hop",
                "Final recipient is a merchant or ATM-linked account",
                "Transaction occurs at odd hours (2-5 AM)",
                "Final amount is a round number near ATM withdrawal limit"
            ]
        },
        "content": (
            "Cash-out detection at the end of a mule chain: The terminal node in a "
            "fraud network typically shows distinctive patterns. The amount retained "
            "at the final hop drops dramatically (more than 90% reduction from the "
            "previous hop), indicating the remaining money has been converted to cash "
            "or goods. Common cash-out methods: ATM withdrawal (amounts near Rs 10000 "
            "or Rs 20000 increments matching ATM limits), merchant purchase of easily "
            "resellable goods (gift cards, electronics), or transfer to a crypto "
            "exchange account. Key timing signal: cash-outs frequently occur between "
            "2-5 AM when monitoring is lowest. The final mule account is almost always "
            "abandoned immediately after cash-out — no subsequent transactions appear."
        ),
    },
]


# ============================================================
# EMBEDDING + INSERTION
# ============================================================

async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings using OpenAI text-embedding-3-small"""
    if not OPENAI_API_KEY:
        print("WARNING: No OPENAI_API_KEY set. Generating zero vectors as placeholders.")
        print("  Re-run with OPENAI_API_KEY to generate real embeddings.")
        return [[0.0] * EMBEDDING_DIM for _ in texts]

    client = OpenAI(api_key=OPENAI_API_KEY)
    embeddings = []

    # Batch in groups of 20 (API limit is higher but this is safe)
    batch_size = 20
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
        )
        for item in response.data:
            embeddings.append(item.embedding)
        print(f"  Embedded {min(i + batch_size, len(texts))}/{len(texts)} entries")

    return embeddings


async def seed_knowledge_base():
    """Insert all knowledge base entries with embeddings into PostgreSQL."""

    print("UNMASKED — RAG Knowledge Base Seeder")
    print("=" * 60)
    print(f"Entries to seed: {len(KNOWLEDGE_ENTRIES)}")
    print()

    # Generate embeddings for all content
    print("Generating embeddings...")
    texts = [entry["content"] for entry in KNOWLEDGE_ENTRIES]
    embeddings = await generate_embeddings(texts)

    # Insert into database
    print("Connecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)

    try:
        # Clear existing knowledge base (idempotent re-seeding)
        await conn.execute("DELETE FROM knowledge_base")
        print("Cleared existing knowledge base entries.")

        print("Inserting entries...")
        for i, (entry, embedding) in enumerate(zip(KNOWLEDGE_ENTRIES, embeddings)):
            # pgvector expects a string representation of the vector
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

            await conn.execute("""
                INSERT INTO knowledge_base (id, source, content, embedding, metadata, category)
                VALUES ($1, $2, $3, $4::vector, $5::jsonb, $6)
            """,
                uuid.uuid4(),
                entry["source"],
                entry["content"],
                embedding_str,
                json.dumps(entry["metadata"]),
                entry["category"],
            )

        print(f"\n{'='*60}")
        print(f"KNOWLEDGE BASE SEEDING COMPLETE")
        print(f"{'='*60}")

        # Summary by category
        rows = await conn.fetch("""
            SELECT category, COUNT(*) as cnt
            FROM knowledge_base
            GROUP BY category
            ORDER BY cnt DESC
        """)
        print("Entries by category:")
        for row in rows:
            print(f"  {row['category']:20s} {row['cnt']:3d}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed_knowledge_base())
