path = "templates/audit/base_auditor.html"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

replacements = [
    ('<i class="fa-solid fa-fingerprint nav-icon text-cyan"></i>', '<i class="fa-solid fa-fingerprint nav-icon text-secondary"></i>'),
    ('<i class="fa-solid fa-file-contract nav-icon text-info"></i>', '<i class="fa-solid fa-file-contract nav-icon" style="color:#f97316;"></i>'),
]

for old, new in replacements:
    assert old in text, f"Target not found: {old}"
    text = text.replace(old, new, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated audit/base_auditor.html successfully!")

