from django.urls import path

from . import views

urlpatterns = [
    path("session/", views.SessionView.as_view(), name="auth-session"),
    path("register/", views.RegisterView.as_view(), name="auth-register"),
    path("login/", views.LoginView.as_view(), name="auth-login"),
    path("logout/", views.LogoutView.as_view(), name="auth-logout"),
]
