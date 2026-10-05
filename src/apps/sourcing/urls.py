from django.urls import path

from .views import sourcing_create_view, sourcing_detail_view, sourcing_list_view

urlpatterns = [
    path("sourcing-events/", sourcing_list_view, name="sourcing_list"),
    path("sourcing-events/create/", sourcing_create_view, name="sourcing_create"),
    path("sourcing-events/<uuid:event_id>/", sourcing_detail_view, name="sourcing_detail"),
]
