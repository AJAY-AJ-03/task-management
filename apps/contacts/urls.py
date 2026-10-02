from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AllocateContactsView,
    ContactAllocationViewSet,
    ContactViewSet,
    ExcelUploadView,
    MyAllocationsView,
    TaskProgressView,
)

router = DefaultRouter()
router.register("contacts", ContactViewSet, basename="contact")
router.register("contact-allocations", ContactAllocationViewSet, basename="contact-allocation")

urlpatterns = [
    path("contacts/upload/", ExcelUploadView.as_view(), name="contacts-upload"),
    path("contacts/allocate/", AllocateContactsView.as_view(), name="contacts-allocate"),
    path("contacts/my-allocations/", MyAllocationsView.as_view(), name="contacts-my-allocations"),
    path("tasks/<int:pk>/progress/", TaskProgressView.as_view(), name="task-progress"),
    path("", include(router.urls)),
]
