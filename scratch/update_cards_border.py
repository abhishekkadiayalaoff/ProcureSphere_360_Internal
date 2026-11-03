file_path = r"c:\Users\windows10\Desktop\PRO 360\ProcureSphere_360_Internal\templates\manager\dashboard.html"

with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

# Replace the 4 KPI cards styling
target_kpis = """        <!-- 1. Pending Award Approvals -->
        <div class="col-sm-6 col-xl-3">
            <a href="/manager/awards/" class="text-decoration-none">
                <div class="stat-card h-100 border-start border-4 border-warning" style="background-color: #FFFFFF; border: 1px solid #DEE2E6 !important; border-left: 4px solid #FFC107 !important; border-radius: 14px;">
                    <div class="d-flex align-items-center justify-content-between mb-2">
                        <span class="text-muted small fw-semibold text-uppercase">Pending Awards</span>
                        <span class="badge bg-warning bg-opacity-25 text-dark rounded-pill small fw-bold">Action Required</span>
                    </div>
                    <div class="d-flex align-items-baseline gap-2">
                        <div class="metric-value fs-3 fw-bold text-dark" id="kpiPendingAwards">0</div>
                    </div>
                    <div class="mt-2 pt-2 border-top d-flex justify-content-between align-items-center small">
                        <span class="text-warning fw-semibold">Review Awards <i class="fa-solid fa-arrow-right ms-1"></i></span>
                    </div>
                </div>
            </a>
        </div>

        <!-- 2. PR Bottlenecks & Aging -->
        <div class="col-sm-6 col-xl-3">
            <a href="/manager/pr-aging/" class="text-decoration-none">
                <div class="stat-card h-100 border-start border-4 border-danger" style="background-color: #FFFFFF; border: 1px solid #DEE2E6 !important; border-left: 4px solid #DC3545 !important; border-radius: 14px;">
                    <div class="d-flex align-items-center justify-content-between mb-2">
                        <span class="text-muted small fw-semibold text-uppercase">PR Bottlenecks</span>
                        <span class="badge bg-danger bg-opacity-10 text-danger border border-danger border-opacity-25 rounded-pill small fw-bold" id="kpiPRBottleneckValue">$0.00</span>
                    </div>
                    <div class="d-flex align-items-baseline gap-2">
                        <div class="metric-value fs-3 fw-bold text-danger" id="kpiPRBottlenecks">0</div>
                    </div>
                    <div class="mt-2 pt-2 border-top d-flex justify-content-between align-items-center small">
                        <span class="text-danger fw-semibold">Inspect Aging <i class="fa-solid fa-arrow-right ms-1"></i></span>
                    </div>
                </div>
            </a>
        </div>

        <!-- 3. Active Purchase Orders -->
        <div class="col-sm-6 col-xl-3">
            <a href="/manager/purchase-orders/" class="text-decoration-none">
                <div class="stat-card h-100 border-start border-4 border-primary" style="background-color: #FFFFFF; border: 1px solid #DEE2E6 !important; border-left: 4px solid #0D6EFD !important; border-radius: 14px;">
                    <div class="d-flex align-items-center justify-content-between mb-2">
                        <span class="text-muted small fw-semibold text-uppercase">Active Orders (PO)</span>
                        <span class="badge bg-primary bg-opacity-10 text-primary border border-primary border-opacity-25 rounded-pill small fw-bold" id="kpiActivePOValue">$0.00</span>
                    </div>
                    <div class="d-flex align-items-baseline gap-2">
                        <div class="metric-value fs-3 fw-bold text-primary" id="kpiActivePOs">0</div>
                    </div>
                    <div class="mt-2 pt-2 border-top d-flex justify-content-between align-items-center small">
                        <span class="text-primary fw-semibold">View POs <i class="fa-solid fa-arrow-right ms-1"></i></span>
                    </div>
                </div>
            </a>
        </div>

        <!-- 4. High-Risk & Suspended Vendors -->
        <div class="col-sm-6 col-xl-3">
            <a href="/manager/vendor-risk/" class="text-decoration-none">
                <div class="stat-card h-100 border-start border-4 border-danger" style="background-color: #FFFFFF; border: 1px solid #DEE2E6 !important; border-left: 4px solid #DC3545 !important; border-radius: 14px;">
                    <div class="d-flex align-items-center justify-content-between mb-2">
                        <span class="text-muted small fw-semibold text-uppercase">High-Risk Vendors</span>
                        <span class="badge bg-secondary bg-opacity-25 text-secondary border border-secondary border-opacity-25 rounded-pill small fw-bold" id="kpiKYCReviews">0 in KYC</span>
                    </div>
                    <div class="d-flex align-items-baseline gap-2">
                        <div class="metric-value fs-3 fw-bold text-danger" id="kpiHighRiskVendors">0</div>
                    </div>
                    <div class="mt-2 pt-2 border-top d-flex justify-content-between align-items-center small">
                        <span class="text-danger fw-semibold">Governance Desk <i class="fa-solid fa-arrow-right ms-1"></i></span>
                    </div>
                </div>
            </a>
        </div>"""

replacement_kpis = """        <!-- 1. Pending Award Approvals (Yellow Border) -->
        <div class="col-sm-6 col-xl-3">
            <a href="/manager/awards/" class="text-decoration-none">
                <div class="card h-100 shadow-sm rounded-4 p-3 hover-elevate transition-all" style="background-color: #FFFFFF; border: 2px solid #FFC107 !important; border-radius: 14px;">
                    <div class="d-flex align-items-center justify-content-between mb-2">
                        <span class="text-muted small fw-semibold text-uppercase">Pending Awards</span>
                        <span class="badge bg-warning bg-opacity-25 text-dark rounded-pill small fw-bold">Action Required</span>
                    </div>
                    <div class="d-flex align-items-baseline gap-2">
                        <div class="metric-value fs-3 fw-bold text-dark" id="kpiPendingAwards">0</div>
                    </div>
                    <div class="mt-2 pt-2 border-top d-flex justify-content-between align-items-center small">
                        <span class="text-warning fw-semibold">Review Awards <i class="fa-solid fa-arrow-right ms-1"></i></span>
                    </div>
                </div>
            </a>
        </div>

        <!-- 2. PR Bottlenecks & Aging (Red Border) -->
        <div class="col-sm-6 col-xl-3">
            <a href="/manager/pr-aging/" class="text-decoration-none">
                <div class="card h-100 shadow-sm rounded-4 p-3 hover-elevate transition-all" style="background-color: #FFFFFF; border: 2px solid #DC3545 !important; border-radius: 14px;">
                    <div class="d-flex align-items-center justify-content-between mb-2">
                        <span class="text-muted small fw-semibold text-uppercase">PR Bottlenecks</span>
                        <span class="badge bg-danger bg-opacity-10 text-danger border border-danger border-opacity-25 rounded-pill small fw-bold" id="kpiPRBottleneckValue">$0.00</span>
                    </div>
                    <div class="d-flex align-items-baseline gap-2">
                        <div class="metric-value fs-3 fw-bold text-danger" id="kpiPRBottlenecks">0</div>
                    </div>
                    <div class="mt-2 pt-2 border-top d-flex justify-content-between align-items-center small">
                        <span class="text-danger fw-semibold">Inspect Aging <i class="fa-solid fa-arrow-right ms-1"></i></span>
                    </div>
                </div>
            </a>
        </div>

        <!-- 3. Active Purchase Orders (Blue Border) -->
        <div class="col-sm-6 col-xl-3">
            <a href="/manager/purchase-orders/" class="text-decoration-none">
                <div class="card h-100 shadow-sm rounded-4 p-3 hover-elevate transition-all" style="background-color: #FFFFFF; border: 2px solid #0D6EFD !important; border-radius: 14px;">
                    <div class="d-flex align-items-center justify-content-between mb-2">
                        <span class="text-muted small fw-semibold text-uppercase">Active Orders (PO)</span>
                        <span class="badge bg-primary bg-opacity-10 text-primary border border-primary border-opacity-25 rounded-pill small fw-bold" id="kpiActivePOValue">$0.00</span>
                    </div>
                    <div class="d-flex align-items-baseline gap-2">
                        <div class="metric-value fs-3 fw-bold text-primary" id="kpiActivePOs">0</div>
                    </div>
                    <div class="mt-2 pt-2 border-top d-flex justify-content-between align-items-center small">
                        <span class="text-primary fw-semibold">View POs <i class="fa-solid fa-arrow-right ms-1"></i></span>
                    </div>
                </div>
            </a>
        </div>

        <!-- 4. High-Risk & Suspended Vendors (Neutral Border) -->
        <div class="col-sm-6 col-xl-3">
            <a href="/manager/vendor-risk/" class="text-decoration-none">
                <div class="card h-100 shadow-sm rounded-4 p-3 hover-elevate transition-all" style="background-color: #FFFFFF; border: 2px solid #DEE2E6 !important; border-radius: 14px;">
                    <div class="d-flex align-items-center justify-content-between mb-2">
                        <span class="text-muted small fw-semibold text-uppercase">High-Risk Vendors</span>
                        <span class="badge bg-secondary bg-opacity-25 text-secondary border border-secondary border-opacity-25 rounded-pill small fw-bold" id="kpiKYCReviews">0 in KYC</span>
                    </div>
                    <div class="d-flex align-items-baseline gap-2">
                        <div class="metric-value fs-3 fw-bold text-danger" id="kpiHighRiskVendors">0</div>
                    </div>
                    <div class="mt-2 pt-2 border-top d-flex justify-content-between align-items-center small">
                        <span class="text-danger fw-semibold">Governance Desk <i class="fa-solid fa-arrow-right ms-1"></i></span>
                    </div>
                </div>
            </a>
        </div>"""

if target_kpis in text:
    text = text.replace(target_kpis, replacement_kpis)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)
    print("4 cards border updated successfully!")
else:
    print("Target KPIs block not found.")

