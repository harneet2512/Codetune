"""Test runner tool — runs tests against the mock codebase and returns results."""
import json

# Deterministic test results for demo workflows
TEST_RESULTS = {
    "tests/test_checkout.py": {
        "total": 4,
        "passed": 3,
        "failed": 1,
        "results": [
            {"name": "test_checkout_happy_path", "status": "PASSED", "duration": "0.12s"},
            {"name": "test_checkout_empty_cart", "status": "PASSED", "duration": "0.03s"},
            {"name": "test_checkout_payment_failure", "status": "PASSED", "duration": "0.08s"},
            {
                "name": "test_checkout_org_discount",
                "status": "FAILED",
                "duration": "0.15s",
                "error": "AssertionError: assert 100.00 == 85.00\n  Where 100.00 = response.json['total']\n  Expected org discount of 15% was not applied",
                "traceback": "tests/test_checkout.py:28: AssertionError",
            },
        ],
    },
    "tests/test_export.py": {
        "total": 4,
        "passed": 3,
        "failed": 1,
        "results": [
            {"name": "test_export_admin", "status": "PASSED", "duration": "0.05s"},
            {"name": "test_export_owner", "status": "PASSED", "duration": "0.04s"},
            {
                "name": "test_export_custom_role",
                "status": "FAILED",
                "duration": "0.03s",
                "error": 'PermissionError: Only admins can export\n  User "user-billing-admin" has role "billing-admin" which is not in ["admin", "owner"]',
                "traceback": "src/services/export.py:12: PermissionError",
            },
            {"name": "test_export_viewer_rejected", "status": "PASSED", "duration": "0.02s"},
        ],
    },
    "tests/test_auth.py": {
        "total": 5,
        "passed": 2,
        "failed": 3,
        "results": [
            {"name": "test_valid_token", "status": "PASSED", "duration": "0.02s"},
            {"name": "test_expired_token", "status": "PASSED", "duration": "0.01s"},
            {
                "name": "test_none_algorithm_rejected",
                "status": "FAILED",
                "duration": "0.01s",
                "error": 'SecurityError: jwt.decode accepts algorithm "none" — tokens can be forged without a secret',
                "traceback": "tests/test_auth.py:15: SecurityError",
            },
            {
                "name": "test_token_expiry_within_1hr",
                "status": "FAILED",
                "duration": "0.01s",
                "error": "AssertionError: Token expiry is 720 hours (30 days), spec requires <= 1 hour",
                "traceback": "tests/test_auth.py:22: AssertionError",
            },
            {
                "name": "test_secret_not_hardcoded",
                "status": "FAILED",
                "duration": "0.01s",
                "error": 'AssertionError: SECRET_KEY is hardcoded as "hardcoded-secret-key-2024", must use env var',
                "traceback": "tests/test_auth.py:30: AssertionError",
            },
        ],
    },
}

# When running all tests
ALL_RESULTS = {
    "total": sum(r["total"] for r in TEST_RESULTS.values()),
    "passed": sum(r["passed"] for r in TEST_RESULTS.values()),
    "failed": sum(r["failed"] for r in TEST_RESULTS.values()),
    "suites": list(TEST_RESULTS.keys()),
}


def run(test_path: str = "", test_name: str = "") -> str:
    """Run tests. Specify a test file or specific test name."""
    if not test_path and not test_name:
        return json.dumps(ALL_RESULTS)

    # Run specific test file
    if test_path in TEST_RESULTS:
        return json.dumps(TEST_RESULTS[test_path])

    # Run specific test by name
    if test_name:
        for suite_path, suite in TEST_RESULTS.items():
            for result in suite["results"]:
                if result["name"] == test_name:
                    return json.dumps({
                        "suite": suite_path,
                        "test": result,
                    })
        return json.dumps({"error": f"Test '{test_name}' not found"})

    return json.dumps({"error": f"Test file '{test_path}' not found"})
