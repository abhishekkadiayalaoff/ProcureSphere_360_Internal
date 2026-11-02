with open("templates/layouts/superadmin_base.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
m = re.search(r'<nav[^>]*id="saNav"[^>]*>([\s\S]*?)</nav>', text)
if m:
    print(m.group(1))
else:
    print("Not found")

