import re

path = r'ProcureSphere_360_Internal/templates/pages/dashboards/stores_dashboard.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Normalize newlines to \n
content = content.replace('\r\n', '\n')

# 1. Update hover style to not override individual border colors
old_hover = """    .kpi-card-link:hover .kpi-card {
        transform: translateY(-4px);
        box-shadow: 0 12px 24px -4px rgba(15, 23, 42, 0.12) !important;
        border-color: rgba(13, 110, 253, 0.4) !important;
    }"""

new_hover = """    .kpi-card-link:hover .kpi-card {
        transform: translateY(-4px);
        box-shadow: 0 12px 24px -4px rgba(15, 23, 42, 0.12) !important;
    }"""

if old_hover in content:
    content = content.replace(old_hover, new_hover)
    print("Hover style updated successfully.")
else:
    print("Hover style not found.")

# 2. Update 5 KPI Cards to full 2px colored border
card_replacements = [
    (
        '<div class="card kpi-card border-0 shadow-sm rounded-4 h-100 bg-white border-start border-4 border-primary">',
        '<div class="card kpi-card shadow-sm rounded-4 h-100 bg-white" style="border: 2px solid #0D6EFD !important; border-radius: 14px;">'
    ),
    (
        '<div class="card kpi-card border-0 shadow-sm rounded-4 h-100 bg-white border-start border-4 border-warning">',
        '<div class="card kpi-card shadow-sm rounded-4 h-100 bg-white" style="border: 2px solid #FFC107 !important; border-radius: 14px;">'
    ),
    (
        '<div class="card kpi-card border-0 shadow-sm rounded-4 h-100 bg-white border-start border-4 border-info">',
        '<div class="card kpi-card shadow-sm rounded-4 h-100 bg-white" style="border: 2px solid #00B8D9 !important; border-radius: 14px;">'
    ),
    (
        '<div class="card kpi-card border-0 shadow-sm rounded-4 h-100 bg-white border-start border-4 border-success">',
        '<div class="card kpi-card shadow-sm rounded-4 h-100 bg-white" style="border: 2px solid #198754 !important; border-radius: 14px;">'
    ),
    (
        '<div class="card kpi-card border-0 shadow-sm rounded-4 h-100 bg-white border-start border-4 border-danger">',
        '<div class="card kpi-card shadow-sm rounded-4 h-100 bg-white" style="border: 2px solid #DC3545 !important; border-radius: 14px;">'
    ),
]

for idx, (old, new) in enumerate(card_replacements, 1):
    if old in content:
        content = content.replace(old, new, 1)
        print(f"Card {idx} updated successfully.")
    else:
        print(f"Card {idx} NOT found!")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("All updates written.")

