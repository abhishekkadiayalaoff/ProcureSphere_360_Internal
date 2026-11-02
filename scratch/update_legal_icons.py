path = "templates/layouts/legal_base.html"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

replacements = [
    ('<i class="fa-solid fa-file-contract nav-icon text-info"></i>', '<i class="fa-solid fa-file-contract nav-icon" style="color:#f97316;"></i>'),
    ('<i class="fa-solid fa-id-card nav-icon text-success"></i>', '<i class="fa-solid fa-id-card nav-icon text-info"></i>'),
    ('<i class="fa-solid fa-clock-rotate-left nav-icon text-warning"></i>', '<i class="fa-solid fa-square-check nav-icon text-warning"></i>'),
    ('<i class="fa-solid fa-gavel nav-icon text-info"></i>', '<i class="fa-solid fa-gavel nav-icon text-warning"></i>'),
    ('<i class="fa-solid fa-chart-line nav-icon text-cyan"></i>', '<i class="fa-solid fa-chart-line nav-icon text-secondary"></i>'),
]

for old, new in replacements:
    assert old in text, f"Target not found: {old}"
    text = text.replace(old, new, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated layouts/legal_base.html successfully!")

