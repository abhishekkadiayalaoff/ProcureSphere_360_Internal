file_path = r"c:\Users\windows10\Desktop\PRO 360\ProcureSphere_360_Internal\templates\pages\dashboards\procurement_dashboard.html"

with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update intake banner and executive workspace card
old_snippet = """<div class="card border-0 shadow-sm rounded-4 mb-4 bg-primary bg-opacity-10 border-start border-primary border-4 overflow-hidden">"""
new_snippet = """<div class="card border-0 shadow-sm rounded-4 mb-4 overflow-hidden" style="background-color: rgba(13, 110, 253, 0.05); border: 1px solid rgba(13, 110, 253, 0.2) !important; border-radius: 12px;">"""

text = text.replace(old_snippet, new_snippet)

# 2. Executive workspace card
old_card = """<div class="glass-card p-3 p-md-4 shadow-sm mb-4">"""
new_card = """<div class="card border-0 shadow-sm rounded-4 p-3 p-md-4 mb-4" style="border: 1px solid #DEE2E6 !important; background-color: #FFFFFF;">"""
text = text.replace(old_card, new_card)

# 3. Yellow button in workspace header
old_btn = """<button class="btn btn-sm btn-warning text-dark rounded-pill fw-bold px-3\""""
new_btn = """<button class="btn btn-sm btn-primary rounded-pill fw-bold px-3 shadow-sm\""""
text = text.replace(old_btn, new_btn)

# 4. Other glass-card occurrences
old_glass_other = """<div class="glass-card p-3 p-md-4 shadow-sm h-100">"""
new_glass_other = """<div class="card border-0 shadow-sm rounded-4 p-3 p-md-4 h-100" style="border: 1px solid #DEE2E6 !important; background-color: #FFFFFF;">"""
text = text.replace(old_glass_other, new_glass_other)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated procurement_dashboard.html successfully!")

