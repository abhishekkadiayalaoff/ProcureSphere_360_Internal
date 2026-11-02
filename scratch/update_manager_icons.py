path = "templates/manager/base_manager.html"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# Replace manager nav items
replacements = [
    ('<i class="fa-solid fa-square-check nav-icon text-cyan"></i>', '<i class="fa-solid fa-square-check nav-icon text-warning"></i>'),
    ('<i class="fa-solid fa-clock-rotate-left nav-icon text-cyan"></i>', '<i class="fa-solid fa-clock-rotate-left nav-icon text-warning"></i>'),
    ('<i class="fa-solid fa-gavel nav-icon text-cyan"></i>', '<i class="fa-solid fa-gavel nav-icon text-warning"></i>'),
    ('<i class="fa-solid fa-award nav-icon text-cyan"></i>', '<i class="fa-solid fa-award nav-icon text-warning"></i>'),
    ('<i class="fa-solid fa-shield-halved nav-icon text-cyan"></i>', '<i class="fa-solid fa-shield-halved nav-icon text-danger"></i>'),
    ('<i class="fa-solid fa-scale-balanced nav-icon text-cyan"></i>', '<i class="fa-solid fa-scale-balanced nav-icon text-danger"></i>'),
    ('<i class="fa-solid fa-star-half-stroke nav-icon text-cyan"></i>', '<i class="fa-solid fa-chart-line nav-icon text-success"></i>'),
    ('<i class="fa-solid fa-chart-line nav-icon text-cyan"></i>', '<i class="fa-solid fa-chart-pie nav-icon text-success"></i>'),
    ('<i class="fa-solid fa-bell nav-icon text-cyan"></i>', '<i class="fa-solid fa-bell nav-icon text-warning"></i>'),
]

for old, new in replacements:
    assert old in text, f"Target not found: {old}"
    text = text.replace(old, new, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated manager/base_manager.html successfully!")

