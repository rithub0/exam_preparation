from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("accounts/signup/", views.signup, name="signup"),
    # 模擬試験
    path("mock/start/", views.mock_start, name="mock_start"),
    path("mock/session/", views.mock_session, name="mock_session"),
    path("mock/result/", views.mock_result, name="mock_result"),
]
