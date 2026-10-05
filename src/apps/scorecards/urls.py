from django.urls import path

from .views import scorecard_list_view

urlpatterns = [
    path("scorecards/", scorecard_list_view, name="scorecard_list"),
]
