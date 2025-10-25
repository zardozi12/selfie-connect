import logging

def send_security_alert(user_id: int, event: str, details: str = ""):
    # In production, integrate with email/SMS/Slack/etc.
    logging.warning(f"SECURITY ALERT: user={user_id} event={event} details={details}")