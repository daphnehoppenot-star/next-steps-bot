"""
Salesforce client — queries open Opportunities and updates the NextStep field.
"""
import re
from datetime import datetime, timedelta
from simple_salesforce import Salesforce
from config import SF_USERNAME, SF_PASSWORD, SF_SECURITY_TOKEN, SF_DOMAIN


def get_sf_connection():
    """Create and return a Salesforce connection."""
    return Salesforce(
        username=SF_USERNAME,
        password=SF_PASSWORD,
        security_token=SF_SECURITY_TOKEN,
        domain=SF_DOMAIN,
    )


def get_opps_for_owner(owner_email: str, sf=None) -> list[dict]:
    """
    Query open Opportunities for a specific owner by email.

    Returns a list of dicts:
        [
            {
                "id": "006...",
                "name": "Acme Corp — Renewal 2026",
                "account": "Acme Corp",
                "amount": 120000,
                "stage": "Negotiation",
                "close_date": "2026-03-28",
                "next_step": "Waiting for security review (3/1/2026)",
                "next_step_text": "Waiting for security review",
                "next_step_date": "3/1/2026",
            },
            ...
        ]
    """
    if sf is None:
        sf = get_sf_connection()

    # Escape single quotes in email for SOQL
    safe_email = owner_email.replace("'", "\\'")

    query = f"""
        SELECT
            Id,
            Name,
            Account.Name,
            Amount,
            StageName,
            CloseDate,
            NextStep
        FROM Opportunity
        WHERE IsClosed = false
          AND Owner.Email = '{safe_email}'
        ORDER BY CloseDate ASC
    """

    results = sf.query_all(query)
    opps = []

    for record in results["records"]:
        raw_ns = record.get("NextStep") or ""

        # Parse date stamp from end of NextStep, e.g. "(3/6/2026)"
        ns_text = raw_ns
        ns_date = None
        date_match = re.search(r"\((\d{1,2}/\d{1,2}/\d{4})\)\s*$", raw_ns)
        if date_match:
            ns_text = raw_ns[: date_match.start()].strip()
            ns_date = date_match.group(1)

        opps.append(
            {
                "id": record["Id"],
                "name": record["Name"],
                "account": record["Account"]["Name"]
                if record.get("Account")
                else "Unknown",
                "amount": record.get("Amount") or 0,
                "stage": record["StageName"],
                "close_date": record["CloseDate"],
                "next_step": raw_ns,
                "next_step_text": ns_text,
                "next_step_date": ns_date,
            }
        )

    return opps


def get_next_step(opportunity_id: str, sf=None) -> str:
    """Read the current NextStep field value for an Opportunity."""
    if sf is None:
        sf = get_sf_connection()
    result = sf.query(
        f"SELECT NextStep FROM Opportunity WHERE Id = '{opportunity_id}'"
    )
    records = result.get("records", [])
    return records[0].get("NextStep", "") if records else ""


def update_next_step(opportunity_id: str, next_step_text: str, sf=None) -> bool:
    """Write the formatted next-step string to the Opportunity's NextStep field."""
    if sf is None:
        sf = get_sf_connection()
    sf.Opportunity.update(opportunity_id, {"NextStep": next_step_text})
    return True


def format_next_step(action: str, text: str) -> str:
    """
    Prepend the locked prefix based on the action, then append today's date.

    Prefixes:
        waiting  → "Waiting for "
        meeting  → "Meeting "
        call     → "Call "
        action   → (none)
    """
    today = datetime.now().strftime("%-m/%-d/%Y")

    prefixes = {
        "waiting": "Waiting for ",
        "meeting": "Meeting ",
        "call": "Call ",
        "other": "Other Next Step: ",
    }
    prefix = prefixes.get(action, "")
    return f"{prefix}{text.strip()} ({today})"


def still_accurate(opportunity_id: str, sf=None) -> str:
    """
    Re-stamp the existing NextStep with today's date.
    Returns the updated text.
    """
    if sf is None:
        sf = get_sf_connection()

    today = datetime.now().strftime("%-m/%-d/%Y")
    current_ns = get_next_step(opportunity_id, sf)

    # Strip old date stamp
    current_ns = re.sub(r"\s*\(\d{1,2}/\d{1,2}/\d{4}\)\s*$", "", current_ns).strip()
    updated = f"{current_ns} ({today})" if current_ns else f"Still accurate ({today})"

    update_next_step(opportunity_id, updated, sf)
    return updated


def get_all_open_opps(sf=None) -> list[dict]:
    """
    Query ALL open Opportunities with owner info for summary tables.

    Returns a list of dicts:
        [
            {
                "id": "006...",
                "name": "Acme Corp — Renewal 2026",
                "owner_name": "John Smith",
                "owner_email": "john@voyantis.ai",
                "stage": "Negotiation",
                "next_step": "Waiting for security review (3/1/2026)",
                "next_step_date": "3/1/2026",  # or None
            },
            ...
        ]
    """
    if sf is None:
        sf = get_sf_connection()

    query = """
        SELECT
            Id,
            Name,
            Owner.Name,
            Owner.Email,
            StageName,
            NextStep
        FROM Opportunity
        WHERE IsClosed = false
        ORDER BY Owner.Name ASC, CloseDate ASC
    """

    results = sf.query_all(query)
    opps = []

    for record in results["records"]:
        raw_ns = record.get("NextStep") or ""
        ns_date = None
        date_match = re.search(r"\((\d{1,2}/\d{1,2}/\d{4})\)\s*$", raw_ns)
        if date_match:
            ns_date = date_match.group(1)

        owner = record.get("Owner") or {}
        opps.append(
            {
                "id": record["Id"],
                "name": record["Name"],
                "owner_name": owner.get("Name", "Unknown"),
                "owner_email": owner.get("Email", ""),
                "stage": record["StageName"],
                "next_step": raw_ns,
                "next_step_date": ns_date,
            }
        )

    return opps


def get_last_monday() -> datetime:
    """Return the most recent Monday at 9am (the last reminder send time)."""
    now = datetime.now()
    days_since_monday = now.weekday()  # Monday=0
    if days_since_monday == 0 and now.hour >= 9:
        # It's Monday past 9am — use today
        return now.replace(hour=9, minute=0, second=0, microsecond=0)
    else:
        # Go back to the previous Monday
        days_back = days_since_monday if days_since_monday > 0 else 7
        last_monday = now - timedelta(days=days_back)
        return last_monday.replace(hour=9, minute=0, second=0, microsecond=0)


def _normalize_stage(raw_stage: str) -> str:
    """
    Map any legacy / abbreviated StageName to the current SFDC picklist value.

    Current SFDC picklist (in pipeline order):
        Stage 0: Pitch Booked
        Stage 1: Person (MQL) || Onboarded || Upcoming
        Stage 2: Discovery (SQL) || Experiment || Discovery || Identified
        Stage 3: Proposal
        Stage 4: Legal
        Closed Won
        Closed Lost
    """
    STAGE_MAP = {
        # Legacy names → current SFDC picklist value
        "Sales Qualified": "Stage 2: Discovery (SQL) || Experiment || Discovery || Identified",
        "Discovery": "Stage 2: Discovery (SQL) || Experiment || Discovery || Identified",
        "Proposal & Negotiation": "Stage 3: Proposal",
        "Proposal & Negotiations": "Stage 3: Proposal",
        "Legal & Procurement": "Stage 4: Legal",
        "Legal & Procurement (& Tech Fit)": "Stage 4: Legal",
        "Tech Fit": "Stage 4: Legal",
    }
    return STAGE_MAP.get(raw_stage, raw_stage)


# Pipeline order for sorting the By Stage table
STAGE_ORDER = [
    "Stage 0: Pitch Booked",
    "Stage 1: Person (MQL) || Onboarded || Upcoming",
    "Stage 2: Discovery (SQL) || Experiment || Discovery || Identified",
    "Stage 3: Proposal",
    "Stage 4: Legal",
]

# Short display labels for the UI
STAGE_DISPLAY_LABEL = {
    "Stage 0: Pitch Booked": "Pitch Booked",
    "Stage 1: Person (MQL) || Onboarded || Upcoming": "Person (MQL)",
    "Stage 2: Discovery (SQL) || Experiment || Discovery || Identified": "Discovery (SQL)",
    "Stage 3: Proposal": "Proposal",
    "Stage 4: Legal": "Legal",
}


def build_summary(opps: list[dict]) -> dict:
    """
    Build summary data from all open opportunities.

    Returns:
        {
            "by_owner": [{"name": "John Smith", "count": 5, "completed": True}, ...],
            "by_stage": [{"stage": "Stage 3: Proposal", "count": 3}, ...],
            "total": 42,
            "last_reminder": "3/2/2026",
        }
    """
    from collections import defaultdict

    last_monday = get_last_monday()
    last_monday_str = last_monday.strftime("%-m/%-d/%Y")

    # Group by owner
    owner_opps = defaultdict(list)
    stage_counts = defaultdict(int)

    for opp in opps:
        owner_opps[opp["owner_name"]].append(opp)
        normalized = _normalize_stage(opp["stage"])
        stage_counts[normalized] += 1

    # Build owner summary with completion status
    by_owner = []
    for name in sorted(owner_opps.keys()):
        owner_list = owner_opps[name]
        # Check if all opps have a next_step_date on or after last Monday
        all_completed = True
        for o in owner_list:
            if not o["next_step_date"]:
                all_completed = False
                break
            try:
                ns_dt = datetime.strptime(o["next_step_date"], "%m/%d/%Y")
            except ValueError:
                all_completed = False
                break
            if ns_dt < last_monday.replace(hour=0, minute=0, second=0, microsecond=0):
                all_completed = False
                break

        by_owner.append(
            {
                "name": name,
                "count": len(owner_list),
                "completed": all_completed,
            }
        )

    # Build stage summary — sorted by pipeline order
    def stage_sort_key(item):
        stage = item["stage"]
        try:
            return STAGE_ORDER.index(stage)
        except ValueError:
            return 999  # Unknown stages go last

    by_stage = [
        {
            "stage": stage,
            "label": STAGE_DISPLAY_LABEL.get(stage, stage),
            "count": count,
        }
        for stage, count in stage_counts.items()
    ]
    by_stage.sort(key=stage_sort_key)

    return {
        "by_owner": by_owner,
        "by_stage": by_stage,
        "total": len(opps),
        "last_reminder": last_monday_str,
    }


def close_opportunity(opportunity_id: str, sf=None) -> str:
    """Write 'Close Opportunity' to the NextStep field."""
    if sf is None:
        sf = get_sf_connection()
    update_next_step(opportunity_id, "Close Opportunity", sf)
    return "Close Opportunity"
