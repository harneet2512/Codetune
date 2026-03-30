"""Codebase search tool — searches a mock codebase for symbols, patterns, and references."""
import json
import re

# Mock codebase: realistic enough for demo workflows
CODEBASE = {
    # Auth middleware (for spec audit demo)
    "src/middleware/auth.py": {
        "content": """import jwt
from datetime import datetime, timedelta
from flask import request, g

SECRET_KEY = "hardcoded-secret-key-2024"

def auth_middleware():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return {"error": "Missing token"}, 401
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256", "none"])
        g.user_id = payload["sub"]
        g.roles = payload.get("roles", [])
        g.session_token = token  # Store full token in memory
    except jwt.ExpiredSignatureError:
        return {"error": "Token expired"}, 401
    except jwt.InvalidTokenError:
        return {"error": "Invalid token"}, 401

def create_token(user_id, roles, expires_hours=720):
    payload = {
        "sub": user_id,
        "roles": roles,
        "exp": datetime.utcnow() + timedelta(hours=expires_hours),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def check_permission(required_role):
    if required_role not in g.roles:
        return {"error": "Forbidden"}, 403
""",
        "last_modified": "2024-03-15",
        "author": "jsmith",
    },
    # Checkout endpoint (for incident triage demo)
    "src/api/checkout.py": {
        "content": """from flask import request, jsonify
from src.models.order import Order
from src.services.payment import charge_card
from src.services.inventory import reserve_items
from src.middleware.auth import auth_middleware
import logging

logger = logging.getLogger(__name__)

@app.route("/api/checkout", methods=["POST"])
@auth_middleware
def checkout():
    cart = request.json.get("items", [])
    if not cart:
        return jsonify({"error": "Empty cart"}), 400

    # Reserve inventory first
    reservation = reserve_items(cart)
    if not reservation.success:
        logger.warning(f"Inventory reservation failed: {reservation.error}")
        return jsonify({"error": "Items unavailable"}), 409

    # Charge payment
    total = sum(item["price"] * item["qty"] for item in cart)
    payment = charge_card(g.user_id, total, currency="USD")
    if not payment.success:
        reservation.rollback()
        logger.error(f"Payment failed for user {g.user_id}: {payment.error}")
        return jsonify({"error": "Payment failed"}), 402

    # Create order - BUG: doesn't handle custom roles org pricing
    order = Order.create(
        user_id=g.user_id,
        items=cart,
        total=total,  # Should apply org discount for custom roles
        payment_id=payment.id,
    )
    return jsonify({"order_id": order.id, "total": total}), 201
""",
        "last_modified": "2024-03-28",
        "author": "deploy-bot",
    },
    # Export module (for customer bug demo)
    "src/services/export.py": {
        "content": """import csv
import io
from src.models.user import User
from src.models.org import Organization

def export_org_data(org_id, requester_id):
    org = Organization.get(org_id)
    requester = User.get(requester_id)

    # Check permissions
    if requester.role not in ["admin", "owner"]:
        raise PermissionError("Only admins can export")

    # BUG: custom roles not in the hardcoded list above
    # Users with custom roles (e.g., "billing-admin") get PermissionError

    users = User.query.filter_by(org_id=org_id).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "email", "role", "created_at"])
    for u in users:
        writer.writerow([u.id, u.email, u.role, u.created_at])
    return buffer.getvalue()
""",
        "last_modified": "2024-03-20",
        "author": "kwilson",
    },
    # Database models
    "src/models/order.py": {
        "content": """from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from src.db import Base
from datetime import datetime

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    total = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    payment_id = Column(String, nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    customer_id = Column(String, ForeignKey("customers.customer_id"))  # Legacy column name
""",
        "last_modified": "2024-02-10",
        "author": "jsmith",
    },
    "src/models/customer.py": {
        "content": """from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from src.db import Base

class Customer(Base):
    __tablename__ = "customers"
    customer_id = Column(String, primary_key=True)  # Should be account_id
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    org_id = Column(String, ForeignKey("organizations.id"))
    tier = Column(String, default="free")
""",
        "last_modified": "2024-01-15",
        "author": "kwilson",
    },
    # Tests
    "tests/test_checkout.py": {
        "content": """import pytest
from src.api.checkout import checkout

def test_checkout_happy_path():
    response = checkout(items=[{"id": "SKU-1", "price": 29.99, "qty": 1}])
    assert response.status_code == 201
    assert "order_id" in response.json

def test_checkout_empty_cart():
    response = checkout(items=[])
    assert response.status_code == 400

def test_checkout_payment_failure():
    # Mock payment to fail
    response = checkout(items=[{"id": "SKU-1", "price": 29.99, "qty": 1}])
    assert response.status_code == 402
    # Verify inventory was rolled back
    assert not reservation_exists("SKU-1")

def test_checkout_org_discount():  # FAILING
    # Custom role org should get 15% discount
    response = checkout(
        items=[{"id": "SKU-1", "price": 100.00, "qty": 1}],
        user_role="billing-admin",
        org_discount=0.15,
    )
    assert response.json["total"] == 85.00  # Fails: gets 100.00
""",
        "last_modified": "2024-03-28",
        "author": "deploy-bot",
    },
    "tests/test_export.py": {
        "content": """import pytest
from src.services.export import export_org_data

def test_export_admin():
    result = export_org_data(org_id="org-1", requester_id="user-admin")
    assert "email" in result

def test_export_owner():
    result = export_org_data(org_id="org-1", requester_id="user-owner")
    assert "email" in result

def test_export_custom_role():  # FAILING
    # billing-admin should also be able to export
    result = export_org_data(org_id="org-1", requester_id="user-billing-admin")
    assert "email" in result  # Raises PermissionError instead

def test_export_viewer_rejected():
    with pytest.raises(PermissionError):
        export_org_data(org_id="org-1", requester_id="user-viewer")
""",
        "last_modified": "2024-03-22",
        "author": "kwilson",
    },
    # SQL migrations
    "migrations/003_rename_customer_id.sql": {
        "content": """-- Migration: Rename customer_id to account_id
-- Status: PENDING
-- Author: kwilson
-- Date: 2024-03-25

-- Step 1: Add new column
ALTER TABLE customers ADD COLUMN account_id VARCHAR(255);
UPDATE customers SET account_id = customer_id;

-- Step 2: Update foreign keys (orders table)
ALTER TABLE orders ADD COLUMN account_id VARCHAR(255);
UPDATE orders SET account_id = customer_id;

-- Step 3: Drop old columns (DANGEROUS - do after verification)
-- ALTER TABLE customers DROP COLUMN customer_id;
-- ALTER TABLE orders DROP COLUMN customer_id;
""",
        "last_modified": "2024-03-25",
        "author": "kwilson",
    },
    # Config
    "config/feature_flags.yaml": {
        "content": """flags:
  new_checkout_flow:
    enabled: true
    rollout_percentage: 100
    deployed_at: "2024-03-28T14:05:00Z"
  org_discount:
    enabled: false  # Disabled - blocking checkout bug
    rollout_percentage: 0
  export_v2:
    enabled: true
    rollout_percentage: 50
    allowed_roles: ["admin", "owner"]  # Missing custom roles!
""",
        "last_modified": "2024-03-28",
        "author": "deploy-bot",
    },
    # API spec
    "docs/api_security_spec.md": {
        "content": """# API Security Specification v2.1

## AUTH-001: Token Algorithm
All JWT tokens MUST use RS256 algorithm. HS256 is prohibited.
The "none" algorithm MUST be rejected.

## AUTH-002: Secret Management
JWT signing keys MUST NOT be hardcoded. Keys must be loaded from
environment variables or a secrets manager (Vault, AWS SM).

## AUTH-003: Token Expiry
Access tokens MUST expire within 1 hour (3600 seconds).
Refresh tokens MUST expire within 30 days.

## AUTH-004: Session Storage
Full JWT tokens MUST NOT be stored in application memory or logs.
Only the token hash or session ID may be stored.

## AUTH-005: Permission Model
Permission checks MUST use a role-based access control (RBAC) system
that supports custom roles. Hardcoded role lists are prohibited.

## AUTH-006: Rate Limiting
All authenticated endpoints MUST enforce rate limiting of 100 req/min.
""",
        "last_modified": "2024-02-01",
        "author": "security-team",
    },
}


def run(query: str, file_filter: str = "") -> str:
    """Search the codebase for a pattern or symbol."""
    results = []
    query_lower = query.lower()

    for filepath, file_data in CODEBASE.items():
        # Apply file filter if provided
        if file_filter and file_filter not in filepath:
            continue

        content = file_data["content"]
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            if query_lower in line.lower() or re.search(query, line, re.IGNORECASE):
                results.append({
                    "file": filepath,
                    "line": i,
                    "content": line.strip(),
                    "author": file_data["author"],
                    "modified": file_data["last_modified"],
                })

    if not results:
        return json.dumps({"error": f"No results found for '{query}'"})

    return json.dumps({"matches": results[:15], "total_matches": len(results)})
