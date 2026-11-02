import re

with open("templates/layouts/vendor_base.html", "r", encoding="utf-8") as f:
    text = f.read()

# Find the nav block
nav_match = re.search(r'<nav[^>]*id="vendorNav"[^>]*>([\s\S]*?)</nav>', text)
if nav_match:
    nav_content = nav_match.group(1)
    # Find all links
    links = re.findall(r'<a\s+[^>]*href="([^"]+)"[^>]*>([\s\S]*?)</a>', nav_content)
    for href, inner in links:
        icon_match = re.search(r'<i\s+class="([^"]+)"', inner)
        icon = icon_match.group(1) if icon_match else "NO_ICON"
        clean_text = " ".join(re.sub(r'<[^>]+>', ' ', inner).split())
        print(f"HREF: {href:30} | ICON: {icon:45} | LABEL: {clean_text}")

