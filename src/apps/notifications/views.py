from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import Notification


@login_required(login_url="/login/")
def notification_list_view(request):
    """Internal users' in-app notifications (vendors use /vendor/notifications/)."""
    if request.user.is_vendor:
        return redirect("vendor_notifications")
    qs = Notification.objects.filter(recipient=request.user).order_by("-created_at")
    if request.GET.get("filter") == "unread":
        qs = qs.filter(is_read=False)
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "notifications/notification_list.html",
        {
            "page_obj": page,
            "notifications": page.object_list,
            "unread_count": Notification.objects.filter(
                recipient=request.user, is_read=False
            ).count(),
            "only_unread": request.GET.get("filter") == "unread",
            "querystring": "filter=unread" if request.GET.get("filter") == "unread" else "",
        },
    )


@login_required(login_url="/login/")
@require_POST
def notification_open_view(request, notification_id):
    notification = get_object_or_404(Notification, pk=notification_id, recipient=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read", "updated_at"])
    target = notification.target_url
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return redirect(target)
    return redirect("notification_list")


@login_required(login_url="/login/")
@require_POST
def notification_mark_all_read_view(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return redirect("notification_list")
