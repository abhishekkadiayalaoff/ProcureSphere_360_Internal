from django.urls import path

from . import views

urlpatterns = [
    path("requisitions/", views.list_view, name="requisitions_list"),
    path("requisitions/create/", views.create_view, name="requisition_create_alt"),
    path("requisitions/<uuid:pk>/", views.detail_view, name="requisition_detail_alt"),
    path("requisitions/<uuid:pk>/edit/", views.edit_view, name="requisition_edit_alt"),
    path("requisitions/<uuid:pk>/submit/", views.submit_view, name="requisition_submit_alt"),
    path("requisitions/<uuid:pk>/cancel/", views.cancel_view, name="requisition_cancel_alt"),
    path("", views.list_view, name="requisitions_list_root"),
    path("create/", views.create_view, name="requisition_create"),
    path("<uuid:pk>/", views.detail_view, name="requisition_detail"),
    path("<uuid:pk>/edit/", views.edit_view, name="requisition_edit"),
    path("<uuid:pk>/submit/", views.submit_view, name="requisition_submit"),
    path("<uuid:pk>/cancel/", views.cancel_view, name="requisition_cancel"),
]
