def classify_sensitivity(meta: dict, body: str) -> str:
    b = (body or "").lower()
    if any(w in b for w in ["invoice", "payment", "refund", "$", "usd"]):
        return "financial"
    if any(w in b for w in ["email", "gmail", "whatsapp", "message", "client", "linkedin", "twitter", "facebook", "instagram"]):
        return "external_communication"
    if any(w in b for w in ["delete", "remove", "erase", "drop table"]):
        return "data_deletion"
    if any(w in b for w in ["permission", "access", "role", "credential"]):
        return "access_change"
    return "none"
