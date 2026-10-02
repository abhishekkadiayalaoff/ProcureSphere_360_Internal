from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard_view, name="reports_dashboard"),
    path("generate/", views.generate_view, name="generate_report"),
]
