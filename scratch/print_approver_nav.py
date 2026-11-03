with open("templates/layouts/approver_base.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
m = re.search(r'<nav[^>]*id="approverNav"[^>]*>([\s\S]*?)</nav>', text)
if m:
    print(m.group(1))
else:
    print("Not found")

