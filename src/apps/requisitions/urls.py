from django.urls import path
from . import views

urlpatterns = [
    path("requisitions/", views.list_view, name="requisitions_list"),
    path("", views.list_view, name="requisitions_list_root"),
    path("create/", views.create_view, name="requisition_create"),
    path("<uuid:pk>/", views.detail_view, name="requisition_detail"),
    path("<uuid:pk>/edit/", views.edit_view, name="requisition_edit"),
    path("<uuid:pk>/submit/", views.submit_view, name="requisition_submit"),
    path("<uuid:pk>/cancel/", views.cancel_view, name="requisition_cancel"),
]
