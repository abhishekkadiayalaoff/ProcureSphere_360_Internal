from django.urls import path

from .views import (
    bid_portal_dashboard_view,
    bid_portal_event_view,
    evaluation_dashboard_view,
    evaluation_event_view,
    sourcing_action_view,
    sourcing_attachment_download_view,
    sourcing_create_view,
    sourcing_detail_view,
    sourcing_edit_view,
    sourcing_list_view,
)

urlpatterns = [
    path("sourcing/bid-portal/", bid_portal_dashboard_view, name="bid_portal_dashboard"),
    path("sourcing/evaluation/", evaluation_dashboard_view, name="evaluation_dashboard"),
    path(
        "sourcing-events/<uuid:event_id>/bid-portal/",
        bid_portal_event_view,
        name="bid_portal_event",
    ),
    path(
        "sourcing-events/<uuid:event_id>/evaluation/",
        evaluation_event_view,
        name="evaluation_event",
    ),
    path("sourcing-events/", sourcing_list_view, name="sourcing_list"),
    path("sourcing-events/create/", sourcing_create_view, name="sourcing_create"),
    path("sourcing-events/<uuid:event_id>/", sourcing_detail_view, name="sourcing_detail"),
    path("sourcing-events/<uuid:event_id>/edit/", sourcing_edit_view, name="sourcing_edit"),
    path(
        "sourcing-events/<uuid:event_id>/actions/<slug:action>/",
        sourcing_action_view,
        name="sourcing_action",
    ),
    path(
        "sourcing-events/<uuid:event_id>/attachments/<uuid:attachment_id>/download/",
        sourcing_attachment_download_view,
        name="sourcing_attachment_download",
    ),
]
