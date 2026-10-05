from django.urls import path
from .views import generate_view, reports_hub_view

urlpatterns = [
    path("reports/", reports_hub_view, name="reports_hub"),
    path("reports/generate/", generate_view, name="generate_report"),
    path("", reports_hub_view, name="reports_dashboard"),
]
