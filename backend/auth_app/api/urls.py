from django.urls import path
from .views import (
    AssignedToMeView,
    EmailCheckView,
    RegisterView,
    LoginView,
    MeView,
    BoardView,
    BoardDetailView,
    TaskView,
    TaskDetailView,
    CommentListCreateView,
    CommentDetailView,
)



urlpatterns = [
    path("registration/", RegisterView.as_view()),
    path("login/", LoginView.as_view()),
    path("me/", MeView.as_view()),

    path("boards/", BoardView.as_view()),
    path("boards/<int:pk>/", BoardDetailView.as_view()),
    
    path("tasks/assigned-to-me/",AssignedToMeView.as_view()),
    path("tasks/reviewing/", AssignedToMeView.as_view()),
    path("email-check/", EmailCheckView.as_view()),

    path("tasks/", TaskView.as_view()),
    path("tasks/<int:pk>/", TaskDetailView.as_view()),
    path("tasks/<int:task_id>/comments/", CommentListCreateView.as_view()),
    path("tasks/<int:task_id>/comments/<int:comment_id>/", CommentDetailView.as_view()),
]