with open("templates/layouts/legal_base.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = re.findall(r'<nav[^>]*>[\s\S]*?</nav>', text)
print(f"Total navs: {len(matches)}")
for i, m in enumerate(matches):
    print(f"--- NAV {i+1} ---")
    print(m[:800])
