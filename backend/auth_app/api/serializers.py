from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import serializers
from ..models import Board, Task


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "email", "password"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            username=attrs.get("username"),
            password=attrs.get("password")
        )

        if not user:
            raise serializers.ValidationError("Invalid username or password")

        attrs["user"] = user
        return attrs


class TaskSerializer(serializers.ModelSerializer):

    def validate_status(self, value):
        # Wenn Task neu erstellt wird → keine Transition prüfen
        if not self.instance:
            return value

        old_status = self.instance.status

        allowed_transitions = {
            "todo": ["doing"],
            "doing": ["done", "todo"],
            "done": ["doing"],
        }

        # Wenn kein Wechsel passiert
        if value == old_status:
            return value

        # Prüfen ob Transition erlaubt ist
        if value not in allowed_transitions.get(old_status, []):
            raise serializers.ValidationError(
                f"Invalid status transition: {old_status} → {value}"
            )

        return value

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "status",
            "board",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class BoardSerializer(serializers.ModelSerializer):
    tasks = TaskSerializer(many=True, read_only=True)

    class Meta:
        model = Board
        fields = ["id", "title", "created_at", "tasks"]
        read_only_fields = ["id", "created_at", "tasks"]