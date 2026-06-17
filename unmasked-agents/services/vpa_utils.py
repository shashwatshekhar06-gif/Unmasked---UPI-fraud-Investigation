BANK_SUFFIX_MAP = {
    "@ybl": "PhonePe / Yes Bank",
    "@okaxis": "Google Pay / Axis Bank",
    "@paytm": "Paytm Payments Bank",
    "@ibl": "ICICI Bank",
    "@axl": "Axis Bank",
    "@sbi": "State Bank of India",
    "@upi": "BHIM / Multiple Banks",
    "@oksbi": "Google Pay / SBI",
    "@okhdfcbank": "Google Pay / HDFC",
    "@okicici": "Google Pay / ICICI",
    "@apl": "Amazon Pay",
    "@fbl": "Federal Bank",
    "@kotak": "Kotak Mahindra Bank",
    "@boi": "Bank of India",
    "@pnb": "Punjab National Bank",
    "@indus": "IndusInd Bank",
    "@rbl": "RBL Bank",
    "@dbs": "DBS Bank",
    "@jupiteraxis": "Jupiter / Axis Bank",
    "@slice": "Slice / NSDL",
}


def extract_bank(vpa: str) -> str:
    for suffix, bank in BANK_SUFFIX_MAP.items():
        if vpa.endswith(suffix):
            return bank
    return "Unknown Bank"


def compute_mule_confidence(
    account_age_days: int | None,
    total_cases: int,
    existing_risk: float
) -> float:
    """
    DSA: Weighted scoring function for mule classification.
    Each signal contributes a weighted score. Final score capped at 1.0.
    """
    score = 0.0

    # Factor 1: Account age (newer = more suspicious)
    if account_age_days is not None:
        if account_age_days < 7:
            score += 0.40
        elif account_age_days < 30:
            score += 0.25
        elif account_age_days < 90:
            score += 0.10

    # Factor 2: Number of fraud cases this VPA appears in
    if total_cases > 5:
        score += 0.40
    elif total_cases > 2:
        score += 0.25
    elif total_cases > 1:
        score += 0.10

    # Factor 3: Existing risk score carries 20% weight
    score += existing_risk * 0.20

    return round(min(score, 1.0), 2)


def extract_naming_pattern(vpa: str) -> str:
    handle = vpa.split("@")[0]
    prefix = handle.rstrip("0123456789")
    prefix = prefix.rstrip("_.")
    return prefix if len(prefix) >= 2 else handle
