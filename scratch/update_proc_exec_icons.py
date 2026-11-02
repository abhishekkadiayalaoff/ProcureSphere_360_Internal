path = "templates/partials/proc_exec_sidebar.html"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

replacements = [
    ('<i class="fa-solid fa-id-card nav-icon text-cyan"></i>', '<i class="fa-solid fa-id-card nav-icon text-info"></i>'),
    ('<i class="fa-solid fa-building-user nav-icon text-cyan"></i>', '<i class="fa-solid fa-building-user nav-icon text-success"></i>'),
    ('<i class="fa-solid fa-shield-halved nav-icon text-cyan"></i>', '<i class="fa-solid fa-shield-halved nav-icon text-danger"></i>'),
    ('<i class="fa-solid fa-gavel nav-icon text-cyan"></i>', '<i class="fa-solid fa-gavel nav-icon text-warning"></i>'),
    ('<i class="fa-solid fa-envelope-open-text nav-icon text-cyan"></i>', '<i class="fa-solid fa-file-invoice-dollar nav-icon text-success"></i>'),
    ('<i class="fa-solid fa-scale-balanced nav-icon text-cyan"></i>', '<i class="fa-solid fa-award nav-icon text-warning"></i>'),
    ('<i class="fa-solid fa-file-invoice-dollar nav-icon text-cyan"></i>', '<i class="fa-solid fa-file-invoice nav-icon" style="color:#a78bfa;"></i>'),
    ('<i class="fa-solid fa-award nav-icon text-cyan"></i>', '<i class="fa-solid fa-chart-line nav-icon text-success"></i>'),
    ('<i class="fa-solid fa-bell nav-icon text-cyan"></i>', '<i class="fa-solid fa-bell nav-icon text-warning"></i>'),
    ('<i class="fa-solid fa-clock-rotate-left nav-icon text-cyan"></i>', '<i class="fa-solid fa-clock-rotate-left nav-icon text-warning"></i>'),
    ('<i class="fa-solid fa-chart-column nav-icon text-cyan"></i>', '<i class="fa-solid fa-chart-column nav-icon text-info"></i>'),
    ('<i class="fa-solid fa-clipboard-check nav-icon text-cyan"></i>', '<i class="fa-solid fa-clipboard-check nav-icon text-success"></i>'),
    ('<i class="fa-solid fa-fingerprint nav-icon text-cyan"></i>', '<i class="fa-solid fa-fingerprint nav-icon text-secondary"></i>'),
]

for old, new in replacements:
    assert old in text, f"Target not found: {old}"
    text = text.replace(old, new, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated partials/proc_exec_sidebar.html successfully!")

