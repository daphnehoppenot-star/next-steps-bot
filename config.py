"""
Configuration — loads all secrets and settings from environment variables.
"""
import os

# ── Salesforce ──────────────────────────────────────────────
SF_USERNAME = os.environ.get("SF_USERNAME", "")
SF_PASSWORD = os.environ.get("SF_PASSWORD", "")
SF_SECURITY_TOKEN = os.environ.get("SF_SECURITY_TOKEN", "")
SF_DOMAIN = os.environ.get("SF_DOMAIN", "login")  # "login" for prod, "test" for sandbox

# ── App ─────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
# Restrict to @voyantis.ai emails (comma-separated list of allowed domains)
ALLOWED_EMAIL_DOMAINS = os.environ.get("ALLOWED_EMAIL_DOMAINS", "voyantis.ai").split(",")
