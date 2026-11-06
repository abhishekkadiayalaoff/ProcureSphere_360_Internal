# ProcureSphere 360: Changed Files Manifest
## Procurement Manager & Auditor Dashboards Remediation

**Document Reference:** `PS360-CHANGED-FILES-2026-V1`  
**Execution Date:** November 4, 2026  
**Target Environment:** Internal Development Baseline (`feature/procurementManager-dashboard`)  

---

## 1. Summary of Changes

A total of **19 source files** were modified or created during this remediation:
- **16 modified files** (backend selectors, services, views, APIs, templates, and tests)
- **3 newly created files** (1 full UI template + 2 comprehensive automated test suites)
- **Zero schema migrations created or applied** (strictly preserved existing models)
- **Zero Git configurations modified**

---

## 2. Exhaustive File-by-File Manifest

### 2.1 Backend Core & Audit Layer

#### 1. `src/apps/audit/selectors.py` (Modified)
- **Architectural Role:** Multi-Tenant Audit Data Access & Query Optimization
- **Key Changes:**
  - Implemented `is_entity_authorized_for_org(target_model, target_object_id, organization)` to dynamically verify polymorphic entity ownership.
  - Implemented `_to_str_ids(queryset)` dual-format ID converter generating both canonical 36-character hyphenated UUIDs and 32-character hex representations. This ensures 100% reliable SQL matching in SQLite and PostgreSQL for `AuditLog.target_object_id`.
  - Implemented `get_scoped_audit_logs_queryset(base_qs, organization)` to enforce tenant filtering.
  - Scoped all 10 selector functions (`get_audit_logs`, `get_audit_metrics`, `get_auditor_dashboard_data`, `get_entity_audit_trail`, `get_vendor_compliance_audit`, `get_approval_history_audit`, `get_sourcing_activity_audit`, `get_po_changes_audit`, `get_invoice_exceptions_audit`, `get_contract_changes_audit`, `get_security_events_audit`) by `organization`.

#### 2. `src/apps/audit/services.py` (Modified)
- **Architectural Role:** Compliance Business Logic, Lifecycle Graph Assembly & Data Export
- **Key Changes:**
  - In `get_transaction_lifecycle_service()`, added root entity authorization validation against the authenticated auditor's organization. Returns `is_unauthorized=True` on cross-tenant attempts and scopes linked `AuditLog` queries by `organization`.
  - In `export_auditor_data_service()`, accepts and enforces `organization`, defaulting to `actor.effective_organization` or `actor.organization` for non-superusers. Passes `organization` into all 8 selector functions.

#### 3. `src/apps/audit/views.py` (Modified)
- **Architectural Role:** Auditor HTML View Controllers & Access Enforcement
- **Key Changes:**
  - Hardened `_enforce_auditor_access(request)` to permit strictly `Role.AUDITOR` and `Role.SUPER_ADMIN` (removed `Role.FINANCE_AP`).
  - Added `_get_auditor_org(request)` helper function.
  - Updated all 11 audit views (`auditor_dashboard_view`, `audit_logs_view`, `vendor_compliance_audit_view`, `approval_history_audit_view`, `sourcing_activity_audit_view`, `po_changes_audit_view`, `invoice_exceptions_audit_view`, `contract_changes_audit_view`, `security_events_audit_view`, `entity_audit_trail_view`, `transaction_lifecycle_view`) to extract `organization` and pass it to selectors.

#### 4. `src/apps/audit/api_views.py` (Modified)
- **Architectural Role:** REST API Endpoints for Auditor Dashboard
- **Key Changes:**
  - Overrode `get_queryset()` in `AuditLogViewSet` using `_get_auditor_org(self.request)` and `get_scoped_audit_logs_queryset`.
  - Scoped all endpoints (`list`, `metrics`, `lifecycle`, `entity_trail`, `dashboard_data`, `vendor_compliance`, `approval_history`, `sourcing_activity`, `po_changes`, `invoice_exceptions`, `contract_changes`, `security_events`, `export_data`) by `organization`.
  - Enforced HTTP 403 Forbidden on cross-tenant `lifecycle` and `entity_trail` requests.
  - Scoped all 10 standalone functional API views at the bottom of the file by `organization`.

#### 5. `src/apps/core/manager_api_views.py` (Modified)
- **Architectural Role:** Procurement Manager REST API Controllers
- **Key Changes:**
  - Enhanced `ManagerBudgetExceptionsAPIView` to compute database-backed KPIs (`kpi_overrun_count`, `kpi_overrun_value`, `kpi_match_exceptions_count`, `kpi_approved_exceptions_count`, `kpi_resolved_match_count`) and return enriched `budget_overrun_prs` and `invoice_match_exceptions`.
  - Implemented `ManagerBudgetExceptionDecisionAPIView`:
    - Concurrency-safe `@transaction.atomic` with row locks (`select_for_update()`).
    - Separation of duties: blocks self-approval (`pr.requester_id == request.user.id`) with HTTP 400.
    - Mandatory audit justification: requires minimum 5 characters with HTTP 400.
    - Multi-tenant isolation: blocks cross-tenant requisitions with HTTP 403.
    - Approval path: calls `check_and_reserve_budget_service(..., force_overrun=True)`, updates status to `STATUS_SUBMITTED`, records `ApprovalAction`, and writes `AuditLog(action=OVERRIDE)`.
    - Rejection path: calls `release_budget_reservation_service(...)`, updates status to `STATUS_REJECTED`, records `ApprovalAction`, and writes `AuditLog(action=REJECT)`.
    - Authority boundary enforcement: blocks attempts to resolve invoice match exceptions with HTTP 403 `AUTHORITY_BOUNDARY_VIOLATION`.

#### 6. `src/apps/core/manager_api_urls.py` (Modified)
- **Architectural Role:** URL Routing for Manager REST APIs
- **Key Changes:**
  - Registered `budget-exceptions/decision/` (`manager-budget-exception-decision-api`).
  - Registered `policy-exceptions/decision/` (`manager-policy-exception-decision-api`).

#### 7. `src/apps/core/manager_views.py` (Modified)
- **Architectural Role:** Procurement Manager HTML Views
- **Key Changes:**
  - Implemented `manager_policy_exceptions_view(request)` with tenant scoping and role guard.
  - Added `policy_exceptions_count` to `_get_manager_context()` for real-time sidebar badge updates.

#### 8. `src/apps/core/manager_urls.py` (Modified)
- **Architectural Role:** URL Routing for Manager HTML Views
- **Key Changes:**
  - Registered `path("policy-exceptions/", manager_policy_exceptions_view, name="manager_policy_exceptions")`.

---

### 2.2 Frontend Templates & Design System

#### 9. `templates/audit/base_auditor.html` (Modified)
- **Architectural Role:** Base Layout & Navigation for Auditor Dashboard
- **Key Changes:**
  - Removed misleading client-side JavaScript scope dropdown (`setAuditorScope`).
  - Added authoritative server-rendered **Active Organization Scope Badge** (`{{ user.effective_organization.name }}` or `{{ user.organization.name }}`) with safe null-guarding for test runners.
  - Displays `Global Compliance Vault` badge for Super Administrators.

#### 10. `templates/manager/base_manager.html` (Modified)
- **Architectural Role:** Base Layout & Navigation for Procurement Manager
- **Key Changes:**
  - Added "Policy Exceptions" navigation item under `PROCUREMENT` with dynamic pending badge counter.
  - Unified "Vendor Risk" and "Vendor Suspension" links into a single unified entry: `Vendor Risk & Governance` pointing to `/manager/vendor-risk/`.

#### 11. `templates/manager/dashboard.html` (Modified)
- **Architectural Role:** Procurement Manager Executive Dashboard
- **Key Changes:**
  - Updated Invoice Match Exceptions summary card to link directly to `/manager/policy-exceptions/?tab=invoices`.

#### 12. `templates/manager/approvals.html` (Modified)
- **Architectural Role:** Procurement Manager Approvals Oversight Desk
- **Key Changes:**
  - Adjusted approval governance layout and oversight visibility.

#### 13. `templates/manager/vendor_risk.html` (Modified)
- **Architectural Role:** Unified Vendor Risk & Governance Desk
- **Key Changes:**
  - Consolidated supplier risk scoring, live financial exposure inspection (invitations, bids, pending awards, open POs), and administrative hold/suspension actions into a single unified view.
  - Integrated real-time append-only governance audit trail.

#### 14. `templates/manager/policy_exceptions.html` (Newly Created)
- **Architectural Role:** Dedicated Policy Exception Desk
- **Key Content:**
  - 5 KPI metric cards with live counts and variance amounts.
  - Tab 1: Budget Overruns (with evaluation and approval/rejection modal).
  - Tab 2: Invoice Match Exceptions (with explicit Finance AP authority banner).
  - Search, filter, and pagination controls.

---

### 2.3 Automated Testing Suites

#### 15. `tests/test_auditor_organization_isolation.py` (Newly Created)
- **Architectural Role:** Auditor Multi-Tenant Security & RBAC Test Suite
- **Key Content:**
  - 13 test cases verifying role enforcement (Auditor/Super Admin allowed; Finance AP, Manager, Requester, Vendor, Stores denied 403).
  - Verifies multi-tenant isolation across logs selectors, REST APIs, lifecycle queries, entity trails, and exports.

#### 16. `tests/test_manager_policy_exceptions_workflow.py` (Newly Created)
- **Architectural Role:** Policy Exception Workflow & Authority Boundary Test Suite
- **Key Content:**
  - 8 test cases verifying view access, API metrics, approval decisions, rejection decisions, separation of duties, mandatory justifications, cross-tenant protection, and invoice authority boundaries.

#### 17. `tests/test_manager_approvals_desk.py` (Modified)
- **Architectural Role:** Approvals Desk Test Suite
- **Key Changes:**
  - Verified manager non-interference oversight and API endpoints.

#### 18. `tests/test_manager_vendor_suspension_module.py` (Modified)
- **Architectural Role:** Unified Vendor Risk Desk Test Suite
- **Key Changes:**
  - Updated assertions to validate the unified `Vendor Risk & Governance` navigation and tabs.

#### 19. `tests/test_vendor_hold_suspension_risk.py` (Modified)
- **Architectural Role:** Vendor Sanction State Machine Test Suite
- **Key Changes:**
  - Normalized role constants for testing environment compatibility.

---

## 3. Verification & Test Execution Status

All 19 files were integrated and verified against the full regression test suite:
- **Total Test Cases:** 53
- **Total Passed:** 53
- **Pass Rate:** 100%
- **Regressions Introduced:** 0

