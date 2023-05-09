from django.urls import path

from .views import GithubCallbackView

urlpatterns = [
    path("gh/callback", GithubCallbackView.as_view(), name="github-callback"),
]
