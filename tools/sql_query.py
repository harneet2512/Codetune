"""SQL query tool — runs queries against a mock database for data investigation."""
import json
import re

# Mock database tables with realistic data
TABLES = {
    "orders": {
        "columns": ["id", "user_id", "total", "currency", "payment_id", "status", "created_at", "customer_id"],
        "rows": [
            {"id": 1, "user_id": "u-1001", "total": 299.99, "currency": "USD", "payment_id": "pay-001", "status": "completed", "created_at": "2024-03-01", "customer_id": "cust-101"},
            {"id": 2, "user_id": "u-1002", "total": 1500.00, "currency": "USD", "payment_id": "pay-002", "status": "completed", "created_at": "2024-03-05", "customer_id": "cust-102"},
            {"id": 3, "user_id": "u-1003", "total": 89.50, "currency": "USD", "payment_id": "pay-003", "status": "refunded", "created_at": "2024-03-10", "customer_id": "cust-101"},
            {"id": 4, "user_id": "u-test-1", "total": 9999.99, "currency": "USD", "payment_id": "pay-test", "status": "completed", "created_at": "2024-03-12", "customer_id": "test-999"},
            {"id": 5, "user_id": "u-1004", "total": 450.00, "currency": "USD", "payment_id": "pay-005", "status": "completed", "created_at": "2024-03-15", "customer_id": "cust-103"},
            {"id": 6, "user_id": "u-1005", "total": 10000.00, "currency": "USD", "payment_id": "pay-006", "status": "completed", "created_at": "2024-03-20", "customer_id": "cust-104"},
            {"id": 7, "user_id": "u-1006", "total": 75.00, "currency": "USD", "payment_id": "pay-007", "status": "refunded_partial", "created_at": "2024-03-22", "customer_id": "cust-101"},
            {"id": 8, "user_id": "u-1007", "total": 125.50, "currency": "USD", "payment_id": "pay-008", "status": "completed", "created_at": "2024-03-25", "customer_id": "cust-105"},
        ],
    },
    "payment_events": {
        "columns": ["id", "order_id", "type", "amount", "status", "created_at"],
        "rows": [
            {"id": 1, "order_id": 1, "type": "charge", "amount": 269.99, "status": "settled", "created_at": "2024-03-01"},
            {"id": 2, "order_id": 1, "type": "tax", "amount": 30.00, "status": "settled", "created_at": "2024-03-01"},
            {"id": 3, "order_id": 2, "type": "charge", "amount": 1350.00, "status": "settled", "created_at": "2024-03-05"},
            {"id": 4, "order_id": 2, "type": "tax", "amount": 150.00, "status": "settled", "created_at": "2024-03-05"},
            {"id": 5, "order_id": 3, "type": "charge", "amount": 80.55, "status": "refunded", "created_at": "2024-03-10"},
            {"id": 6, "order_id": 4, "type": "charge", "amount": 9499.99, "status": "settled", "created_at": "2024-03-12"},
            {"id": 7, "order_id": 5, "type": "charge", "amount": 405.00, "status": "settled", "created_at": "2024-03-15"},
            {"id": 8, "order_id": 5, "type": "tax", "amount": 45.00, "status": "settled", "created_at": "2024-03-15"},
            {"id": 9, "order_id": 6, "type": "charge", "amount": 9000.00, "status": "settled", "created_at": "2024-03-20"},
            {"id": 10, "order_id": 6, "type": "tax", "amount": 1000.00, "status": "settled", "created_at": "2024-03-20"},
            {"id": 11, "order_id": 7, "type": "charge", "amount": 67.50, "status": "settled", "created_at": "2024-03-22"},
            {"id": 12, "order_id": 8, "type": "charge", "amount": 113.00, "status": "settled", "created_at": "2024-03-25"},
            {"id": 13, "order_id": 8, "type": "tax", "amount": 12.50, "status": "pending", "created_at": "2024-03-25"},
        ],
    },
    "customers": {
        "columns": ["customer_id", "email", "name", "org_id", "tier"],
        "rows": [
            {"customer_id": "cust-101", "email": "alice@acme.com", "name": "Alice Chen", "org_id": "acme-corp", "tier": "enterprise"},
            {"customer_id": "cust-102", "email": "bob@globex.com", "name": "Bob Smith", "org_id": "globex-inc", "tier": "enterprise"},
            {"customer_id": "cust-103", "email": "carol@startup.io", "name": "Carol Diaz", "org_id": "startup-io", "tier": "pro"},
            {"customer_id": "cust-104", "email": "dave@bigcorp.com", "name": "Dave Park", "org_id": "bigcorp-llc", "tier": "enterprise"},
            {"customer_id": "cust-105", "email": "eve@freelance.dev", "name": "Eve Nakamura", "org_id": None, "tier": "free"},
            {"customer_id": "test-999", "email": "test@internal.dev", "name": "Test Account", "org_id": "test-org", "tier": "test"},
        ],
    },
}

# Pre-computed query results for common queries
QUERY_RESULTS = {
    "dashboard_march_revenue": {
        "description": "Dashboard revenue: SUM(total) from orders WHERE status IN ('completed','refunded_partial') AND created_at LIKE '2024-03%' AND customer_id NOT LIKE 'test-%'",
        "result": [{"revenue": 12450.49}],
        "note": "Includes: orders 1,2,5,6,7,8. Excludes: order 3 (refunded), order 4 (test account)",
    },
    "warehouse_march_revenue": {
        "description": "Warehouse revenue: SUM(amount) from payment_events WHERE type='charge' AND status='settled' AND created_at LIKE '2024-03%'",
        "result": [{"revenue": 11705.48}],
        "note": "Net charges only. Excludes: refunded (order 3), tax events, pending events",
    },
}


def run(query: str) -> str:
    """Execute a SQL query against the database."""
    query_lower = query.lower().strip()

    # Match pre-computed results
    if "dashboard" in query_lower and "revenue" in query_lower:
        return json.dumps(QUERY_RESULTS["dashboard_march_revenue"])
    if "warehouse" in query_lower and "revenue" in query_lower:
        return json.dumps(QUERY_RESULTS["warehouse_march_revenue"])

    # Simple SELECT parser
    table_match = re.search(r"from\s+(\w+)", query_lower)
    if not table_match:
        return json.dumps({"error": "Could not parse table name from query"})

    table_name = table_match.group(1)
    if table_name not in TABLES:
        return json.dumps({"error": f"Table '{table_name}' not found. Available: {list(TABLES.keys())}"})

    table = TABLES[table_name]
    rows = table["rows"]

    # Simple WHERE filtering
    where_match = re.search(r"where\s+(.+?)(?:order|group|limit|$)", query_lower)
    if where_match:
        condition = where_match.group(1).strip()

        # Handle customer_id NOT LIKE 'test-%'
        if "not like" in condition and "test" in condition:
            key = condition.split("not")[0].strip()
            rows = [r for r in rows if not str(r.get(key, "")).startswith("test")]
        # Handle status = 'completed'
        elif "=" in condition and "!=" not in condition:
            parts = condition.split("=")
            if len(parts) == 2:
                key = parts[0].strip().strip("'\"")
                val = parts[1].strip().strip("'\"")
                rows = [r for r in rows if str(r.get(key, "")).lower() == val]
        # Handle status IN (...)
        elif "in" in condition:
            key_match = re.search(r"(\w+)\s+in\s*\(([^)]+)\)", condition)
            if key_match:
                key = key_match.group(1)
                vals = [v.strip().strip("'\"") for v in key_match.group(2).split(",")]
                rows = [r for r in rows if str(r.get(key, "")).lower() in vals]

    # Handle COUNT/SUM
    if "count(" in query_lower:
        return json.dumps({"result": [{"count": len(rows)}]})
    if "sum(" in query_lower:
        col_match = re.search(r"sum\((\w+)\)", query_lower)
        if col_match:
            col = col_match.group(1)
            total = sum(r.get(col, 0) for r in rows)
            return json.dumps({"result": [{"sum": round(total, 2)}]})

    # Handle LIMIT
    limit_match = re.search(r"limit\s+(\d+)", query_lower)
    if limit_match:
        rows = rows[: int(limit_match.group(1))]

    # Return schema info for DESCRIBE/SHOW
    if "describe" in query_lower or "schema" in query_lower or "columns" in query_lower:
        return json.dumps({"table": table_name, "columns": table["columns"], "row_count": len(table["rows"])})

    return json.dumps({"columns": table["columns"], "rows": rows[:20], "total_rows": len(rows)})
