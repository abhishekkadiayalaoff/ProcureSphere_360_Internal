# ProcureSphere 360: Policy Exception Workflow Implementation Report
## Procurement Manager Policy Exceptions Desk

**Document Reference:** `PS360-POLICY-EXCEPTION-2026-V1`  
**Execution Date:** November 4, 2026  
**Target Environment:** Internal Development Baseline (`feature/procurementManager-dashboard`)  
**Target Module:** Procurement Manager (`/manager/policy-exceptions/`) & Core Management APIs  

---

## 1. Executive Summary

This report provides the technical specification, architectural blueprint, and verification documentation for the **Policy Exception Desk** implemented within the Procurement Manager dashboard (`/manager/policy-exceptions/`).

Under the ProcureSphere 360 enterprise governance framework, policy exceptions occur when procurement requests deviate from standard business rules. The primary exception classes are:
1. **Budget Overrun Exceptions:** A purchase requisition requires funds exceeding the currently available budget allocation in the assigned cost center.
2. **Invoice 3-Way Match Exceptions:** Invoiced amounts, quantities, or unit prices deviate beyond configured tolerances when compared against the underlying Purchase Order (PO) and Goods Receipt Note (GRN).

The implementation establishes a robust, transaction-safe, and auditable governance desk that enforces rigorous separation of duties, prevents cross-tenant access, and strictly maintains authority boundaries between Procurement and Finance.

---

## 2. Governance Authority Boundaries

A cornerstone of the PRD requirements is the strict differentiation of authority between **Procurement Management** and **Finance / Accounts Payable (AP)**:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      POLICY EXCEPTION DESK                             │
│                  URL: /manager/policy-exceptions/                      │
├───────────────────────────────────┬────────────────────────────────────┤
│     BUDGET OVERRUN EXCEPTIONS     │      INVOICE MATCH EXCEPTIONS      │
├───────────────────────────────────┼────────────────────────────────────┤
│ • Authority: PROCUREMENT MANAGER  │ • Authority: FINANCE AP            │
│ • Actions: APPROVE / REJECT       │ • Manager Role: READ-ONLY OVERSIGHT│
│ • Atomic fund reservation override│ • Direct resolution blocked (403)  │
│ • AuditLog(action='OVERRIDE')     │ • Dispatched to Finance Desk       │
│ • Separation of Duties enforced   │ • AuditLog(action='ACCESS')        │
└───────────────────────────────────┴────────────────────────────────────┘
```

### 2.1 Budget Overrun Governance
The Procurement Manager is authorized to review requests where a department requires emergency spending beyond budget limits. The manager can:
- **Approve Exception:** Bypasses budget constraints (`force_overrun=True`), reserves the required funds in the budget pool, transitions the requisition to `STATUS_SUBMITTED`, records an `ApprovalAction` with the manager's identity and comments, and emits an immutable `AuditLog(action=OVERRIDE)`.
- **Reject Exception:** Releases any soft reservations, transitions the requisition to `STATUS_REJECTED`, records an `ApprovalAction` with rejection rationale, and emits an immutable `AuditLog(action=REJECT)`.

### 2.2 Invoice Match Oversight Boundary
While Procurement Managers require visibility into invoice matching hold-ups to troubleshoot supply chain delays, they **do not possess financial resolution authority**. Any API call attempting to settle, override, or clear an invoice match exception from the Manager desk is rejected server-side with `HTTP 403 Forbidden` (`AUTHORITY_BOUNDARY_VIOLATION`).

---

## 3. Technical Architecture & Endpoints

### 3.1 Routing & URL Scheme

| Endpoint URL | HTTP Method | Handler / Class | Purpose |
|---|---|---|---|
| `/manager/policy-exceptions/` | `GET` | `manager_policy_exceptions_view` | Full-page HTML Policy Exception Desk |
| `/api/v1/manager/policy-exceptions/` | `GET` | `ManagerBudgetExceptionsAPIView` | REST endpoint retrieving aggregated exception metrics, overrun PRs, and invoice exceptions |
| `/api/v1/manager/budget-exceptions/` | `GET` | `ManagerBudgetExceptionsAPIView` | Alias REST endpoint for backward compatibility |
| `/api/v1/manager/budget-exceptions/decision/` | `POST` | `ManagerBudgetExceptionDecisionAPIView` | Transactional endpoint executing exception approval or rejection decisions |
| `/api/v1/manager/policy-exceptions/decision/` | `POST` | `ManagerBudgetExceptionDecisionAPIView` | Unified REST alias for exception decisions |

### 3.2 Transactional Concurrency & Database Safety
All exception decision operations are guarded by database-level transactions:
```python
with transaction.atomic():
    pr = Requisition.objects.select_for_update().get(id=requisition_id)
    # Validate tenant isolation
    if str(pr.organization_id) != str(org.id):
        return Response({"error": "ACCESS_DENIED"}, status=status.HTTP_403_FORBIDDEN)
```
- **Row-Level Locking:** Prevents race conditions where two concurrent managers attempt to decide on the same requisition.
- **Rollback Guarantee:** If budget reservation fails or database constraints are violated, all changes (status changes, reservation records, approval actions) roll back automatically.

### 3.3 Separation of Duties (SoD) Validation
Enterprise compliance mandates that no user may approve their own requisition, regardless of their administrative rank.
```python
if pr.requester_id and pr.requester_id == request.user.id:
    return Response(
        {"error": "SEPARATION_OF_DUTIES_VIOLATION", "message": "You cannot approve your own policy exception."},
        status=status.HTTP_400_BAD_REQUEST
    )
```

### 3.4 Mandatory Audit Justification
Decisions to override enterprise budget caps cannot be made silently:
```python
comments = (request.data.get("comments") or "").strip()
if len(comments) < 5:
    return Response(
        {"error": "JUSTIFICATION_REQUIRED", "message": "A detailed audit comment (minimum 5 characters) is required."},
        status=status.HTTP_400_BAD_REQUEST
    )
```

---

## 4. Frontend UI/UX Design

The Policy Exception Desk is implemented in `templates/manager/policy_exceptions.html`, following the ProcureSphere 360 design system:

### 4.1 Key Performance Indicators (KPIs)
The top section features 5 live-computed, database-backed metric cards:
1. **Pending Overrun Exceptions:** Count of active budget overrun PRs requiring manager intervention.
2. **Total Overrun Value:** Cumulative financial variance in currency units.
3. **Invoice Match Discrepancies:** Active 3-way match exceptions currently blocked in Accounts Payable.
4. **Approved Exceptions (MTD):** Count of successfully approved budget exceptions in the current calendar month.
5. **Resolved Discrepancies (MTD):** Count of cleared invoice discrepancies.

### 4.2 Interactive Budget Overruns Tab
- Displays PR Number, Request Title, Department, Cost Center, Allocated Budget, Available Budget, Requested Amount, Overrun Variance, Requester, and Pending Duration.
- Includes an **"Evaluate Exception"** action button opening an interactive evaluation modal.
- The modal allows the Procurement Manager to inspect financial exposure, review past requisition history, enter mandatory justification, and execute **"Approve & Reserve Funds"** or **"Reject Request"**.

### 4.3 Invoice Match Exceptions Oversight Tab
- Prominently displays an **Authoritative Governance Banner**:
  > *"Notice: Invoice match discrepancies are under the operational jurisdiction of Finance AP. Procurement Managers have read-only visibility for delivery coordination."*
- Lists PO Reference, Supplier Name, Invoice Number, Match Type (Quantity / Price Variance), Discrepancy Amount, and Hold Status.
- Disables resolution actions, guiding the user to contact Finance AP.

### 4.4 Global Navigation Integration
Updated `templates/manager/base_manager.html` to integrate the "Policy Exceptions" navigation link under the `PROCUREMENT` section, complete with a dynamic warning badge displaying the live count of pending exceptions (`policy_exceptions_count`).

---

## 5. Verification & Test Evidence

The Policy Exception workflow was verified via dedicated automated tests in `tests/test_manager_policy_exceptions_workflow.py`. All 8 tests passed unconditionally:

| Test Case Name | Assertion Objective | HTTP Status | Result |
|---|---|---|---|
| `test_manager_policy_exceptions_view_access` | Verify HTML view renders for manager, blocked for requester | 200 OK / 403 Forbidden | **PASS** |
| `test_policy_exceptions_api_data` | Validate KPI metrics, overrun PRs, and invoice data formatting | 200 OK | **PASS** |
| `test_policy_exception_approve_decision` | Verify successful override approval, budget reservation, and AuditLog emission | 200 OK | **PASS** |
| `test_policy_exception_reject_decision` | Verify rejection, fund release, status update to REJECTED | 200 OK | **PASS** |
| `test_policy_exception_self_approval_blocked` | Enforce separation of duties when manager is requester | 400 Bad Request | **PASS** |
| `test_policy_exception_missing_comments_blocked` | Enforce minimum 5 characters justification validation | 400 Bad Request | **PASS** |
| `test_policy_exception_cross_org_blocked` | Block cross-tenant exception manipulation (IDOR) | 403 Forbidden | **PASS** |
| `test_invoice_match_exception_resolution_blocked_for_manager` | Block manager attempts to resolve invoice match exceptions | 403 Forbidden | **PASS** |

---

## 6. Conclusion

The Policy Exception workflow is fully realized and operational. It bridges the critical operational gap between rigid budget controls and business agility while ensuring 100% audit compliance, database concurrency safety, and strict multi-tenant isolation.

