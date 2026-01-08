"""
Business-policy constants used across services/jobs.

Keep these in one place so rules remain consistent.
"""

# Cancellation is allowed only if training starts strictly later than this many hours.
CANCEL_HOURS_BEFORE_TRAINING: int = 2

# Auto-ban job checks upcoming trainings within this window.
AUTOBAN_HOURS_BEFORE_TRAINING: int = 2
