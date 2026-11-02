path = "templates/layouts/vendor_base.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

target = """            <!-- Security Footnote -->
            <div class="mt-4 pt-3 border-top border-secondary border-opacity-25 px-2 mb-2">
                <div class="d-flex align-items-center text-white-50 small" style="font-size: 0.68rem;">
                    <i class="fa-solid fa-lock text-success me-2"></i>
                    <span>RBAC Backend Enforced &bull; Sealed Bids</span>
                </div>
            </div>"""

content_norm = content.replace("\r\n", "\n")
target_norm = target.replace("\r\n", "\n")

assert target_norm in content_norm, "Target not found in vendor_base.html"
cleaned = content_norm.replace(target_norm + "\n", "")

with open(path, "w", encoding="utf-8", newline="\r\n") as f:
    f.write(cleaned)

print("Successfully removed footnote from vendor_base.html")

