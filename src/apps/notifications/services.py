from apps.accounts.models import User

from .models import Notification


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
