path = "templates/layouts/approver_base.html"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

replacements = [
    ('<i class="fa-solid fa-square-check nav-icon text-cyan"></i>', '<i class="fa-solid fa-square-check nav-icon text-warning"></i>'),
    ('<i class="fa-solid fa-list nav-icon text-cyan"></i>', '<i class="fa-solid fa-file-lines nav-icon text-info"></i>'),
    ('<i class="fa-solid fa-timeline nav-icon text-cyan"></i>', '<i class="fa-solid fa-clock-rotate-left nav-icon text-secondary"></i>'),
]

for old, new in replacements:
    assert old in text, f"Target not found: {old}"
    text = text.replace(old, new, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated layouts/approver_base.html successfully!")

