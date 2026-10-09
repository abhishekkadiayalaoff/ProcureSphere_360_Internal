from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.accounts.models import User

from .models import Notification
from .selectors import get_recent_unread_notifications


def notify_users(*, users, notification_type: str, title: str, message: str, target_url: str = ""):
    """
    Creates one in-app Notification per active recipient. Returns the created notifications.
    """
    notifications = [
        Notification(
            recipient=user,
            notification_type=notification_type,
            title=title[:200],
            message=message,
            target_url=target_url[:255],
        )
        for user in users
        if user.is_active
    ]
    return Notification.objects.bulk_create(notifications)


def notify_vendor_users(*, vendor, notification_type: str, title: str, message: str, target_url=""):
    """Notifies every portal user linked to the given vendor."""
    users = User.objects.filter(vendor=vendor, is_active=True)
    return notify_users(
        users=users,
        notification_type=notification_type,
        title=title,
        message=message,
        target_url=target_url,
    )


def notify_role_users(
    *, role_codes, notification_type: str, title: str, message: str, target_url=""
):
    """Notifies every active user holding one of the given role codes."""
    users = User.objects.filter(role__code__in=role_codes, is_active=True)
    return notify_users(
        users=users,
        notification_type=notification_type,
        title=title,
        message=message,
        target_url=target_url,
    )


def get_top_unread_for_user(*, user, limit: int = 10):
    """Service-layer fetch of the top-N recent unread notifications.

    Read path goes through ``selectors``; this wrapper keeps views thin and
    gives callers a single domain entry-point (enforces authenticated user).
    """
    if user is None or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required to read notifications.")
    return get_recent_unread_notifications(user, limit=limit)


@transaction.atomic
def mark_notification_as_read(*, user, notification_id) -> Notification:
    """Mark one notification read. RBAC: only the recipient may mutate it.

    Raises:
        PermissionDenied: unauthenticated caller.
        Notification.DoesNotExist: id unknown OR owned by another user
            (deliberately indistinguishable to prevent ID enumeration).
    """
    if user is None or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required to update notifications.")
    notification = Notification.objects.select_for_update().get(pk=notification_id, recipient=user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read", "updated_at"])
    return notification
