from django.urls import path

from . import views

urlpatterns = [
    path("vendors/", views.vendor_list_view, name="vendor_list"),
    path("vendors/governance/", views.vendor_governance_view, name="vendor_governance"),
    path("vendors/onboarding/", views.vendor_onboarding_view, name="vendor_onboarding"),
    path("vendors/create/", views.vendor_create_view, name="vendor_create"),
    path("vendors/<uuid:vendor_id>/", views.vendor_detail_view, name="vendor_detail"),
    path(
        "vendors/<uuid:vendor_id>/status/",
        views.vendor_status_change_view,
        name="vendor_status_change",
    ),
    path(
        "vendors/<uuid:vendor_id>/risk/", views.vendor_risk_assess_view, name="vendor_risk_assess"
    ),
    path(
        "vendors/<uuid:vendor_id>/kyc/<slug:kyc_action>/",
        views.vendor_kyc_action_view,
        name="vendor_kyc_action",
    ),
    path(
        "vendors/<uuid:vendor_id>/documents/<uuid:doc_id>/download/",
        views.vendor_document_download_view,
        name="vendor_document_download",
    ),
]
