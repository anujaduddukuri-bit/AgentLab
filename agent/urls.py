from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("tools/", views.tools_page, name="tools"),
    path("playground/", views.playground, name="playground"),
    path("playground/agent/", views.agent_playground, name="agent_playground"),
    path("tasks/", views.tasks, name="tasks"),
    path("tasks/<int:pk>/", views.challenge_detail, name="challenge_detail"),
    path("tasks/results/<int:pk>/", views.challenge_result, name="challenge_result"),
    path("activity/", views.activity, name="activity"),
    path("activity/<int:pk>/", views.activity_detail, name="activity_detail"),
    path("history/", views.history, name="history"),
    path("settings/", views.settings_page, name="settings"),
    path("learning/", views.learning, name="learning"),
    path("developer/", views.developer, name="developer"),
    path("add-a-tool/", views.add_tool_guide, name="add_tool"),
]
