"""
Next Steps Web App — Flask application.

Routes:
    GET  /                  → Email landing page
    POST /opps              → Load opportunities for an email
    POST /update            → Write a next-step update to Salesforce (AJAX)
    POST /still-accurate    → Re-stamp date on existing next step (AJAX)
    POST /close             → Write "Close Opportunity" to Salesforce (AJAX)
"""
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for

from config import SECRET_KEY, ALLOWED_EMAIL_DOMAINS
from salesforce_client import (
    get_opps_for_owner,
    get_all_open_opps,
    build_summary,
    format_next_step,
    update_next_step,
    still_accurate,
    close_opportunity,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = SECRET_KEY


# ═════════════════════════════════════════════════════════════
#  ROUTES
# ═════════════════════════════════════════════════════════════


@app.route("/")
def index():
    """Landing page — email input + summary tables."""
    summary = None
    try:
        all_opps = get_all_open_opps()
        summary = build_summary(all_opps)
    except Exception as e:
        logger.error(f"Failed to load summary: {e}")
    return render_template("index.html", summary=summary)


@app.route("/opps", methods=["POST"])
def opps():
    """Load and display opportunities for the given email."""
    email = request.form.get("email", "").strip().lower()

    if not email:
        return render_template("index.html", error="Please enter your email.")

    # Validate email domain
    domain = email.split("@")[-1] if "@" in email else ""
    if domain not in ALLOWED_EMAIL_DOMAINS:
        return render_template(
            "index.html",
            error=f"Only {', '.join(ALLOWED_EMAIL_DOMAINS)} emails are allowed.",
        )

    try:
        opportunities = get_opps_for_owner(email)
    except Exception as e:
        logger.error(f"Salesforce query failed for {email}: {e}")
        return render_template(
            "index.html",
            error="Could not connect to Salesforce. Please try again.",
        )

    if not opportunities:
        return render_template(
            "index.html",
            error="No open opportunities found for this email.",
        )

    return render_template("opps.html", email=email, opps=opportunities)


@app.route("/update", methods=["POST"])
def update():
    """AJAX endpoint — format and write a next-step update to Salesforce."""
    data = request.get_json()
    opp_id = data.get("opp_id")
    action = data.get("action")
    text = data.get("text", "").strip()

    if not opp_id or not action or not text:
        return jsonify({"ok": False, "error": "Missing fields."}), 400

    try:
        formatted = format_next_step(action, text)
        update_next_step(opp_id, formatted)
        logger.info(f"Updated {opp_id}: {formatted}")
        return jsonify({"ok": True, "formatted": formatted})
    except Exception as e:
        logger.error(f"Failed to update {opp_id}: {e}")
        return jsonify({"ok": False, "error": str(e)[:200]}), 500


@app.route("/still-accurate", methods=["POST"])
def handle_still_accurate():
    """AJAX endpoint — re-stamp the date on the existing next step."""
    data = request.get_json()
    opp_id = data.get("opp_id")

    if not opp_id:
        return jsonify({"ok": False, "error": "Missing opp_id."}), 400

    try:
        updated = still_accurate(opp_id)
        logger.info(f"Still accurate {opp_id}: {updated}")
        return jsonify({"ok": True, "formatted": updated})
    except Exception as e:
        logger.error(f"Failed still_accurate {opp_id}: {e}")
        return jsonify({"ok": False, "error": str(e)[:200]}), 500


@app.route("/close", methods=["POST"])
def handle_close():
    """AJAX endpoint — write 'Close Opportunity' to the NextStep field."""
    data = request.get_json()
    opp_id = data.get("opp_id")

    if not opp_id:
        return jsonify({"ok": False, "error": "Missing opp_id."}), 400

    try:
        result = close_opportunity(opp_id)
        logger.info(f"Closed {opp_id}: {result}")
        return jsonify({"ok": True, "formatted": result})
    except Exception as e:
        logger.error(f"Failed close {opp_id}: {e}")
        return jsonify({"ok": False, "error": str(e)[:200]}), 500


# ═════════════════════════════════════════════════════════════
#  ENTRYPOINT
# ═════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
