file_path = r"c:\Users\windows10\Desktop\PRO 360\ProcureSphere_360_Internal\templates\manager\base_manager.html"

with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

old_btn = """<button class="navbar-toggler border-0 me-2 d-lg-none p-1" type="button" data-bs-toggle="offcanvas" data-bs-target="#managerSidebar" aria-controls="managerSidebar" aria-label="Toggle navigation">"""
new_btn = """<button class="btn btn-dark border-0 me-2 d-flex d-lg-none p-1 align-items-center justify-content-center" type="button" data-bs-toggle="offcanvas" data-bs-target="#managerSidebar" aria-controls="managerSidebar" aria-label="Toggle navigation">"""

if old_btn in text:
    text = text.replace(old_btn, new_btn)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)
    print("Updated mobile button in base_manager.html successfully!")
else:
    print("Target old_btn not found.")

