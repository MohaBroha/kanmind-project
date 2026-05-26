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
class UserSerializer(serializers.ModelSerializer):

    fullname = serializers.CharField(source="username")

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "fullname",
        ]

class TaskSerializer(serializers.ModelSerializer):

    def validate_status(self, value):
        
        if not self.instance:
            return value

        old_status = self.instance.status

        allowed_transitions = {
            "todo": ["doing"],
            "doing": ["done", "todo"],
            "done": ["doing"],
        }

        
        if value == old_status:
            return value

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
            "priority",
            "board",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class BoardSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    ticket_count = serializers.SerializerMethodField()
    tasks_to_do_count = serializers.SerializerMethodField()
    tasks_high_prio_count = serializers.SerializerMethodField()
    owner_id = serializers.IntegerField(source="owner.id", read_only=True)

    class Meta:
        model = Board
        fields = [
            "id",
            "title",
            "member_count",
            "ticket_count",
            "tasks_to_do_count",
            "tasks_high_prio_count",
            "owner_id",
        ]

    def get_member_count(self, obj):
        return obj.members.count() if hasattr(obj, "members") else 0

    def get_ticket_count(self, obj):
        return Task.objects.filter(board=obj).count()

    def get_tasks_to_do_count(self, obj):
        return Task.objects.filter(board=obj, status="todo").count()

    def get_tasks_high_prio_count(self, obj):
        return Task.objects.filter(board=obj, priority="high").count()

class BoardDetailSerializer(serializers.ModelSerializer):

    owner_id = serializers.IntegerField(
        source="owner.id",
        read_only=True
    )

    members = UserSerializer(
        many=True,
        read_only=True
    )

    tasks = TaskSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = Board
        fields = [
            "id",
            "title",
            "owner_id",
            "members",
            "tasks",
        ]