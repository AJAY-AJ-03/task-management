from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import EmployeeMeView, EmployeeViewSet

router = DefaultRouter()
router.register("employees", EmployeeViewSet, basename="employee")

urlpatterns = [
    path("employees/me/", EmployeeMeView.as_view(), name="employee-me"),
] + router.urls