from django.urls import path
from .views import generate_view, reports_hub_view

urlpatterns = [
    path("", reports_hub_view, name="reports_dashboard"),
    path("hub/", reports_hub_view, name="reports_hub"),
    path("reports/", reports_hub_view, name="reports_hub_alias"),
    path("generate/", generate_view, name="generate_report"),
    path("reports/generate/", generate_view, name="generate_report_alias"),
]
