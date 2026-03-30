"""Documentation search tool — searches internal docs, specs, and runbooks."""
import json

DOCS = {
    "api_security_spec": {
        "title": "API Security Specification v2.1",
        "path": "docs/api_security_spec.md",
        "sections": {
            "AUTH-001": "Token Algorithm: All JWT tokens MUST use RS256 algorithm. HS256 is prohibited. The 'none' algorithm MUST be rejected.",
            "AUTH-002": "Secret Management: JWT signing keys MUST NOT be hardcoded. Keys must be loaded from environment variables or a secrets manager (Vault, AWS SM).",
            "AUTH-003": "Token Expiry: Access tokens MUST expire within 1 hour (3600 seconds). Refresh tokens MUST expire within 30 days.",
            "AUTH-004": "Session Storage: Full JWT tokens MUST NOT be stored in application memory or logs. Only the token hash or session ID may be stored.",
            "AUTH-005": "Permission Model: Permission checks MUST use RBAC that supports custom roles. Hardcoded role lists are prohibited.",
            "AUTH-006": "Rate Limiting: All authenticated endpoints MUST enforce rate limiting of 100 req/min.",
        },
    },
    "incident_runbook": {
        "title": "Checkout Service Incident Runbook",
        "path": "docs/runbooks/checkout.md",
        "sections": {
            "triage": "1. Check error rate on monitoring dashboard. 2. Identify affected user segments. 3. Check deploy history for recent changes. 4. Check feature flags for recent toggles.",
            "rollback_criteria": "Rollback if: (a) error rate > 10% for > 5 min, (b) revenue impact > $1000/min, (c) data corruption detected. Do NOT rollback if: errors are isolated to a single org or user segment — hotfix instead.",
            "hotfix_process": "1. Create branch from last stable tag. 2. Apply minimal fix. 3. Run targeted test suite. 4. Deploy with feature flag disabled. 5. Gradual rollout.",
            "escalation": "Page on-call SRE if: error rate > 50%, payment failures detected, or data inconsistency confirmed.",
        },
    },
    "data_dictionary": {
        "title": "Data Dictionary — Revenue Metrics",
        "path": "docs/data/revenue.md",
        "sections": {
            "dashboard_revenue": "Dashboard revenue = SUM(orders.total) WHERE orders.status IN ('completed', 'refunded_partial') AND orders.created_at IN date_range. Includes: taxes, shipping. Excludes: fully refunded orders, test accounts (org_id LIKE 'test-%').",
            "warehouse_revenue": "Warehouse revenue = SUM(payment_events.amount) WHERE payment_events.type = 'charge' AND payment_events.status = 'settled'. Includes: net charges only. Excludes: pending, failed, refunded. Does NOT include taxes or shipping.",
            "known_discrepancy": "Dashboard includes taxes+shipping; warehouse is net charges only. Expected delta: 3-5%. If delta > 5%, check for: (1) unsettled payments, (2) timezone misalignment (dashboard=UTC, warehouse=US-Eastern), (3) test account filtering differences.",
        },
    },
    "schema_migration_guide": {
        "title": "Schema Migration Best Practices",
        "path": "docs/engineering/migrations.md",
        "sections": {
            "rename_columns": "Column renames MUST be done in 3 phases: (1) Add new column + backfill, (2) Update application code to use new column, (3) Drop old column after verification period (min 7 days).",
            "verification": "Before dropping old columns: (a) confirm zero reads from old column in query logs, (b) run full test suite, (c) verify all serializers/API responses use new name, (d) check for raw SQL queries outside ORM.",
            "rollback": "Every migration must have a rollback script. Test rollback in staging before production.",
        },
    },
}


def run(query: str, doc_id: str = "") -> str:
    """Search documentation for a topic or retrieve a specific doc."""
    if doc_id and doc_id in DOCS:
        return json.dumps(DOCS[doc_id])

    query_lower = query.lower()
    results = []

    for did, doc in DOCS.items():
        for section_id, content in doc["sections"].items():
            if query_lower in content.lower() or query_lower in section_id.lower():
                results.append({
                    "doc": doc["title"],
                    "doc_id": did,
                    "section": section_id,
                    "content": content,
                })

    if not results:
        return json.dumps({"error": f"No documentation found for '{query}'"})

    return json.dumps({"results": results, "total": len(results)})
