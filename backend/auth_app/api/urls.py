from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    MeView,
    BoardView,
    BoardDetailView,
    TaskView,
    TaskDetailView,
)



urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("login/", LoginView.as_view()),
    path("me/", MeView.as_view()),

    path("boards/", BoardView.as_view()),
    path("boards/<int:pk>/", BoardDetailView.as_view()),
    
    path("tasks/", TaskView.as_view()),
    path("tasks/<int:pk>/", TaskDetailView.as_view()),
]