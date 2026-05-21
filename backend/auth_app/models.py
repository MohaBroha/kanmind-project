from django.db import models
from django.contrib.auth.models import User


class Board(models.Model):
    title = models.CharField(max_length=255)
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="boards"
    )
    members = models.ManyToManyField(
        User,
        related_name='member_boards'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Task(models.Model):

    STATUS_CHOICES = [
        ("todo", "Todo"),
        ("doing", "Doing"),
        ("done", "Done"),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="todo"
    )

    priority = models.CharField(
    max_length=10,
    choices=[
        ("low", "low"),
        ("medium", "medium"),
        ("high", "high"),
    ],
    default="medium",
    )

    board = models.ForeignKey(
        Board,
        on_delete=models.CASCADE,
        related_name="tasks"
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="tasks"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title