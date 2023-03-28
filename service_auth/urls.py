from django.urls import path

from .views import gh_callback

urlpatterns = [
    path("/gh/callback", gh_callback, name="gh_callback"),
]