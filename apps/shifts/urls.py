from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import EmployeeShiftViewSet, MyShiftView, ShiftViewSet

router = DefaultRouter()
router.register(r"shifts", ShiftViewSet, basename="shift")
router.register(r"employee-shifts", EmployeeShiftViewSet, basename="employee-shift")

urlpatterns = [
    path("my-shift/", MyShiftView.as_view(), name="my-shift"),
    path("", include(router.urls)),
]
