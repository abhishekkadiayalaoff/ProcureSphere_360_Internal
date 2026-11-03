path = "templates/layouts/superadmin_base.html"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

target = "{% block layout %}"
assert target in text

# Find the start of the style tag after {% block layout %}
style_idx = text.find("<style>", text.find(target))
assert style_idx != -1

# Replace everything from {% block layout %} to <style> with {% block layout %}\n
cleaned = text[:text.find(target) + len(target)] + "\n" + text[style_idx:]

with open(path, "w", encoding="utf-8") as f:
    f.write(cleaned)

print("Cleaned superadmin_base.html successfully!")

