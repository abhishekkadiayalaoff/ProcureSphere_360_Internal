with open("templates/layouts/stores_base.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = re.findall(r'<nav[^>]*>[\s\S]*?</nav>', text)
for i, m in enumerate(matches):
    print(f"--- NAV {i+1} ---")
    print(m[:800])
