from django.urls import path

from .views import notification_list_view, notification_mark_all_read_view, notification_open_view

urlpatterns = [
    path("notifications/", notification_list_view, name="notification_list"),
    path(
        "notifications/<uuid:notification_id>/open/",
        notification_open_view,
        name="notification_open",
    ),
    path(
        "notifications/mark-all-read/",
        notification_mark_all_read_view,
        name="notification_mark_all_read",
    ),
]
