"""
UNMASKED — Synthetic Fraud Data Generator
==========================================
Generates ~500 fraud cases with realistic UPI fraud patterns.
Each case has 2-5 mule hops with proper timing, amounts, and edge cases.

Fraud Archetypes:
  1. OLX/Marketplace scam — victim pays for item, money chains through mules
  2. Fake refund scam — small amount sent "by mistake", victim returns more
  3. Investment/crypto pool — money aggregated from multiple victims
  4. KYC harvest — fake bank call, OTP stolen, money drained
  5. Job scam — registration/processing fees collected
  6. Loan app scam — fake loan app, upfront fees
  7. QR code scam — victim scans QR expecting to receive, but sends

Edge Cases Covered:
  - Circular transactions (A→B→C→A) — cycle detection test
  - Dead trails (cold accounts, no further hops)
  - Ultra-fast velocity (<60s between hops) — classic mule signal
  - Large networks (10+ connected accounts via shared mules)
  - Same mule appearing across multiple cases — syndicate pattern
  - Micro-transactions before big fraud — account testing pattern
  - Cash-out detection (amount drops >90% at final hop)
  - Mixed legitimate + fraud accounts in same network
  - Phone-number VPAs vs name-based VPAs vs merchant VPAs
  - Same-prefix VPA clusters (same operator runs multiple mules)

Usage:
  python generate_synthetic_data.py
  # Requires: DATABASE_URL env var or defaults to local postgres
"""

import os
import random
import uuid
import json
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional
from dataclasses import dataclass, field

import asyncpg

# ============================================================
# CONFIGURATION
# ============================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://unmasked:unmasked_dev@localhost:5432/unmasked"
)

TOTAL_CASES = 500
SHARED_MULE_POOL_SIZE = 60       # mules reused across cases (syndicate pattern)
LEGITIMATE_ACCOUNT_POOL = 100    # clean accounts mixed into networks

random.seed(42)  # reproducible generation

# ============================================================
# REALISTIC INDIAN UPI DATA
# ============================================================

# Real UPI handle suffixes mapped to banks
BANK_SUFFIXES = {
    "@ybl":       "PhonePe / Yes Bank",
    "@okaxis":    "Google Pay / Axis Bank",
    "@paytm":     "Paytm Payments Bank",
    "@ibl":       "ICICI Bank",
    "@axl":       "Axis Bank",
    "@sbi":       "State Bank of India",
    "@upi":       "BHIM / Multiple Banks",
    "@oksbi":     "Google Pay / SBI",
    "@okhdfcbank":"Google Pay / HDFC",
    "@okicici":   "Google Pay / ICICI",
    "@apl":       "Amazon Pay",
    "@fbl":       "Federal Bank",
    "@kotak":     "Kotak Mahindra Bank",
    "@boi":       "Bank of India",
    "@pnb":       "Punjab National Bank",
    "@indus":     "IndusInd Bank",
    "@rbl":       "RBL Bank",
    "@dbs":       "DBS Bank",
    "@jupiteraxis":"Jupiter / Axis Bank",
    "@slice":     "Slice / NSDL",
}

SUFFIX_LIST = list(BANK_SUFFIXES.keys())
MULE_PREFERRED_SUFFIXES = ["@ybl", "@paytm", "@okaxis", "@axl"]  # commonly exploited

# Common Indian first names (mix of Hindi, South Indian, Bengali, etc.)
FIRST_NAMES = [
    "rahul", "priya", "amit", "sneha", "vikram", "ananya", "rohit", "pooja",
    "arjun", "divya", "suresh", "neha", "karthik", "swati", "manish", "ritu",
    "deepak", "kavita", "sanjay", "meera", "rajesh", "anjali", "arun", "lakshmi",
    "nikhil", "shreya", "manoj", "pallavi", "gaurav", "nandini", "ashok", "sunita",
    "vivek", "rekha", "prakash", "geeta", "santosh", "usha", "dinesh", "sapna",
    "varun", "tanvi", "vishal", "sweta", "pankaj", "komal", "tushar", "aditi",
    "hemant", "jyoti", "naveen", "rashmi", "sachin", "bhavna", "yogesh", "ankita",
    "sunil", "preeti", "mukesh", "shilpa", "ramesh", "vandana", "ajay", "megha",
    "tarun", "seema", "pramod", "ritika", "hitesh", "monika", "kamal", "sonal",
    "vinay", "madhuri", "rakesh", "nisha", "umesh", "kriti", "mahesh", "chitra",
    "ravi", "anita", "gopal", "smita", "harsh", "puja", "lalit", "renuka",
    "madan", "veena", "chandan", "sudha", "jagdish", "radha", "kishore", "aarti",
    "mohammad", "fatima", "irfan", "zara", "imran", "ayesha", "salman", "noor",
]

LAST_NAMES = [
    "sharma", "patel", "kumar", "singh", "gupta", "reddy", "nair", "das",
    "joshi", "verma", "mishra", "iyer", "shah", "rao", "pandey", "menon",
    "chauhan", "mehta", "bhat", "pillai", "agarwal", "chopra", "saxena", "nayak",
    "thakur", "banerjee", "chatterjee", "mukherjee", "deshmukh", "patil",
    "kulkarni", "sawant", "shinde", "jadhav", "pawar", "deshpande", "yadav",
    "tiwari", "dubey", "srivastava", "tripathi", "awasthi", "bose", "sen",
    "ghosh", "roy", "dutta", "bhatt", "vyas", "trivedi", "dave", "parmar",
    "rathore", "solanki", "gill", "dhillon", "bajwa", "sandhu", "sidhu",
    "khan", "malik", "ansari", "qureshi", "syed", "sheikh",
]

# Scam archetypes with realistic parameters
SCAM_ARCHETYPES = {
    "olx_marketplace": {
        "name": "OLX/Marketplace Scam",
        "amount_range": (5000, 75000),
        "hops": (2, 4),
        "velocity_seconds": (120, 600),      # fast but not instant
        "amount_retention": (0.85, 0.95),     # mules keep 5-15% per hop
        "description": "Victim pays for item on marketplace, seller never delivers, money laundered through mule chain",
    },
    "fake_refund": {
        "name": "Fake Refund Scam",
        "amount_range": (2000, 30000),
        "hops": (2, 3),
        "velocity_seconds": (60, 300),        # very fast — urgency-based
        "amount_retention": (0.80, 0.90),
        "description": "Scammer sends small amount, claims mistake, victim returns larger amount via collect request",
    },
    "investment_pool": {
        "name": "Investment/Crypto Pool Scam",
        "amount_range": (25000, 500000),
        "hops": (3, 5),
        "velocity_seconds": (300, 1800),      # slightly slower — larger amounts
        "amount_retention": (0.90, 0.98),     # less skimmed per hop
        "description": "Promise of high returns, money aggregated then split across accounts for withdrawal",
    },
    "kyc_harvest": {
        "name": "KYC Phishing / OTP Theft",
        "amount_range": (10000, 200000),
        "hops": (2, 4),
        "velocity_seconds": (30, 180),        # fastest — before victim notices
        "amount_retention": (0.88, 0.95),
        "description": "Fake bank call harvests OTP, immediate unauthorized debit, rapid mule chain",
    },
    "job_scam": {
        "name": "Fake Job / Registration Fee Scam",
        "amount_range": (1000, 15000),
        "hops": (2, 3),
        "velocity_seconds": (300, 900),
        "amount_retention": (0.85, 0.92),
        "description": "Promise of job placement, registration/training fee collected, money moved through mules",
    },
    "loan_app": {
        "name": "Fake Loan App Scam",
        "amount_range": (3000, 50000),
        "hops": (2, 4),
        "velocity_seconds": (120, 600),
        "amount_retention": (0.82, 0.90),
        "description": "Fake loan app charges processing/insurance fees upfront, never disburses loan",
    },
    "qr_code": {
        "name": "QR Code Scam",
        "amount_range": (5000, 100000),
        "hops": (2, 3),
        "velocity_seconds": (60, 300),
        "amount_retention": (0.85, 0.95),
        "description": "Victim scans QR code expecting to receive money but actually authorizes a debit",
    },
}

# ============================================================
# VPA GENERATORS
# ============================================================

def random_suffix(prefer_mule: bool = False) -> str:
    if prefer_mule and random.random() < 0.7:
        return random.choice(MULE_PREFERRED_SUFFIXES)
    return random.choice(SUFFIX_LIST)


def generate_name_vpa(prefer_mule: bool = False) -> str:
    """name-based VPA: rahulsharma@ybl, priya.patel@okaxis"""
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    suffix = random_suffix(prefer_mule)

    patterns = [
        f"{first}{last}{suffix}",
        f"{first}.{last}{suffix}",
        f"{first}{last}{random.randint(1, 999)}{suffix}",
        f"{first[0]}{last}{suffix}",
        f"{first}_{last}{random.randint(10, 99)}{suffix}",
        f"{first}{random.randint(100, 9999)}{suffix}",
    ]
    return random.choice(patterns)


def generate_phone_vpa(prefer_mule: bool = False) -> str:
    """phone-based VPA: 9876543210@ybl"""
    prefix = random.choice(["6", "7", "8", "9"])
    number = prefix + "".join([str(random.randint(0, 9)) for _ in range(9)])
    suffix = random_suffix(prefer_mule)
    return f"{number}{suffix}"


def generate_merchant_vpa() -> str:
    """merchant VPA: shopname@axl"""
    merchants = [
        "quickmart", "fastshop", "dealzone", "megastore", "payeasy",
        "shopcity", "netbazaar", "flashdeal", "onlinehub", "smartpay",
        "trustshop", "safemart", "clickbuy", "easytrade", "webstore",
        "digitalmart", "paynow", "buymore", "tradesafe", "gooddeal",
    ]
    name = random.choice(merchants)
    num = random.randint(1, 999)
    suffix = random_suffix(False)
    return f"{name}{num}{suffix}"


def generate_random_vpa(prefer_mule: bool = False) -> str:
    """random-looking VPA common in disposable mule accounts: xk47m@paytm"""
    chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    length = random.randint(5, 8)
    handle = "".join(random.choice(chars) for _ in range(length))
    suffix = random_suffix(prefer_mule)
    return f"{handle}{suffix}"


def generate_mule_cluster_vpas(prefix: str, count: int) -> list[str]:
    """Same-prefix VPAs indicating same operator: rk_op01@ybl, rk_op02@ybl, rk_op03@ybl"""
    suffix = random.choice(MULE_PREFERRED_SUFFIXES)
    return [f"{prefix}{str(i).zfill(2)}{suffix}" for i in range(1, count + 1)]


def generate_vpa(vpa_type: str = "random", prefer_mule: bool = False) -> str:
    generators = {
        "personal": generate_name_vpa,
        "phone":    generate_phone_vpa,
        "merchant": generate_merchant_vpa,
        "random":   generate_random_vpa,
    }
    gen = generators.get(vpa_type, generate_name_vpa)
    if vpa_type == "merchant":
        return gen()
    return gen(prefer_mule)


def classify_vpa_type(vpa: str) -> str:
    handle = vpa.split("@")[0]
    if handle.isdigit() and len(handle) == 10:
        return "phone"
    if any(m in handle for m in ["mart", "shop", "store", "pay", "deal", "buy", "trade"]):
        return "merchant"
    if len(handle) <= 8 and sum(c.isdigit() for c in handle) > len(handle) * 0.4:
        return "random"
    return "personal"


def extract_bank(vpa: str) -> str:
    for suffix, bank in BANK_SUFFIXES.items():
        if vpa.endswith(suffix):
            return bank
    return "Unknown Bank"


def extract_naming_pattern(vpa: str) -> str:
    """Extract prefix pattern for clustering same-operator mules"""
    handle = vpa.split("@")[0]
    # Remove trailing digits
    prefix = handle.rstrip("0123456789")
    # Remove trailing separators
    prefix = prefix.rstrip("_.")
    return prefix if len(prefix) >= 2 else handle


# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class VPARecord:
    vpa: str
    registrar_bank: str
    account_age_days: int
    risk_score: float
    flags: list[str]
    vpa_type: str
    is_confirmed_fraud: bool = False
    total_cases_involved: int = 1
    naming_pattern: str = ""

    def __post_init__(self):
        if not self.naming_pattern:
            self.naming_pattern = extract_naming_pattern(self.vpa)


@dataclass
class TransactionHop:
    case_id: str
    sender_vpa: str
    receiver_vpa: str
    amount: float
    timestamp: datetime
    transaction_ref: str
    hop_number: int
    time_delta_seconds: Optional[int]
    amount_drop_pct: Optional[float]
    is_cash_out: bool
    receiver_bank: str


@dataclass
class FraudCase:
    case_id: str
    victim_vpa: str
    fraud_vpa: str
    amount: float
    transaction_ref: str
    archetype: str
    hops: list[TransactionHop] = field(default_factory=list)

# ============================================================
# SHARED MULE POOL — Syndicate Pattern
# ============================================================

def create_shared_mule_pool() -> list[VPARecord]:
    """
    Create a pool of mule accounts that will be reused across multiple cases.
    This simulates real-world syndicates operating the same mule network.
    """
    mules = []

    # Cluster 1: "rk_op" prefix — same operator, 8 accounts
    cluster1 = generate_mule_cluster_vpas("rk_op", 8)
    for vpa in cluster1:
        mules.append(VPARecord(
            vpa=vpa,
            registrar_bank=extract_bank(vpa),
            account_age_days=random.randint(1, 5),
            risk_score=round(random.uniform(0.7, 0.95), 2),
            flags=["cluster_detected", "rapid_turnover", "new_account"],
            vpa_type="random",
            is_confirmed_fraud=random.random() < 0.3,
        ))

    # Cluster 2: "sv_mule" prefix — 6 accounts
    cluster2 = generate_mule_cluster_vpas("sv_mule", 6)
    for vpa in cluster2:
        mules.append(VPARecord(
            vpa=vpa,
            registrar_bank=extract_bank(vpa),
            account_age_days=random.randint(2, 10),
            risk_score=round(random.uniform(0.6, 0.85), 2),
            flags=["cluster_detected", "high_velocity"],
            vpa_type="random",
        ))

    # Cluster 3: "quickcash" merchant fronts — 5 accounts
    cluster3_suffix = random.choice(MULE_PREFERRED_SUFFIXES)
    cluster3 = [f"quickcash{i}{cluster3_suffix}" for i in range(1, 6)]
    for vpa in cluster3:
        mules.append(VPARecord(
            vpa=vpa,
            registrar_bank=extract_bank(vpa),
            account_age_days=random.randint(15, 45),
            risk_score=round(random.uniform(0.5, 0.75), 2),
            flags=["merchant_front", "high_volume"],
            vpa_type="merchant",
        ))

    # Individual mules — varied types
    for _ in range(SHARED_MULE_POOL_SIZE - len(mules)):
        vpa_type = random.choice(["personal", "phone", "random", "random"])
        vpa = generate_vpa(vpa_type, prefer_mule=True)
        age = random.choices(
            [random.randint(1, 7), random.randint(8, 30), random.randint(31, 90)],
            weights=[0.5, 0.3, 0.2]
        )[0]
        mules.append(VPARecord(
            vpa=vpa,
            registrar_bank=extract_bank(vpa),
            account_age_days=age,
            risk_score=round(random.uniform(0.3, 0.9), 2),
            flags=random.sample(
                ["new_account", "high_velocity", "multiple_banks", "rapid_turnover",
                 "night_activity", "round_amounts", "no_incoming_legitimate"],
                k=random.randint(1, 3)
            ),
            vpa_type=vpa_type,
        ))

    return mules


def create_legitimate_pool() -> list[VPARecord]:
    """Legitimate accounts that appear in networks but aren't mules."""
    legit = []
    for _ in range(LEGITIMATE_ACCOUNT_POOL):
        vpa_type = random.choice(["personal", "personal", "phone", "merchant"])
        vpa = generate_vpa(vpa_type, prefer_mule=False)
        legit.append(VPARecord(
            vpa=vpa,
            registrar_bank=extract_bank(vpa),
            account_age_days=random.randint(180, 1800),
            risk_score=round(random.uniform(0.0, 0.15), 2),
            flags=[],
            vpa_type=vpa_type,
        ))
    return legit


# ============================================================
# CASE GENERATORS — One per Archetype
# ============================================================

def generate_transaction_ref() -> str:
    return f"TXN{uuid.uuid4().hex[:12].upper()}"


def generate_case(
    archetype_key: str,
    mule_pool: list[VPARecord],
    legit_pool: list[VPARecord],
    case_number: int,
) -> FraudCase:
    """Generate a single fraud case with realistic hop chain."""

    arch = SCAM_ARCHETYPES[archetype_key]
    case_id = str(uuid.uuid4())

    # Victim is always a legitimate-looking VPA
    victim_vpa = generate_vpa(
        random.choice(["personal", "phone"]),
        prefer_mule=False
    )

    # First fraud VPA — sometimes a shared mule, sometimes fresh
    if random.random() < 0.4:
        fraud_vpa_record = random.choice(mule_pool)
        fraud_vpa = fraud_vpa_record.vpa
    else:
        fraud_vpa = generate_vpa("personal", prefer_mule=True)

    amount = round(random.uniform(*arch["amount_range"]), 2)
    num_hops = random.randint(*arch["hops"])

    # Base timestamp: random time in last 90 days
    base_time = datetime.now(timezone.utc) - timedelta(
        days=random.randint(1, 90),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59)
    )

    case = FraudCase(
        case_id=case_id,
        victim_vpa=victim_vpa,
        fraud_vpa=fraud_vpa,
        amount=amount,
        transaction_ref=generate_transaction_ref(),
        archetype=archetype_key,
    )

    # Hop 0: victim → fraud_vpa
    case.hops.append(TransactionHop(
        case_id=case_id,
        sender_vpa=victim_vpa,
        receiver_vpa=fraud_vpa,
        amount=amount,
        timestamp=base_time,
        transaction_ref=case.transaction_ref,
        hop_number=0,
        time_delta_seconds=None,     # first hop has no delta
        amount_drop_pct=None,
        is_cash_out=False,
        receiver_bank=extract_bank(fraud_vpa),
    ))

    # Build mule chain
    current_sender = fraud_vpa
    current_amount = amount
    current_time = base_time

    for hop_num in range(1, num_hops + 1):
        # Time delta — velocity signature
        td = random.randint(*arch["velocity_seconds"])

        # Occasionally ultra-fast (<60s) — strong mule signal
        if random.random() < 0.15:
            td = random.randint(10, 59)

        current_time += timedelta(seconds=td)

        # Amount retention
        retention = random.uniform(*arch["amount_retention"])
        new_amount = round(current_amount * retention, 2)
        drop_pct = round((1 - retention) * 100, 2)

        # Last hop: possible cash-out (large drop)
        is_cash_out = False
        if hop_num == num_hops and random.random() < 0.6:
            new_amount = round(current_amount * random.uniform(0.02, 0.08), 2)
            drop_pct = round((1 - new_amount / current_amount) * 100, 2)
            is_cash_out = True

        # Pick receiver: shared mule (60%), fresh mule (30%), legit-looking (10%)
        roll = random.random()
        if roll < 0.6:
            receiver_record = random.choice(mule_pool)
            receiver_vpa = receiver_record.vpa
        elif roll < 0.9:
            receiver_vpa = generate_vpa(
                random.choice(["random", "phone"]),
                prefer_mule=True
            )
        else:
            receiver_record = random.choice(legit_pool)
            receiver_vpa = receiver_record.vpa

        # Avoid self-loops
        if receiver_vpa == current_sender:
            receiver_vpa = generate_vpa("random", prefer_mule=True)

        case.hops.append(TransactionHop(
            case_id=case_id,
            sender_vpa=current_sender,
            receiver_vpa=receiver_vpa,
            amount=new_amount,
            timestamp=current_time,
            transaction_ref=generate_transaction_ref(),
            hop_number=hop_num,
            time_delta_seconds=td,
            amount_drop_pct=drop_pct,
            is_cash_out=is_cash_out,
            receiver_bank=extract_bank(receiver_vpa),
        ))

        current_sender = receiver_vpa
        current_amount = new_amount

    return case


# ============================================================
# EDGE CASE GENERATORS
# ============================================================

def generate_circular_case(mule_pool: list[VPARecord]) -> FraudCase:
    """Edge case: A→B→C→A circular transaction — tests cycle detection"""
    case_id = str(uuid.uuid4())
    victim = generate_vpa("personal")
    vpas = [random.choice(mule_pool).vpa for _ in range(3)]

    base_time = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))
    amount = round(random.uniform(10000, 50000), 2)

    case = FraudCase(
        case_id=case_id,
        victim_vpa=victim,
        fraud_vpa=vpas[0],
        amount=amount,
        transaction_ref=generate_transaction_ref(),
        archetype="circular_laundering",
    )

    chain = [victim] + vpas + [vpas[0]]  # circular: back to first mule
    current_amount = amount
    current_time = base_time

    for i in range(len(chain) - 1):
        td = random.randint(60, 300) if i > 0 else None
        if td:
            current_time += timedelta(seconds=td)
        retention = random.uniform(0.90, 0.98)
        new_amount = round(current_amount * retention, 2) if i > 0 else amount

        case.hops.append(TransactionHop(
            case_id=case_id,
            sender_vpa=chain[i],
            receiver_vpa=chain[i + 1],
            amount=new_amount if i > 0 else amount,
            timestamp=current_time,
            transaction_ref=generate_transaction_ref(),
            hop_number=i,
            time_delta_seconds=td,
            amount_drop_pct=round((1 - retention) * 100, 2) if i > 0 else None,
            is_cash_out=False,
            receiver_bank=extract_bank(chain[i + 1]),
        ))
        current_amount = new_amount

    return case


def generate_dead_trail_case(mule_pool: list[VPARecord]) -> FraudCase:
    """Edge case: trail goes cold — receiver has no outgoing transactions"""
    case_id = str(uuid.uuid4())
    victim = generate_vpa("personal")
    fraud_vpa = random.choice(mule_pool).vpa
    amount = round(random.uniform(5000, 80000), 2)
    base_time = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 60))

    case = FraudCase(
        case_id=case_id,
        victim_vpa=victim,
        fraud_vpa=fraud_vpa,
        amount=amount,
        transaction_ref=generate_transaction_ref(),
        archetype="dead_trail",
    )

    # Only 1 hop — money disappears (withdrawn via ATM or account closed)
    case.hops.append(TransactionHop(
        case_id=case_id,
        sender_vpa=victim,
        receiver_vpa=fraud_vpa,
        amount=amount,
        timestamp=base_time,
        transaction_ref=case.transaction_ref,
        hop_number=0,
        time_delta_seconds=None,
        amount_drop_pct=None,
        is_cash_out=False,
        receiver_bank=extract_bank(fraud_vpa),
    ))

    # Dead end — money sent to a cold account with no further hops
    cold_account = generate_vpa("random", prefer_mule=True)
    case.hops.append(TransactionHop(
        case_id=case_id,
        sender_vpa=fraud_vpa,
        receiver_vpa=cold_account,
        amount=round(amount * 0.95, 2),
        timestamp=base_time + timedelta(seconds=random.randint(30, 120)),
        transaction_ref=generate_transaction_ref(),
        hop_number=1,
        time_delta_seconds=random.randint(30, 120),
        amount_drop_pct=5.0,
        is_cash_out=False,  # not confirmed as cash-out, just... gone
        receiver_bank=extract_bank(cold_account),
    ))

    return case


def generate_micro_test_case(mule_pool: list[VPARecord]) -> FraudCase:
    """Edge case: small test transactions before big fraud — account testing pattern"""
    case_id = str(uuid.uuid4())
    victim = generate_vpa("phone")
    fraud_vpa = random.choice(mule_pool).vpa
    big_amount = round(random.uniform(50000, 200000), 2)
    base_time = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 45))

    case = FraudCase(
        case_id=case_id,
        victim_vpa=victim,
        fraud_vpa=fraud_vpa,
        amount=big_amount,
        transaction_ref=generate_transaction_ref(),
        archetype="micro_test_then_drain",
    )

    # Micro test: ₹1 sent first
    case.hops.append(TransactionHop(
        case_id=case_id,
        sender_vpa=victim,
        receiver_vpa=fraud_vpa,
        amount=1.00,
        timestamp=base_time - timedelta(minutes=random.randint(5, 30)),
        transaction_ref=generate_transaction_ref(),
        hop_number=0,
        time_delta_seconds=None,
        amount_drop_pct=None,
        is_cash_out=False,
        receiver_bank=extract_bank(fraud_vpa),
    ))

    # Big transaction follows
    td = random.randint(300, 1800)
    case.hops.append(TransactionHop(
        case_id=case_id,
        sender_vpa=victim,
        receiver_vpa=fraud_vpa,
        amount=big_amount,
        timestamp=base_time,
        transaction_ref=case.transaction_ref,
        hop_number=1,
        time_delta_seconds=td,
        amount_drop_pct=None,
        is_cash_out=False,
        receiver_bank=extract_bank(fraud_vpa),
    ))

    # Rapid drain through mules
    current_sender = fraud_vpa
    current_amount = big_amount
    current_time = base_time

    for hop_num in range(2, 5):
        td = random.randint(15, 90)  # ultra-fast drain
        current_time += timedelta(seconds=td)
        retention = random.uniform(0.88, 0.95)
        new_amount = round(current_amount * retention, 2)

        receiver = random.choice(mule_pool).vpa
        if receiver == current_sender:
            receiver = generate_vpa("random", prefer_mule=True)

        case.hops.append(TransactionHop(
            case_id=case_id,
            sender_vpa=current_sender,
            receiver_vpa=receiver,
            amount=new_amount,
            timestamp=current_time,
            transaction_ref=generate_transaction_ref(),
            hop_number=hop_num,
            time_delta_seconds=td,
            amount_drop_pct=round((1 - retention) * 100, 2),
            is_cash_out=(hop_num == 4),
            receiver_bank=extract_bank(receiver),
        ))
        current_sender = receiver
        current_amount = new_amount

    return case


def generate_large_network_case(mule_pool: list[VPARecord]) -> FraudCase:
    """Edge case: fan-out pattern — money splits to 5+ accounts at once"""
    case_id = str(uuid.uuid4())
    victim = generate_vpa("personal")
    fraud_vpa = random.choice(mule_pool).vpa
    total_amount = round(random.uniform(100000, 500000), 2)
    base_time = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))

    case = FraudCase(
        case_id=case_id,
        victim_vpa=victim,
        fraud_vpa=fraud_vpa,
        amount=total_amount,
        transaction_ref=generate_transaction_ref(),
        archetype="investment_pool_fanout",
    )

    # Hop 0: victim → collector
    case.hops.append(TransactionHop(
        case_id=case_id,
        sender_vpa=victim,
        receiver_vpa=fraud_vpa,
        amount=total_amount,
        timestamp=base_time,
        transaction_ref=case.transaction_ref,
        hop_number=0,
        time_delta_seconds=None,
        amount_drop_pct=None,
        is_cash_out=False,
        receiver_bank=extract_bank(fraud_vpa),
    ))

    # Fan-out: split to 5-8 accounts
    fan_count = random.randint(5, 8)
    remaining = total_amount
    current_time = base_time

    for i in range(fan_count):
        td = random.randint(60, 300)
        current_time += timedelta(seconds=td)

        if i == fan_count - 1:
            split_amount = round(remaining, 2)
        else:
            split_amount = round(remaining * random.uniform(0.1, 0.3), 2)
            remaining -= split_amount

        receiver = random.choice(mule_pool).vpa
        if receiver == fraud_vpa:
            receiver = generate_vpa("random", prefer_mule=True)

        case.hops.append(TransactionHop(
            case_id=case_id,
            sender_vpa=fraud_vpa,
            receiver_vpa=receiver,
            amount=split_amount,
            timestamp=current_time,
            transaction_ref=generate_transaction_ref(),
            hop_number=1,
            time_delta_seconds=td,
            amount_drop_pct=None,
            is_cash_out=False,
            receiver_bank=extract_bank(receiver),
        ))

    return case


# ============================================================
# MAIN GENERATOR
# ============================================================

def generate_all_cases() -> tuple[list[FraudCase], list[VPARecord], list[VPARecord]]:
    """Generate all cases, mule pool, and legitimate accounts."""

    mule_pool = create_shared_mule_pool()
    legit_pool = create_legitimate_pool()

    cases = []
    archetype_keys = list(SCAM_ARCHETYPES.keys())

    # Regular cases: ~470
    regular_count = TOTAL_CASES - 30  # reserve 30 for edge cases
    for i in range(regular_count):
        arch = random.choice(archetype_keys)
        case = generate_case(arch, mule_pool, legit_pool, i)
        cases.append(case)

    # Edge cases: ~30
    for _ in range(8):
        cases.append(generate_circular_case(mule_pool))
    for _ in range(8):
        cases.append(generate_dead_trail_case(mule_pool))
    for _ in range(7):
        cases.append(generate_micro_test_case(mule_pool))
    for _ in range(7):
        cases.append(generate_large_network_case(mule_pool))

    random.shuffle(cases)

    # Update mule pool case counts based on actual usage
    vpa_case_count: dict[str, int] = {}
    for case in cases:
        seen_in_case: set[str] = set()
        for hop in case.hops:
            for vpa in [hop.sender_vpa, hop.receiver_vpa]:
                if vpa not in seen_in_case:
                    vpa_case_count[vpa] = vpa_case_count.get(vpa, 0) + 1
                    seen_in_case.add(vpa)

    for mule in mule_pool:
        mule.total_cases_involved = vpa_case_count.get(mule.vpa, 1)

    return cases, mule_pool, legit_pool


# ============================================================
# DATABASE INSERTION
# ============================================================

async def insert_all(
    cases: list[FraudCase],
    mule_pool: list[VPARecord],
    legit_pool: list[VPARecord],
):
    conn = await asyncpg.connect(DATABASE_URL)

    try:
        # Insert VPA registry — mules
        print(f"Inserting {len(mule_pool)} mule VPAs...")
        for m in mule_pool:
            await conn.execute("""
                INSERT INTO vpa_registry
                    (vpa, registrar_bank, account_age_days, risk_score, flags,
                     vpa_type, naming_pattern, is_confirmed_fraud, total_cases_involved)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                ON CONFLICT (vpa) DO UPDATE SET
                    risk_score = GREATEST(vpa_registry.risk_score, $4),
                    total_cases_involved = $9
            """,
                m.vpa, m.registrar_bank, m.account_age_days, m.risk_score,
                m.flags, m.vpa_type, m.naming_pattern, m.is_confirmed_fraud,
                m.total_cases_involved,
            )

        # Insert VPA registry — legitimate accounts
        print(f"Inserting {len(legit_pool)} legitimate VPAs...")
        for l in legit_pool:
            await conn.execute("""
                INSERT INTO vpa_registry
                    (vpa, registrar_bank, account_age_days, risk_score, flags,
                     vpa_type, naming_pattern)
                VALUES ($1,$2,$3,$4,$5,$6,$7)
                ON CONFLICT (vpa) DO NOTHING
            """,
                l.vpa, l.registrar_bank, l.account_age_days, l.risk_score,
                l.flags, l.vpa_type, l.naming_pattern,
            )

        # Insert cases + transactions
        print(f"Inserting {len(cases)} fraud cases with transactions...")
        for i, case in enumerate(cases):
            # Insert case
            await conn.execute("""
                INSERT INTO cases (case_id, victim_vpa, fraud_vpa, amount,
                                   transaction_ref, status, created_at, completed_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
            """,
                uuid.UUID(case.case_id),
                case.victim_vpa,
                case.fraud_vpa,
                case.amount,
                case.transaction_ref,
                "complete",
                case.hops[0].timestamp - timedelta(minutes=random.randint(1, 10)),
                case.hops[-1].timestamp + timedelta(minutes=random.randint(1, 5)),
            )

            # Insert all hops
            for hop in case.hops:
                await conn.execute("""
                    INSERT INTO transactions
                        (case_id, sender_vpa, receiver_vpa, amount, timestamp,
                         transaction_ref, hop_number, time_delta_seconds,
                         amount_drop_pct, is_cash_out, receiver_bank)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                """,
                    uuid.UUID(hop.case_id),
                    hop.sender_vpa,
                    hop.receiver_vpa,
                    hop.amount,
                    hop.timestamp,
                    hop.transaction_ref,
                    hop.hop_number,
                    hop.time_delta_seconds,
                    hop.amount_drop_pct,
                    hop.is_cash_out,
                    hop.receiver_bank,
                )

                # Upsert VPA registry for every VPA we encounter
                for vpa in [hop.sender_vpa, hop.receiver_vpa]:
                    await conn.execute("""
                        INSERT INTO vpa_registry (vpa, registrar_bank, vpa_type, naming_pattern)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (vpa) DO UPDATE SET
                            last_seen_at = NOW(),
                            total_cases_involved = vpa_registry.total_cases_involved + 1
                    """,
                        vpa, extract_bank(vpa), classify_vpa_type(vpa),
                        extract_naming_pattern(vpa),
                    )

            if (i + 1) % 50 == 0:
                print(f"  ... {i + 1}/{len(cases)} cases inserted")

        # Print summary stats
        total_hops = sum(len(c.hops) for c in cases)
        archetype_counts: dict[str, int] = {}
        for c in cases:
            archetype_counts[c.archetype] = archetype_counts.get(c.archetype, 0) + 1

        print(f"\n{'='*60}")
        print(f"SYNTHETIC DATA GENERATION COMPLETE")
        print(f"{'='*60}")
        print(f"Total cases:        {len(cases)}")
        print(f"Total transactions: {total_hops}")
        print(f"Shared mule pool:   {len(mule_pool)}")
        print(f"Legitimate pool:    {len(legit_pool)}")
        print(f"\nArchetype breakdown:")
        for arch, count in sorted(archetype_counts.items(), key=lambda x: -x[1]):
            print(f"  {arch:30s} {count:4d}")

    finally:
        await conn.close()


# ============================================================
# ENTRY POINT
# ============================================================

async def main():
    print("UNMASKED — Synthetic Fraud Data Generator")
    print("=" * 60)
    print(f"Target: {TOTAL_CASES} cases")
    print(f"Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")
    print()

    cases, mule_pool, legit_pool = generate_all_cases()
    await insert_all(cases, mule_pool, legit_pool)


if __name__ == "__main__":
    asyncio.run(main())
