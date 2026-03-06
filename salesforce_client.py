"""
Salesforce client — queries open Opportunities and updates the NextStep field.
"""
import re
from datetime import datetime
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
    result = sf.Opportunity.get(opportunity_id, ["NextStep"])
    return result.get("NextStep") or ""


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


def close_opportunity(opportunity_id: str, sf=None) -> str:
    """Write 'Close Opportunity' to the NextStep field."""
    if sf is None:
        sf = get_sf_connection()
    update_next_step(opportunity_id, "Close Opportunity", sf)
    return "Close Opportunity"
