"""Log search tool — searches application logs for patterns, errors, time ranges."""
import json

# Mock application logs (for incident triage demo)
LOGS = [
    {"ts": "2024-03-28T14:03:22Z", "level": "INFO", "service": "checkout", "msg": "Deploy v2.14.0 started", "request_id": ""},
    {"ts": "2024-03-28T14:05:01Z", "level": "INFO", "service": "checkout", "msg": "Deploy v2.14.1 completed. Changes: new_checkout_flow enabled", "request_id": ""},
    {"ts": "2024-03-28T14:05:15Z", "level": "INFO", "service": "checkout", "msg": "POST /api/checkout 201 125ms user=u-1001", "request_id": "req-8801"},
    {"ts": "2024-03-28T14:05:18Z", "level": "INFO", "service": "checkout", "msg": "POST /api/checkout 201 130ms user=u-1002", "request_id": "req-8802"},
    {"ts": "2024-03-28T14:06:02Z", "level": "ERROR", "service": "checkout", "msg": "POST /api/checkout 500 45ms user=u-2050 error='NoneType has no attribute price' org=acme-corp", "request_id": "req-8810"},
    {"ts": "2024-03-28T14:06:05Z", "level": "ERROR", "service": "checkout", "msg": "POST /api/checkout 500 38ms user=u-2051 error='NoneType has no attribute price' org=acme-corp", "request_id": "req-8811"},
    {"ts": "2024-03-28T14:06:10Z", "level": "INFO", "service": "checkout", "msg": "POST /api/checkout 201 122ms user=u-1003", "request_id": "req-8812"},
    {"ts": "2024-03-28T14:06:15Z", "level": "ERROR", "service": "checkout", "msg": "POST /api/checkout 500 41ms user=u-2052 error='NoneType has no attribute price' org=globex-inc", "request_id": "req-8813"},
    {"ts": "2024-03-28T14:06:22Z", "level": "WARN", "service": "checkout", "msg": "Inventory reservation timeout for SKU-4401, retrying...", "request_id": "req-8814"},
    {"ts": "2024-03-28T14:06:30Z", "level": "ERROR", "service": "checkout", "msg": "POST /api/checkout 500 39ms user=u-2053 error='NoneType has no attribute price' org=acme-corp", "request_id": "req-8815"},
    {"ts": "2024-03-28T14:06:45Z", "level": "INFO", "service": "checkout", "msg": "POST /api/checkout 201 118ms user=u-1005", "request_id": "req-8816"},
    {"ts": "2024-03-28T14:07:00Z", "level": "ERROR", "service": "checkout", "msg": "POST /api/checkout 500 42ms user=u-2054 error='NoneType has no attribute price' org=widgets-llc", "request_id": "req-8817"},
    {"ts": "2024-03-28T14:07:15Z", "level": "INFO", "service": "payment", "msg": "Charge succeeded $29.99 user=u-1003 payment_id=pay-9912", "request_id": "req-8812"},
    {"ts": "2024-03-28T14:07:30Z", "level": "ERROR", "service": "checkout", "msg": "5 errors in last 90s on /api/checkout. All from orgs with custom pricing tiers.", "request_id": ""},
    {"ts": "2024-03-28T14:08:00Z", "level": "WARN", "service": "monitoring", "msg": "Error rate threshold breached: checkout 500s at 35% (threshold: 5%)", "request_id": ""},
]

DEPLOY_HISTORY = [
    {"version": "v2.14.0", "deployed_at": "2024-03-28T14:03:22Z", "author": "jsmith", "changes": ["Updated payment SDK", "Fixed cart validation"], "status": "superseded"},
    {"version": "v2.14.1", "deployed_at": "2024-03-28T14:05:01Z", "author": "deploy-bot", "changes": ["Enabled new_checkout_flow flag", "Added org discount lookup"], "status": "active", "rollback_available": True},
    {"version": "v2.13.9", "deployed_at": "2024-03-27T10:00:00Z", "author": "kwilson", "changes": ["Export performance fix"], "status": "previous_stable"},
]


def run(query: str = "", level: str = "", service: str = "", source: str = "logs") -> str:
    """Search application logs or deploy history."""
    if source == "deploys" or "deploy" in query.lower():
        return json.dumps({"deploys": DEPLOY_HISTORY})

    results = []
    for entry in LOGS:
        if level and entry["level"] != level.upper():
            continue
        if service and entry["service"] != service.lower():
            continue
        if query and query.lower() not in entry["msg"].lower():
            continue
        results.append(entry)

    if not results:
        return json.dumps({"error": f"No log entries matching query='{query}' level={level} service={service}"})

    return json.dumps({"entries": results, "total": len(results)})
