file_path = r"c:\Users\windows10\Desktop\PRO 360\ProcureSphere_360_Internal\templates\manager\base_manager.html"

with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

old_dash_link = """<a href="/manager/" class="manager-nav-link {% if request.path == '/manager/' %}active{% endif %}">"""
new_dash_link = """<a href="/manager/" class="manager-nav-link {% if request.path == '/manager/' or request.path == '/' %}active{% endif %}">"""

if old_dash_link in text:
    text = text.replace(old_dash_link, new_dash_link)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)
    print("Updated Executive Dashboard active link successfully!")
else:
    print("Target link not found.")

