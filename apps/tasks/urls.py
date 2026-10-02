from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MyTasksView, TaskActivityViewSet, TaskViewSet, TeamTasksView

router = DefaultRouter()
router.register(r"tasks", TaskViewSet, basename="task")
router.register(r"task-activities", TaskActivityViewSet, basename="task-activity")

urlpatterns = [
    path("tasks/my/", MyTasksView.as_view(), name="tasks-my"),
    path("tasks/team/", TeamTasksView.as_view(), name="tasks-team"),
    path("", include(router.urls)),
]
