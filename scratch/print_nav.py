import re

with open("templates/manager/base_manager.html", "r", encoding="utf-8") as f:
    text = f.read()

m = re.search(r'<nav[^>]*id="managerNav"[^>]*>([\s\S]*?)</nav>', text)
if m:
    print(m.group(1))
else:
    print("Not found")

