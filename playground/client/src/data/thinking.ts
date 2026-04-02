// ============================================================================
// thinking.ts - Rich thinking content for typing animation
// Each task x model combination has distinct thinking lines that reveal
// how each model tier approaches the same problem differently.
// ============================================================================

export interface ThinkingLine {
  type: 'think' | 'strong' | 'tool_call' | 'observe' | 'conclusion' | 'error' | 'separator'
  text: string
}

export type ThinkingData = Record<string, Record<string, ThinkingLine[]>>

export const thinkingContent: ThinkingData = {

  // ==========================================================================
  // TASK 1: incident-triage
  // Prompt: "500 errors spiked on /api/checkout after the 14:05 deploy.
  //          Recommend rollback, hotfix, or no action."
  // ==========================================================================
  'incident-triage': {
    base: [
      { type: 'think', text: 'This looks like a deployment issue. The errors started right after the deploy so it is probably caused by the new code.' },
      { type: 'think', text: 'When there are 500 errors after a deploy, the safest thing is to rollback.' },
      { type: 'conclusion', text: '\u2717 Recommend immediate rollback of the 14:05 deploy.' },
    ],

    sft: [
      { type: 'think', text: 'I need to investigate what happened after the 14:05 deploy to determine the right course of action.' },
      { type: 'tool_call', text: '\u2192 log_search(query="checkout", level="ERROR")' },
      { type: 'observe', text: '\u2190 234 errors found across checkout service. Various error types including NoneType, timeout, and connection refused.' },
      { type: 'think', text: 'There are a lot of errors. Let me also check what changed in the deploy.' },
      { type: 'tool_call', text: '\u2192 deploy_read(service="checkout", deploy_id="latest")' },
      { type: 'observe', text: '\u2190 Deploy at 14:05 included 3 PRs: refactor pricing, update dependencies, fix typo in docs.' },
      { type: 'think', text: 'Multiple changes went out. The error count is high so this seems serious.' },
      { type: 'tool_call', text: '\u2192 log_search(query="500", service="checkout", timerange="14:00-14:30")' },
      { type: 'observe', text: '\u2190 234 errors in 25 minutes. Error rate approximately 3.2%.' },
      { type: 'tool_call', text: '\u2192 read_spec(doc="incident runbook")' },
      { type: 'observe', text: '\u2190 Rollback criteria: >5% error rate across service OR confirmed data corruption.' },
      { type: 'think', text: 'The error rate is below the 5% threshold but there are still a lot of errors. Better to be safe.' },
      { type: 'conclusion', text: '! Recommend rollback. Multiple errors detected post-deploy across checkout service.' },
    ],

    grpo: [
      { type: 'think', text: 'Before recommending anything, I need to determine if this is broad or isolated.' },
      { type: 'think', text: 'The rollback threshold per our incident runbook is >5% error rate OR data corruption.' },
      { type: 'think', text: 'Let me check the specific error signature first rather than pulling all errors.' },
      { type: 'separator', text: '' },
      { type: 'tool_call', text: '\u2192 log_search(query="NoneType has no attribute price", service="checkout", level="ERROR")' },
      { type: 'observe', text: '\u2190 47 errors, all from orgs with custom_pricing=true. Standard checkout path unaffected.' },
      { type: 'strong', text: 'Key finding: isolated to custom-pricing orgs. This is <1% of total checkout traffic.' },
      { type: 'separator', text: '' },
      { type: 'tool_call', text: '\u2192 read_spec(doc="incident runbook")' },
      { type: 'observe', text: '\u2190 Rollback criteria: >5% error rate across service OR confirmed data corruption. Feature flag criteria: isolated impact, <5% traffic.' },
      { type: 'think', text: 'Error rate is well below 5%. No data corruption. Runbook says use feature flag for isolated issues.' },
      { type: 'separator', text: '' },
      { type: 'tool_call', text: '\u2192 github_search_code(repo="acme/checkout", query="new_checkout_flow")' },
      { type: 'observe', text: '\u2190 Feature flag new_checkout_flow found in config/flags.yaml, currently enabled.' },
      { type: 'think', text: 'There is an existing feature flag we can disable. Now let me confirm what the deploy changed.' },
      { type: 'tool_call', text: '\u2192 deploy_read(service="checkout", deploy_id="14:05")' },
      { type: 'observe', text: '\u2190 Changes: custom pricing null check removed in refactor. Author: @chen.' },
      { type: 'think', text: 'Root cause confirmed: the pricing refactor removed a null check that custom-pricing orgs depend on.' },
      { type: 'think', text: 'Rollback is overkill. The flag gives us an instant mitigation path and the fix is a one-line null check restore.' },
      { type: 'separator', text: '' },
      { type: 'conclusion', text: '\u2713 Recommend HOTFIX, not rollback. Disable new_checkout_flow flag immediately. Patch: restore null check in custom pricing path. Impact: <1% traffic, no data corruption.' },
    ],
  },

  // ==========================================================================
  // TASK 2: spec-audit
  // Prompt: "Audit the auth middleware against the API Security Spec."
  // ==========================================================================
  'spec-audit': {
    base: [
      { type: 'think', text: 'The auth middleware should follow security best practices. It needs to validate tokens and handle authentication properly.' },
      { type: 'think', text: 'Common security issues include missing HTTPS enforcement, weak token validation, and insufficient logging.' },
      { type: 'conclusion', text: '\u2717 There may be security issues with the auth middleware. Recommend a thorough security review.' },
    ],

    sft: [
      { type: 'think', text: 'I need to read both the security spec and the auth middleware code to perform the audit.' },
      { type: 'tool_call', text: '\u2192 read_spec(doc="API Security Spec")' },
      { type: 'observe', text: '\u2190 Spec requires: (1) token rotation every 1hr, (2) rate limiting at 100 req/min, (3) HMAC-SHA256 signature validation, (4) audit log on every auth failure.' },
      { type: 'tool_call', text: '\u2192 read_code(file="middleware/auth.py")' },
      { type: 'observe', text: '\u2190 Auth middleware: validates JWT tokens, checks expiry, logs successful auth. Rate limiting set to 500 req/min. No HMAC validation. Logs auth success but not failure.' },
      { type: 'think', text: 'I can see the middleware does JWT validation but the rate limit seems off and there is no HMAC check.' },
      { type: 'think', text: 'Let me compile the violations I found.' },
      { type: 'strong', text: 'Found 2 violations: rate limit is 500/min instead of 100/min, and HMAC-SHA256 validation is missing.' },
      { type: 'conclusion', text: '! Partial audit complete. Found rate limiting violation and missing HMAC validation. Recommend fixes for both.' },
    ],

    grpo: [
      { type: 'think', text: 'A proper spec audit requires systematically checking every requirement against the implementation. Let me build a checklist first.' },
      { type: 'separator', text: '' },
      { type: 'tool_call', text: '\u2192 read_spec(doc="API Security Spec")' },
      { type: 'observe', text: '\u2190 Spec defines 4 mandatory controls: (1) Token rotation \u22641hr [Section 3.1], (2) Rate limiting \u2264100 req/min per client [Section 4.2], (3) HMAC-SHA256 on all webhook payloads [Section 5.1], (4) Audit log entry on every auth failure [Section 6.3].' },
      { type: 'strong', text: 'Checklist built: 4 mandatory controls to verify. Will check each against the code.' },
      { type: 'separator', text: '' },
      { type: 'tool_call', text: '\u2192 read_code(file="middleware/auth.py")' },
      { type: 'observe', text: '\u2190 Line 14: token_expiry = 720 * 60 (720 hours). Line 31: rate_limit = 500. Line 45-60: JWT validation only, no HMAC. Line 72: logger.info("auth_success") but no failure logging branch.' },
      { type: 'separator', text: '' },
      { type: 'think', text: 'Now cross-referencing each control against the code:' },
      { type: 'strong', text: 'Violation 1 [Section 3.1]: Token expiry is 720hr at line 14. Spec requires \u22641hr. Severity: CRITICAL.' },
      { type: 'strong', text: 'Violation 2 [Section 4.2]: Rate limit is 500 req/min at line 31. Spec requires \u2264100. Severity: HIGH.' },
      { type: 'strong', text: 'Violation 3 [Section 5.1]: No HMAC-SHA256 validation anywhere in auth.py. Webhook payloads are unverified. Severity: CRITICAL.' },
      { type: 'strong', text: 'Violation 4 [Section 6.3]: Auth failure path at line 68 has no logging. Only success is logged at line 72. Severity: MEDIUM.' },
      { type: 'separator', text: '' },
      { type: 'think', text: 'All 4 mandatory controls are violated. Two are critical severity.' },
      { type: 'conclusion', text: '\u2713 Audit complete. 4/4 mandatory controls violated: (1) token expiry 720hr vs 1hr required [line 14], (2) rate limit 500 vs 100 [line 31], (3) missing HMAC validation [Section 5.1], (4) no auth failure logging [line 68]. Recommend immediate remediation of critical items.' },
    ],
  },

  // ==========================================================================
  // TASK 3: customer-bug
  // Prompt: "Exports fail for orgs with custom roles like billing-admin.
  //          Find the root cause."
  // ==========================================================================
  'customer-bug': {
    base: [
      { type: 'think', text: 'Export failures for custom roles sound like a permissions issue. The billing-admin role probably does not have the right permissions to export data.' },
      { type: 'think', text: 'Custom roles might not be included in the default permission set.' },
      { type: 'conclusion', text: '\u2717 This is likely a permissions issue. Check that billing-admin has export permissions in the role configuration.' },
    ],

    sft: [
      { type: 'think', text: 'I should look at the error logs to see what is happening when exports fail for these orgs.' },
      { type: 'tool_call', text: '\u2192 log_search(query="export", level="ERROR")' },
      { type: 'observe', text: '\u2190 12 errors: "InvalidRoleError: role billing-admin not found in enum" across 4 orgs with custom roles.' },
      { type: 'think', text: 'The error says the role is not found in an enum. Let me look at the export code.' },
      { type: 'tool_call', text: '\u2192 read_code(file="services/export.py")' },
      { type: 'observe', text: '\u2190 Export service validates user role against VALID_ROLES list before proceeding. Line 23: VALID_ROLES = ["admin", "member", "viewer", "billing"].' },
      { type: 'tool_call', text: '\u2192 read_code(file="models/roles.py")' },
      { type: 'observe', text: '\u2190 Role model supports custom roles via org_roles table. Custom roles like billing-admin are stored in the database, not in the enum.' },
      { type: 'tool_call', text: '\u2192 log_search(query="billing-admin export", level="ERROR")' },
      { type: 'observe', text: '\u2190 Same InvalidRoleError. Confirmed it is the enum check blocking custom roles.' },
      { type: 'think', text: 'The export service is checking against a hardcoded list that does not include custom roles.' },
      { type: 'conclusion', text: '! The VALID_ROLES enum in export.py does not include custom roles. The hardcoded list needs to be updated.' },
    ],

    grpo: [
      { type: 'think', text: 'Export failures for a specific role pattern suggests a validation issue rather than a permissions issue. Let me reproduce the exact error first.' },
      { type: 'separator', text: '' },
      { type: 'tool_call', text: '\u2192 log_search(query="InvalidRoleError billing-admin", service="export", level="ERROR")' },
      { type: 'observe', text: '\u2190 12 errors: "InvalidRoleError: role billing-admin not found in RoleEnum". Stack trace points to export.py:validate_user_role() at line 28.' },
      { type: 'strong', text: 'Reproduced. The error is a validation failure in validate_user_role(), not a permissions check.' },
      { type: 'separator', text: '' },
      { type: 'tool_call', text: '\u2192 read_code(file="services/export.py", lines="20-35")' },
      { type: 'observe', text: '\u2190 Line 23: VALID_ROLES = Enum("RoleEnum", ["admin", "member", "viewer", "billing"]). Line 28: def validate_user_role(role): if role not in VALID_ROLES.__members__: raise InvalidRoleError(f"role {role} not found in RoleEnum").' },
      { type: 'think', text: 'Found it. The export service uses a hardcoded Enum for role validation. Custom roles like billing-admin are stored in the database but this enum only has the 4 default roles.' },
      { type: 'separator', text: '' },
      { type: 'tool_call', text: '\u2192 read_code(file="tests/test_export.py", query="custom role")' },
      { type: 'observe', text: '\u2190 No test cases for custom roles. All tests use "admin" or "member". The test gap matches the bug.' },
      { type: 'think', text: 'The test suite never exercises custom roles, which is why this was not caught earlier.' },
      { type: 'separator', text: '' },
      { type: 'think', text: 'Root cause is clear: export.py line 23 defines a static enum while the roles system supports dynamic custom roles via the database. The fix should query org_roles instead of checking the enum.' },
      { type: 'conclusion', text: '\u2713 Root cause: export.py line 23 hardcodes VALID_ROLES as a 4-member Enum, but custom roles (billing-admin) are stored in org_roles table. Fix: replace Enum check at line 28 with a database query to org_roles. Test gap: no custom role coverage in test_export.py.' },
    ],
  },

  // ==========================================================================
  // TASK 4: data-discrepancy
  // Prompt: "Dashboard says $12,450.49 and warehouse says $11,705.48.
  //          Determine the cause."
  // ==========================================================================
  'data-discrepancy': {
    base: [
      { type: 'think', text: 'The difference between $12,450.49 and $11,705.48 is $745.01. This is probably a timing issue between the two systems.' },
      { type: 'think', text: 'Dashboards often show slightly different numbers due to caching or refresh delays.' },
      { type: 'conclusion', text: '\u2717 This is likely a timing or caching discrepancy. The dashboard may include more recent transactions than the warehouse.' },
    ],

    sft: [
      { type: 'think', text: 'I need to understand how each system calculates its revenue figure.' },
      { type: 'tool_call', text: '\u2192 read_code(file="dashboard/queries/revenue.sql")' },
      { type: 'observe', text: '\u2190 SELECT SUM(amount) FROM orders WHERE status IN ("completed", "pending") AND created_at >= "2024-01-01".' },
      { type: 'tool_call', text: '\u2192 read_code(file="warehouse/transforms/revenue.sql")' },
      { type: 'observe', text: '\u2190 SELECT SUM(amount) FROM fact_orders WHERE order_status = "completed" AND order_date >= "2024-01-01".' },
      { type: 'think', text: 'Both queries look at orders since January 1st. The dashboard uses "orders" table and the warehouse uses "fact_orders".' },
      { type: 'think', text: 'The status filters look slightly different but I am not sure what the exact impact is.' },
      { type: 'think', text: 'The delta is $745.01 which could come from the different data sources or filters.' },
      { type: 'conclusion', text: '! The two systems use different tables and possibly different status filters. Further investigation needed to reconcile the $745.01 delta.' },
    ],

    grpo: [
      { type: 'think', text: 'A $745.01 discrepancy between dashboard and warehouse is too large for timing drift. I need to compare the exact query definitions.' },
      { type: 'separator', text: '' },
      { type: 'tool_call', text: '\u2192 read_code(file="dashboard/queries/revenue.sql")' },
      { type: 'observe', text: '\u2190 SELECT SUM(amount) FROM orders WHERE status IN ("completed", "pending") AND created_at >= "2024-01-01".' },
      { type: 'tool_call', text: '\u2192 read_code(file="warehouse/transforms/revenue.sql")' },
      { type: 'observe', text: '\u2190 SELECT SUM(amount) FROM fact_orders WHERE order_status = "completed" AND order_date >= "2024-01-01".' },
      { type: 'separator', text: '' },
      { type: 'strong', text: 'Found the filter difference: dashboard includes status IN ("completed", "pending") but warehouse only includes "completed".' },
      { type: 'think', text: 'The dashboard counts pending orders. The warehouse does not. That is the likely source of the delta.' },
      { type: 'separator', text: '' },
      { type: 'tool_call', text: '\u2192 run_query(query="SELECT SUM(amount) FROM orders WHERE status = \'pending\' AND created_at >= \'2024-01-01\'")' },
      { type: 'observe', text: '\u2190 Result: $745.01' },
      { type: 'strong', text: 'Confirmed: pending orders sum to exactly $745.01, which matches the discrepancy ($12,450.49 - $11,705.48 = $745.01).' },
      { type: 'separator', text: '' },
      { type: 'think', text: 'This is not a bug in either system. It is a definition mismatch. The dashboard defines revenue as completed + pending, while the warehouse defines revenue as completed only.' },
      { type: 'think', text: 'The question is which definition is correct for the business. Typically warehouse is the source of truth for finance.' },
      { type: 'conclusion', text: '\u2713 Cause: definition mismatch. Dashboard includes pending orders ($745.01), warehouse does not. Dashboard query: status IN ("completed", "pending"). Warehouse query: order_status = "completed". Recommend aligning dashboard to warehouse definition or adding a "pending" column for visibility.' },
    ],
  },

  // ==========================================================================
  // TASK 5: ci-fix
  // Prompt: "Checkout test suite has a failing test after the latest deploy.
  //          Identify the root cause."
  // ==========================================================================
  'ci-fix': {
    base: [
      { type: 'think', text: 'A failing test after a deploy usually means something changed that broke the expected behavior.' },
      { type: 'think', text: 'Need to check what the test expects and what the deploy changed.' },
      { type: 'conclusion', text: '\u2717 The test is probably failing because the deploy changed some behavior. Check the test assertions against the new code.' },
    ],

    sft: [
      { type: 'think', text: 'Let me look at the CI output to see which test is failing and what the error is.' },
      { type: 'tool_call', text: '\u2192 ci_read(suite="checkout", run="latest")' },
      { type: 'observe', text: '\u2190 FAIL test_checkout_total: AssertionError: expected 99.99 but got 94.99. 47 passed, 1 failed.' },
      { type: 'think', text: 'The checkout total test expects 99.99 but gets 94.99. That is a $5 difference.' },
      { type: 'tool_call', text: '\u2192 read_code(file="tests/test_checkout.py")' },
      { type: 'observe', text: '\u2190 test_checkout_total creates a cart with a $99.99 item and asserts total == 99.99.' },
      { type: 'tool_call', text: '\u2192 read_code(file="services/checkout.py")' },
      { type: 'observe', text: '\u2190 Checkout service calculates total and applies promotions. Line 45: applies active promotions to cart total.' },
      { type: 'tool_call', text: '\u2192 log_search(query="promotion applied", service="checkout")' },
      { type: 'observe', text: '\u2190 Promotion "SAVE5" applied 234 times today. $5 off orders over $50.' },
      { type: 'think', text: 'A $5 promotion is being applied. The test does not account for promotions.' },
      { type: 'conclusion', text: '! The test is failing because a $5 promotion (SAVE5) is being applied to the cart total. The test fixture does not account for active promotions.' },
    ],

    grpo: [
      { type: 'think', text: 'A single test failure in a suite of passing tests suggests a specific behavioral change, not a broad regression. Let me start with the exact failure.' },
      { type: 'separator', text: '' },
      { type: 'tool_call', text: '\u2192 ci_read(suite="checkout", test="test_checkout_total", run="latest")' },
      { type: 'observe', text: '\u2190 FAIL test_checkout_total: AssertionError at line 34: assert cart.total == 99.99, got 94.99. Duration: 0.3s. 47/48 tests passed.' },
      { type: 'think', text: 'The delta is exactly $5.00. That is suspiciously round. Not floating point, not rounding. This looks like a discount or promotion was applied.' },
      { type: 'separator', text: '' },
      { type: 'tool_call', text: '\u2192 read_code(file="tests/test_checkout.py", lines="28-40")' },
      { type: 'observe', text: '\u2190 Line 30: cart = Cart(items=[Item("widget", 99.99)]). Line 34: assert cart.total == 99.99. No setup/teardown for promotions. Test assumes no active promotions.' },
      { type: 'strong', text: 'Test gap: fixture does not isolate from active promotions. The test implicitly depends on no promotions being active.' },
      { type: 'separator', text: '' },
      { type: 'tool_call', text: '\u2192 read_code(file="services/checkout.py", lines="40-55")' },
      { type: 'observe', text: '\u2190 Line 45: for promo in get_active_promotions(): if promo.applies_to(cart): cart.total -= promo.discount. Line 48: Promotion pulled from promotions table at runtime.' },
      { type: 'think', text: 'The checkout service applies promotions from a database table at runtime. The test does not mock or clear promotions.' },
      { type: 'think', text: 'The deploy likely added or activated a promotion. Let me confirm.' },
      { type: 'tool_call', text: '\u2192 run_query(query="SELECT * FROM promotions WHERE active = true AND created_at > \'2024-01-15\'")' },
      { type: 'observe', text: '\u2190 SAVE5: $5 off orders over $50. Activated 2024-01-16 by @marketing. Auto-applied to all carts.' },
      { type: 'separator', text: '' },
      { type: 'strong', text: 'Root cause confirmed: SAVE5 promotion was activated by marketing on Jan 16. Test environment shares the promotions table with no isolation.' },
      { type: 'think', text: 'This is a test isolation bug, not a code bug. The checkout logic is working correctly.' },
      { type: 'conclusion', text: '\u2713 Root cause: test_checkout_total at line 34 assumes no active promotions, but the SAVE5 promotion ($5 off > $50) was activated on Jan 16. Fix: add test fixture to clear/mock promotions table before checkout tests. The checkout code itself is correct.' },
    ],
  },

  // ==========================================================================
  // TASK 6: schema-migration
  // Prompt: "Rename customer_id to account_id across the service without
  //          breaking compatibility."
  // ==========================================================================
  'schema-migration': {
    base: [
      { type: 'think', text: 'Renaming a column across a service requires updating the database schema and all references in the code.' },
      { type: 'think', text: 'You should do a find-and-replace of customer_id to account_id in all files.' },
      { type: 'conclusion', text: '\u2717 Rename customer_id to account_id in the database and do a global find-and-replace in the codebase.' },
    ],

    sft: [
      { type: 'think', text: 'I need to find all references to customer_id to understand the blast radius of this rename.' },
      { type: 'tool_call', text: '\u2192 code_search(query="customer_id", scope="repo")' },
      { type: 'observe', text: '\u2190 47 references across 12 files: models (3), services (4), API routes (2), tests (3). Also found in 2 external API contracts.' },
      { type: 'think', text: 'There are 47 references. I need to update all of them plus the database column.' },
      { type: 'think', text: 'The external API contracts are concerning because renaming the field would break clients.' },
      { type: 'think', text: 'I should write a migration to rename the column.' },
      { type: 'think', text: 'For the API, maybe we can add an alias for backward compatibility.' },
      { type: 'conclusion', text: '! Found 47 references across 12 files including 2 external API contracts. Recommend writing a migration and adding backward-compatible aliases in the API layer.' },
    ],

    grpo: [
      { type: 'think', text: 'A column rename across a service is a multi-phase operation. Before writing any migration, I need to map the blast radius and check for a migration guide.' },
      { type: 'separator', text: '' },
      { type: 'tool_call', text: '\u2192 code_search(query="customer_id", scope="repo")' },
      { type: 'observe', text: '\u2190 47 references: models/customer.py (8), models/order.py (4), services/billing.py (6), services/export.py (5), api/routes.py (7), api/serializers.py (4), tests/ (9), migrations/ (2), docs/api-contract.yaml (2).' },
      { type: 'strong', text: 'Blast radius: 47 references across 9 file groups. Critical: api-contract.yaml has external-facing references.' },
      { type: 'separator', text: '' },
      { type: 'tool_call', text: '\u2192 read_spec(doc="migration guide")' },
      { type: 'observe', text: '\u2190 Column renames must follow 3-phase process: (1) Add new column with dual-write, (2) Backfill and migrate reads, (3) Drop old column after 2 release cycles. Zero-downtime required.' },
      { type: 'think', text: 'The migration guide requires a 3-phase approach. No direct renames allowed.' },
      { type: 'separator', text: '' },
      { type: 'tool_call', text: '\u2192 read_code(file="docs/api-contract.yaml", query="customer_id")' },
      { type: 'observe', text: '\u2190 customer_id is in the public API response schema for /orders and /invoices endpoints. Used by 3 known external consumers.' },
      { type: 'think', text: 'The API contract has external consumers. We need a deprecation period, not a hard rename.' },
      { type: 'separator', text: '' },
      { type: 'tool_call', text: '\u2192 read_code(file="models/customer.py", lines="1-20")' },
      { type: 'observe', text: '\u2190 Line 5: customer_id = Column(UUID, primary_key=True). Line 8: ForeignKey references in order.py, billing.py, export.py.' },
      { type: 'think', text: 'Now I can build the phased migration plan:' },
      { type: 'separator', text: '' },
      { type: 'strong', text: 'Phase 1 (this release): Add account_id column. Dual-write both columns. API returns both fields. Migration: AddColumn + trigger.' },
      { type: 'strong', text: 'Phase 2 (next release): Migrate all reads to account_id. Backfill any nulls. Mark customer_id as deprecated in API contract. Update 9 test files.' },
      { type: 'strong', text: 'Phase 3 (release +2): Drop customer_id column and trigger. Remove deprecated field from API contract after consumer migration.' },
      { type: 'conclusion', text: '\u2713 3-phase migration plan per migration guide. Phase 1: dual-write with AddColumn. Phase 2: migrate reads, backfill, deprecate API field. Phase 3: drop old column after 2 release cycles. Blast radius: 47 refs across 9 file groups, 3 external API consumers need deprecation notice.' },
    ],
  },

  // ==========================================================================
  // TASK 7: conflicting-evidence
  // Prompt: "Spec says 1hr expiry, code says 720hr. Which should win and
  //          what should change?"
  // ==========================================================================
  'conflicting-evidence': {
    base: [
      { type: 'think', text: 'There is a mismatch between the spec and the code. The spec says 1 hour but the code says 720 hours.' },
      { type: 'think', text: 'Usually the spec is the intended behavior and the code should match it.' },
      { type: 'conclusion', text: '\u2717 The spec and code disagree. One of them needs to be updated to match the other. Need to determine which is correct.' },
    ],

    sft: [
      { type: 'think', text: 'I need to look at both the spec and the code to understand the full context of this discrepancy.' },
      { type: 'tool_call', text: '\u2192 read_spec(doc="API Security Spec", section="token-expiry")' },
      { type: 'observe', text: '\u2190 Section 3.1: "All session tokens MUST expire within 1 hour of issuance. This is a compliance requirement per SOC2 control AC-12."' },
      { type: 'tool_call', text: '\u2192 read_code(file="middleware/auth.py", query="expiry")' },
      { type: 'observe', text: '\u2190 Line 14: TOKEN_EXPIRY_HOURS = 720. Comment: "# 30 days - extended for better UX per product request".' },
      { type: 'think', text: 'The spec says 1 hour for compliance reasons. The code was changed to 720 hours for UX. These are in direct conflict.' },
      { type: 'think', text: 'Compliance requirements usually take priority over UX preferences.' },
      { type: 'conclusion', text: '! Spec requires 1hr expiry for SOC2 compliance. Code uses 720hr for UX. Compliance should win. Recommend changing code to 1hr.' },
    ],

    grpo: [
      { type: 'think', text: 'A spec vs code conflict needs authority resolution, not just a diff. I need to determine: who owns the spec, what the compliance implications are, and whether there is a way to satisfy both constraints.' },
      { type: 'separator', text: '' },
      { type: 'tool_call', text: '\u2192 read_spec(doc="API Security Spec", section="token-expiry")' },
      { type: 'observe', text: '\u2190 Section 3.1: "All session tokens MUST expire within 1 hour of issuance. This is a compliance requirement per SOC2 control AC-12." Approved by: Security Team, last updated 2024-01-05.' },
      { type: 'strong', text: 'The spec uses RFC 2119 "MUST" language and cites a specific SOC2 control. This is a compliance mandate, not a recommendation.' },
      { type: 'separator', text: '' },
      { type: 'tool_call', text: '\u2192 read_code(file="middleware/auth.py", lines="10-20")' },
      { type: 'observe', text: '\u2190 Line 14: TOKEN_EXPIRY_HOURS = 720. Line 15: # 30 days - extended for better UX per product request (PR #847, @martinez).' },
      { type: 'think', text: 'The code change has a paper trail: PR #847 by @martinez extended it for product/UX. But there is no security review on that PR.' },
      { type: 'separator', text: '' },
      { type: 'tool_call', text: '\u2192 github_search_pr(repo="acme/api", pr_number=847)' },
      { type: 'observe', text: '\u2190 PR #847: "Extend session duration for better UX". Approved by: @martinez (product), @lee (frontend). No security team reviewer. Merged 2024-01-12.' },
      { type: 'strong', text: 'PR #847 was merged without security review, 7 days after the spec was approved. The product team overrode a compliance control without authority.' },
      { type: 'separator', text: '' },
      { type: 'think', text: 'The authority chain is clear: SOC2 control AC-12 is a legal obligation. A product UX preference cannot override it.' },
      { type: 'think', text: 'However, the UX concern is legitimate. The solution should satisfy both: short token expiry with transparent refresh.' },
      { type: 'separator', text: '' },
      { type: 'strong', text: 'Recommendation: Spec wins. Revert TOKEN_EXPIRY_HOURS to 1. Implement silent token refresh to preserve UX. Require security review for future auth changes.' },
      { type: 'conclusion', text: '\u2713 Spec wins. SOC2 AC-12 mandates 1hr expiry. Code was changed to 720hr in PR #847 without security review. Fix: revert to 1hr, add silent token refresh for UX, add CODEOWNERS rule requiring security team approval on auth middleware changes.' },
    ],
  },

  // ==========================================================================
  // TASK 8: restraint-409
  // Prompt: "What HTTP status code should be returned for a business logic
  //          conflict?"
  // ==========================================================================
  'restraint-409': {
    base: [
      { type: 'think', text: 'Let me look up HTTP status codes to find the right one for business logic conflicts.' },
      { type: 'tool_call', text: '\u2192 web_search(query="HTTP status codes list wikipedia")' },
      { type: 'observe', text: '\u2190 Wikipedia: List of HTTP status codes. 4xx client errors include 400 Bad Request, 403 Forbidden, 404 Not Found, 409 Conflict...' },
      { type: 'think', text: 'There are several 4xx codes that could apply. 400 is for bad requests, 409 is for conflicts.' },
      { type: 'conclusion', text: '\u2717 You could use 400 Bad Request or 409 Conflict depending on the specific situation. Both are valid for business logic issues.' },
    ],

    sft: [
      { type: 'think', text: 'For a business logic conflict, I need to find the most appropriate HTTP status code.' },
      { type: 'tool_call', text: '\u2192 read_spec(doc="RFC 9110", section="status-codes")' },
      { type: 'observe', text: '\u2190 409 Conflict: "indicates that the request could not be completed due to a conflict with the current state of the target resource."' },
      { type: 'think', text: 'RFC 9110 defines 409 Conflict as the code for state conflicts. Business logic conflicts fit this definition.' },
      { type: 'conclusion', text: '! 409 Conflict is the appropriate status code. It indicates a conflict with the current state of the resource per RFC 9110.' },
    ],

    grpo: [
      { type: 'think', text: '409 Conflict.' },
      { type: 'separator', text: '' },
      { type: 'think', text: 'This is a well-established HTTP semantic. RFC 9110 Section 15.5.10 defines 409 as "the request could not be completed due to a conflict with the current state of the target resource." Business logic conflicts (e.g., trying to publish an already-published document, double-booking a slot) are the textbook use case.' },
      { type: 'separator', text: '' },
      { type: 'strong', text: 'No tools needed. This is domain knowledge, not a lookup task.' },
      { type: 'separator', text: '' },
      { type: 'conclusion', text: '\u2713 409 Conflict. Per RFC 9110 Section 15.5.10: for conflicts with the current state of the target resource. Include a response body describing the specific conflict so the client can resolve it.' },
    ],
  },
}
