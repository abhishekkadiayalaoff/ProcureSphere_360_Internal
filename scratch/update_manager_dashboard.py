file_path = r"c:\Users\windows10\Desktop\PRO 360\ProcureSphere_360_Internal\templates\manager\dashboard.html"

with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update hero header
old_hero = """    <!-- Page Header Area (Glass-card dark matching Procurement Executive) -->
    <div class="glass-card-dark p-4 mb-4">
        <div class="row align-items-center g-3">
            <div class="col-lg-8">
                <span class="badge bg-info text-dark rounded-pill fw-bold px-3 py-1 mb-2">
                    <i class="fa-solid fa-shield-halved me-1"></i> GOVERNANCE HUB · PROCUREMENT MANAGER
                </span>
                <h1 class="fw-bold text-white mb-1 h3">Procurement Manager Executive Desk</h1>
                <p class="text-white-50 mb-0 small">{{ user.email }} · High-value approvals, RFQ/RFP award decisions, PR bottlenecks, and supplier risk governance.</p>
            </div>
            <div class="col-lg-4 text-lg-end d-flex flex-wrap gap-2 justify-content-lg-end">
                <button type="button" onclick="openDashboardGovModal()" class="btn btn-outline-warning rounded-pill px-3 fw-bold text-white border-warning" title="Execute Vendor Suspension or Reinstatement">
                    <i class="fa-solid fa-scale-balanced me-1"></i> Governance Action
                </button>
                <button onclick="loadDashboardMetrics()" class="btn btn-warning text-dark rounded-pill fw-bold px-4" id="refreshBtn">
                    <i class="fa-solid fa-arrows-rotate me-1" id="refreshIcon"></i> Refresh Data
                </button>
                <a href="/manager/awards/" class="btn btn-outline-light rounded-pill px-4">Pending Awards</a>
            </div>
        </div>
    </div>"""

new_hero = """    <!-- Page Header Area (Dark Charcoal matching Vendor Dashboard) -->
    <div class="card border-0 shadow-sm rounded-4 p-4 mb-4 text-white" style="background-color: #212529 !important;">
        <div class="row align-items-center g-3">
            <div class="col-lg-8">
                <span class="badge bg-secondary bg-opacity-50 text-light rounded-pill fw-bold px-3 py-1 mb-2" style="font-size: 0.68rem; letter-spacing: 0.05em;">
                    <i class="fa-solid fa-shield-halved text-cyan me-1"></i> GOVERNANCE HUB &bull; PROCUREMENT MANAGER
                </span>
                <h1 class="fw-bold text-white mb-1 h3">Procurement Manager Executive Desk</h1>
                <p class="text-white-50 mb-0 small">{{ user.email }} &bull; High-value approvals, RFQ/RFP award decisions, PR bottlenecks, and supplier risk governance.</p>
            </div>
            <div class="col-lg-4 text-lg-end d-flex flex-wrap gap-2 justify-content-lg-end">
                <button type="button" onclick="openDashboardGovModal()" class="btn btn-outline-light btn-sm rounded-pill px-3 fw-semibold" title="Execute Vendor Suspension or Reinstatement">
                    <i class="fa-solid fa-scale-balanced me-1"></i> Governance Action
                </button>
                <button onclick="loadDashboardMetrics()" class="btn btn-primary btn-sm rounded-pill fw-bold px-4 shadow-sm" id="refreshBtn">
                    <i class="fa-solid fa-arrows-rotate me-1" id="refreshIcon"></i> Refresh Data
                </button>
                <a href="/manager/awards/" class="btn btn-outline-light btn-sm rounded-pill px-4 fw-semibold">Pending Awards</a>
            </div>
        </div>
    </div>"""

if old_hero in text:
    text = text.replace(old_hero, new_hero)
    print("Hero updated successfully!")
else:
    print("Warning: old_hero not found directly, checking variations...")

# 2. Update KPI cards container and cards
old_kpi_block = """        <!-- 1. Pending Award Approvals -->
        <div class="col-sm-6 col-xl-3">
            <a href="/manager/awards/" class="text-decoration-none">
                <div class="stat-card h-100 border-start border-4 border-warning">
                    <div class="d-flex align-items-center justify-content-between mb-2">
                        <span class="text-muted small fw-semibold text-uppercase">Pending Awards</span>
                        <span class="badge bg-warning text-dark rounded-pill small">Action Required</span>
                    </div>
                    <div class="d-flex align-items-baseline gap-2">
                        <div class="metric-value text-dark" id="kpiPendingAwards">0</div>
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
                <div class="stat-card h-100 border-start border-4 border-danger">
                    <div class="d-flex align-items-center justify-content-between mb-2">
                        <span class="text-muted small fw-semibold text-uppercase">PR Bottlenecks</span>
                        <span class="badge bg-danger text-white rounded-pill small" id="kpiPRBottleneckValue">$0.00</span>
                    </div>
                    <div class="d-flex align-items-baseline gap-2">
                        <div class="metric-value text-danger" id="kpiPRBottlenecks">0</div>
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
                <div class="stat-card h-100 border-start border-4 border-primary">
                    <div class="d-flex align-items-center justify-content-between mb-2">
                        <span class="text-muted small fw-semibold text-uppercase">Active Orders (PO)</span>
                        <span class="badge bg-primary-subtle text-primary rounded-pill small" id="kpiActivePOValue">$0.00</span>
                    </div>
                    <div class="d-flex align-items-baseline gap-2">
                        <div class="metric-value text-primary" id="kpiActivePOs">0</div>
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
                <div class="stat-card h-100 border-start border-4 border-rose">
                    <div class="d-flex align-items-center justify-content-between mb-2">
                        <span class="text-muted small fw-semibold text-uppercase">High-Risk Vendors</span>
                        <span class="badge bg-secondary rounded-pill small" id="kpiKYCReviews">0 in KYC</span>
                    </div>
                    <div class="d-flex align-items-baseline gap-2">
                        <div class="metric-value text-rose" id="kpiHighRiskVendors">0</div>
                    </div>
                    <div class="mt-2 pt-2 border-top d-flex justify-content-between align-items-center small">
                        <span class="text-rose fw-semibold">Governance Desk <i class="fa-solid fa-arrow-right ms-1"></i></span>
                    </div>
                </div>
            </a>
        </div>"""

new_kpi_block = """        <!-- 1. Pending Award Approvals -->
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

if old_kpi_block in text:
    text = text.replace(old_kpi_block, new_kpi_block)
    print("KPI cards updated successfully!")
else:
    print("Warning: old_kpi_block not found directly.")

# 3. Replace all remaining glass-card occurrences with card border-0 shadow-sm rounded-4
text = text.replace('<div class="glass-card p-4 shadow-sm h-100">', '<div class="card border-0 shadow-sm rounded-4 p-4 h-100" style="background-color: #FFFFFF; border: 1px solid #DEE2E6 !important;">')
text = text.replace('<div class="glass-card p-4 shadow-sm mb-4">', '<div class="card border-0 shadow-sm rounded-4 p-4 mb-4" style="background-color: #FFFFFF; border: 1px solid #DEE2E6 !important;">')
text = text.replace('<div class="glass-card ', '<div class="card border-0 shadow-sm rounded-4 ')

with open(file_path, "w", encoding="utf-8") as f:
    f.write(text)

print("dashboard.html updated successfully!")

