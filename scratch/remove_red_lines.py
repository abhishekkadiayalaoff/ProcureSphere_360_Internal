# 1. Update templates/manager/dashboard.html
path_dash = "templates/manager/dashboard.html"
with open(path_dash, "r", encoding="utf-8") as f:
    text_dash = f.read()

target_dash = """                // High-risk and suspended vendor prominent border styling
                const isHighRisk = (v.current_risk_level === 'HIGH' || v.status === 'SUSPENDED');
                const rowBorderClass = isHighRisk ? 'border-start border-4 border-danger bg-danger-subtle bg-opacity-10' : '';"""

target_dash_tr = """                return `
                    <tr class="${rowBorderClass} align-middle">"""

replacement_dash_tr = """                return `
                    <tr class="align-middle">"""

text_dash_norm = text_dash.replace("\r\n", "\n")
target_dash_norm = target_dash.replace("\r\n", "\n")
target_dash_tr_norm = target_dash_tr.replace("\r\n", "\n")
replacement_dash_tr_norm = replacement_dash_tr.replace("\r\n", "\n")

assert target_dash_norm in text_dash_norm, "target_dash not found"
assert target_dash_tr_norm in text_dash_norm, "target_dash_tr not found"

text_dash_norm = text_dash_norm.replace(target_dash_norm, "")
text_dash_norm = text_dash_norm.replace(target_dash_tr_norm, replacement_dash_tr_norm)

with open(path_dash, "w", encoding="utf-8", newline="\r\n") as f:
    f.write(text_dash_norm)
print("Updated templates/manager/dashboard.html successfully!")

# 2. Update templates/manager/vendor_risk.html
path_risk = "templates/manager/vendor_risk.html"
with open(path_risk, "r", encoding="utf-8") as f:
    text_risk = f.read()

target_risk = """            const isHighRisk = (v.current_risk_level === 'HIGH' || v.status === 'SUSPENDED');
            const rowBorderClass = isHighRisk ? 'border-start border-4 border-danger bg-danger-subtle bg-opacity-10' : '';"""

target_risk_tr = """            return `
                <tr class="${rowBorderClass} align-middle">"""

replacement_risk_tr = """            return `
                <tr class="align-middle">"""

text_risk_norm = text_risk.replace("\r\n", "\n")
target_risk_norm = target_risk.replace("\r\n", "\n")
target_risk_tr_norm = target_risk_tr.replace("\r\n", "\n")
replacement_risk_tr_norm = replacement_risk_tr.replace("\r\n", "\n")

if target_risk_norm in text_risk_norm:
    text_risk_norm = text_risk_norm.replace(target_risk_norm, "")
    text_risk_norm = text_risk_norm.replace(target_risk_tr_norm, replacement_risk_tr_norm)
    with open(path_risk, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(text_risk_norm)
    print("Updated templates/manager/vendor_risk.html successfully!")

# 3. Update templates/manager/vendor_suspension.html
path_susp = "templates/manager/vendor_suspension.html"
with open(path_susp, "r", encoding="utf-8") as f:
    text_susp = f.read()

target_susp_tr = """                    <tr class="${v.current_risk_level === 'HIGH' || v.status === 'SUSPENDED' ? 'border-start border-4 border-danger bg-danger-subtle bg-opacity-10' : ''}">"""
replacement_susp_tr = """                    <tr class="align-middle">"""

text_susp_norm = text_susp.replace("\r\n", "\n")
target_susp_tr_norm = target_susp_tr.replace("\r\n", "\n")
replacement_susp_tr_norm = replacement_susp_tr.replace("\r\n", "\n")

if target_susp_tr_norm in text_susp_norm:
    text_susp_norm = text_susp_norm.replace(target_susp_tr_norm, replacement_susp_tr_norm)
    with open(path_susp, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(text_susp_norm)
    print("Updated templates/manager/vendor_suspension.html successfully!")

