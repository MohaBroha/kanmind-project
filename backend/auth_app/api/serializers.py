from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import serializers
from auth_app.models import Board, Task, Comment


class RegisterSerializer(serializers.Serializer):
    fullname = serializers.CharField(write_only=True)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    repeated_password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        if "username" in self.initial_data:
            raise serializers.ValidationError({"username": "Field 'username' is not allowed. Use 'fullname' instead."})
        if attrs["password"] != attrs["repeated_password"]:
            raise serializers.ValidationError("Passwords do not match")
        return attrs

    def create(self, validated_data):
        validated_data.pop("repeated_password")
        fullname = validated_data.pop("fullname")
        username = fullname.replace(" ", "_").strip() or "user"
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
        user = User.objects.create_user(
            username=username,
            email=validated_data["email"],
            password=validated_data["password"]
        )
        user._generated_fullname = fullname

        from rest_framework.authtoken.models import Token
        token, _ = Token.objects.get_or_create(user=user)
        user._generated_token = token.key
        return user

    def to_representation(self, instance):
        return {
            "token": instance._generated_token,
            "fullname": instance._generated_fullname,
            "email": instance.email,
            "user_id": instance.id,
        }


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        user = User.objects.filter(email=email).first()

        if user is None:
            raise serializers.ValidationError("Invalid email or password")

        user = authenticate(username=user.username, password=password)

        if not user:
            raise serializers.ValidationError("Invalid email or password")

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


class BoardSerializer(serializers.ModelSerializer):
    owner_id = serializers.IntegerField(source="owner.id", read_only=True)

    member_count = serializers.SerializerMethodField()
    ticket_count = serializers.SerializerMethodField()
    tasks_to_do_count = serializers.SerializerMethodField()
    tasks_high_prio_count = serializers.SerializerMethodField()

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
        return obj.members.count()

    def get_ticket_count(self, obj):
        return obj.tasks.count()

    def get_tasks_to_do_count(self, obj):
        return obj.tasks.filter(status="todo").count()

    def get_tasks_high_prio_count(self, obj):
        return obj.tasks.filter(priority="high").count()


class TaskSerializer(serializers.ModelSerializer):

    assignee_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    reviewer_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    def validate_status(self, value):
        allowed_statuses = ["todo", "doing", "done"]
        if value not in allowed_statuses:
            raise serializers.ValidationError(
                f"Invalid status: {value}. Must be one of {allowed_statuses}"
            )
        return value

    def validate(self, attrs):
        board = attrs.get("board")
        assignee_id = attrs.pop("assignee_id", None) if not self.instance else self.initial_data.get("assignee_id")
        reviewer_id = attrs.pop("reviewer_id", None) if not self.instance else self.initial_data.get("reviewer_id")

        if board:
            board_obj = board if isinstance(board, Board) else Board.objects.get(id=board)
            member_ids = list(board_obj.members.values_list("id", flat=True)) + [board_obj.owner.id]

            if assignee_id is not None:
                assignee_id = int(assignee_id)
                if assignee_id not in member_ids:
                    raise serializers.ValidationError({"assignee_id": "Assignee must be a board member"})
                attrs["assignee_id"] = assignee_id

            if reviewer_id is not None:
                reviewer_id = int(reviewer_id)
                if reviewer_id not in member_ids:
                    raise serializers.ValidationError({"reviewer_id": "Reviewer must be a board member"})
                attrs["reviewer_id"] = reviewer_id

        return attrs

    def create(self, validated_data):
        assignee_id = validated_data.pop("assignee_id", None)
        reviewer_id = validated_data.pop("reviewer_id", None)

        if assignee_id is not None:
            validated_data["assignee_id"] = assignee_id
        if reviewer_id is not None:
            validated_data["reviewer_id"] = reviewer_id

        return super().create(validated_data)

    def update(self, instance, validated_data):
        assignee_id = validated_data.pop("assignee_id", None)
        reviewer_id = validated_data.pop("reviewer_id", None)
        if assignee_id is not None:
            validated_data["assignee_id"] = assignee_id
        if reviewer_id is not None:
            validated_data["reviewer_id"] = reviewer_id
        return super().update(instance, validated_data)

    class Meta:
        model = Task
        fields = "__all__"
        read_only_fields = ["id", "created_at", "owner"]


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "created_at", "author", "content"]
        read_only_fields = ["id", "created_at", "author"]

    def get_author(self, obj):
        name = obj.author.get_full_name().strip()
        return name if name else obj.author.username


class BoardListSerializer(serializers.ModelSerializer):
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
        return Task.objects.filter(board=obj, status="to-do").count()

    def get_tasks_high_prio_count(self, obj):
        return Task.objects.filter(board=obj, priority="high").count()


class BoardDetailSerializer(serializers.ModelSerializer):
    owner_id = serializers.IntegerField(source="owner.id", read_only=True)
    members = UserSerializer(many=True, read_only=True)
    tasks = TaskSerializer(many=True, read_only=True)

    class Meta:
        model = Board
        fields = [
            "id",
            "title",
            "owner_id",
            "members",
            "tasks",
        ]