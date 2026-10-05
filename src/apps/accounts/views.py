from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render

def portal_login_view(request):
    """
    Renders and processes the ProcureSphere 360 ERP Portal login form.
    Redirects authenticated users straight to the ERP Dashboard (/).
    """
    if request.user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        email = (request.POST.get("email") or request.POST.get("username") or "").strip()
        password = request.POST.get("password", "")

        if not email or not password:
            messages.error(request, "Please provide both email and password.")
            return render(request, "pages/login.html", {"email": email})

        # Explicit request=request keyword parameter is required for django-axes compatibility
        user = authenticate(request=request, username=email, password=password)

        if user is not None:
            if not user.is_active:
                messages.error(request, "Your account has been deactivated. Please contact support.")
                return render(request, "pages/login.html", {"email": email})

            login(request, user)
            next_url = request.GET.get("next") or "/"
            return redirect(next_url)
        else:
            messages.error(request, "Invalid email or password. Please try again.")

    return render(request, "pages/login.html")


def portal_logout_view(request):
    """
    Logs out the user from the ERP Portal and redirects to /login/.
    """
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect("/login/")


# Aliases for route compatibility
login_page_view = portal_login_view
logout_page_view = portal_logout_view

