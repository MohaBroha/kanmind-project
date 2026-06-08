from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.views import APIView
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth.models import User
from ..models import Board, Task, Comment


from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    BoardSerializer,
    BoardDetailSerializer,
    BoardPatchSerializer,
    TaskSerializer,
    CommentSerializer,
)


class RegisterView(generics.CreateAPIView):
    """
    API endpoint for user registration.

    Creates a new user account using RegisterSerializer.
    Returns authentication token and user data on success.
    """

    serializer_class = RegisterSerializer


class LoginView(generics.GenericAPIView):
    """
    API endpoint for user login.

    Authenticates user via email and password.
    Returns authentication token and basic user information.
    """

    serializer_class = LoginSerializer

    def post(self, request):
        """
        Handles user login request.

        Validates credentials and returns auth token if successful.
        """

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "fullname": user.username.replace("_", " "),
                "email": user.email,
                "user_id": user.id,
            }
        )


class UserView(APIView):
    """
    API endpoint to retrieve the currently authenticated user.

    Requires token authentication.
    Returns user id, email and formatted fullname.
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Returns the authenticated user's profile data.
        """

        return Response(
            {
                "id": request.user.id,
                "fullname": request.user.username.replace("_", " "),
                "email": request.user.email,
            }
        )


class BoardView(generics.ListCreateAPIView):
    """
    API endpoint for listing and creating boards.

    GET:
    Returns all boards where the authenticated user is owner or member.

    POST:
    Creates a new board and automatically assigns the creator as owner and member.
    """

    queryset = Board.objects.all()
    serializer_class = BoardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Returns boards where the current user is either owner or member.
        """

        return Board.objects.filter(
            Q(owner=self.request.user) | Q(members=self.request.user)
        ).distinct()

    def perform_create(self, serializer):
        """
        Creates a board and automatically adds the creator as member.
        """

        board = serializer.save(owner=self.request.user)
        board.members.add(self.request.user)


class BoardDetailView(APIView):
    """
    API endpoint for retrieving, updating and deleting a single board.

    GET:
    Returns detailed board information including members and tasks.

    PATCH:
    Updates board title and/or members if user has permission.

    DELETE:
    Deletes board (only allowed for owner).

    Access Control:
    User must be either owner or member of the board.
    """

    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        """
        Retrieves a board by ID and checks access permissions.

        Returns:
            Board object if accessible
            None if not found
            "FORBIDDEN" if user has no access
        """

        try:
            board = Board.objects.get(id=pk)
        except Board.DoesNotExist:
            return None

        if board.owner != user and not board.members.filter(id=user.id).exists():
            return "FORBIDDEN"

        return board

    def get(self, request, pk):
        """
        Returns a single board with full details.
        """

        board = self.get_object(pk, request.user)

        if board is None:
            return Response({"error": "Board not found"}, status=404)

        if board == "FORBIDDEN":
            return Response({"error": "Forbidden"}, status=403)

        serializer = BoardDetailSerializer(board)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        """
        Partially updates board data (title and/or members).
        """

        board = self.get_object(pk, request.user)

        if board is None:
            return Response(
                {"error": "Board not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if board == "FORBIDDEN":
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        data = request.data

        if "title" in data:
            board.title = data["title"]

        if "members" in data:
            member_ids = data["members"]

            users = User.objects.filter(id__in=member_ids)

            if len(users) != len(member_ids):
                return Response(
                    {"error": "One or more users not found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            board.members.set(users)

        board.save()
        serializer = BoardPatchSerializer(board)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        """
        Deletes a board if the user is the owner.
        """

        board = self.get_object(pk, request.user)

        if board is None:
            return Response(
                {"error": "Board not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if board == "FORBIDDEN":
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        if board.owner != request.user:
            return Response(
                {"error": "Only owner can delete board"},
                status=status.HTTP_403_FORBIDDEN,
            )

        board.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskView(APIView):
    """
    API endpoint for listing and creating tasks.

    GET:
    Returns all tasks accessible by the authenticated user.
    Optional filtering by status via query parameter.

    POST:
    Creates a new task inside a board.
    User must be owner or member of the board.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Returns a list of tasks accessible by the current user.

        Optional Query Params:
        - status: filters tasks by status (e.g. 'todo', 'in-progress')
        """

        status_param = request.query_params.get("status")

        tasks = Task.objects.filter(
            Q(board__owner=request.user) | Q(board__members=request.user)
        ).distinct()

        if status_param:
            tasks = tasks.filter(status=status_param)

        serializer = TaskSerializer(tasks, many=True)

        return Response(serializer.data)

    def post(self, request):
        """
        Creates a new task in a board.

        Validates board existence and user permissions.
        Automatically assigns the requesting user as task owner.
        """

        board_id = request.data.get("board")

        try:
            board = Board.objects.get(id=board_id)
        except Board.DoesNotExist:
            return Response(
                {"error": "Board not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if (
            not Board.objects.filter(id=board_id, members=request.user).exists()
            and not Board.objects.filter(id=board_id, owner=request.user).exists()
        ):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        serializer = TaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task = serializer.save(owner=request.user)

        return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)


class TaskDetailView(APIView):
    """
    API endpoint for retrieving, updating and deleting a single task.

    GET:
    Returns task details if user has access to the board.

    PATCH:
    Partially updates a task if user has permission.

    DELETE:
    Deletes a task if user has permission.

    Access Control:
    Only board owner or board members can access tasks.
    """

    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        """
        Retrieves a task by ID.

        Returns:
            Task object if exists
            Raises Task.DoesNotExist if not found
        """

        return Task.objects.get(id=pk)

    def get(self, request, pk):
        """
        Returns a single task if user has access.
        """

        try:
            task = self.get_object(pk)

            allowed = (
                task.board.owner == request.user
                or task.board.members.filter(id=request.user.id).exists()
            )

            if not allowed:
                return Response({"error": "Forbidden"}, status=403)

            serializer = TaskSerializer(task)
            return Response(serializer.data)

        except Task.DoesNotExist:
            return Response({"error": "Task not found"}, status=404)

    def patch(self, request, pk):
        """
        Partially updates a task.
        """

        try:
            task = self.get_object(pk)

            allowed = (
                task.board.owner == request.user
                or task.board.members.filter(id=request.user.id).exists()
            )

            if not allowed:
                return Response({"error": "Forbidden"}, status=403)

            serializer = TaskSerializer(task, data=request.data, partial=True)

            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(serializer.data)

        except Task.DoesNotExist:
            return Response({"error": "Task not found"}, status=404)

    def delete(self, request, pk):
        """
        Deletes a task if user has permission.
        """

        try:
            task = self.get_object(pk)

            allowed = (
                task.board.owner == request.user
                or task.board.members.filter(id=request.user.id).exists()
            )

            if not allowed:
                return Response({"error": "Forbidden"}, status=403)

            task.delete()

            return Response(status=204)

        except Task.DoesNotExist:
            return Response({"error": "Task not found"}, status=404)


class AssignedToMeView(APIView):
    """
    API endpoint to retrieve tasks assigned to the authenticated user.

    GET:
    Returns all tasks where the current user is set as assignee.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Returns all tasks assigned to the current user.
        """

        user = request.user

        tasks = Task.objects.filter(assignee=user)

        serializer = TaskSerializer(tasks, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


class EmailCheckView(APIView):
    """
    API endpoint to check if a user exists by email.

    GET:
    Returns user information (id, email, fullname) if email exists.

    Query Params:
    - email: email address to search for

    Errors:
    - 400 if email is missing
    - 404 if user not found
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Checks if a user exists by email and returns user data.
        """

        email = request.query_params.get("email")

        if not email:
            return Response({"error": "email required"}, status=400)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "not found"}, status=404)

        return Response(
            {
                "id": user.id,
                "email": user.email,
                "fullname": user.username.replace("_", " "),
            }
        )


class CommentListCreateView(APIView):
    """
    API endpoint for listing and creating comments for a specific task.

    GET:
    Returns all comments for a task if the user is a member of the board.

    POST:
    Creates a new comment for a task.
    The author is automatically set to the authenticated user.

    Access Control:
    Only board members are allowed to view or create comments.
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_task(self, task_id, user):
        """
        Retrieves a task and checks if the user has access via board membership.
        """

        task = Task.objects.get(id=task_id)

        if user not in task.board.members.all():
            raise PermissionDenied("You are not a member of this board")

        return task

    def get(self, request, task_id):
        """
        Returns all comments for a given task.
        """

        try:
            task = self.get_task(task_id, request.user)
        except Task.DoesNotExist:
            return Response(
                {"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND
            )

        comments = task.comments.all().order_by("created_at")
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

    def post(self, request, task_id):
        """
        Creates a new comment for a task.
        """

        try:
            task = self.get_task(task_id, request.user)
        except Task.DoesNotExist:
            return Response(
                {"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = CommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(task=task, author=request.user)

        return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)


class CommentDetailView(APIView):
    """
    API endpoint for deleting a single comment.

    DELETE:
    Deletes a comment if the user is authorized.

    Access Control:
    Only the comment author or the board owner can delete a comment.
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, task_id, comment_id):
        """
        Deletes a comment if it belongs to the given task and user has permission.
        """

        try:
            comment = Comment.objects.get(id=comment_id, task__id=task_id)

        except Comment.DoesNotExist:
            return Response(
                {"error": "Comment not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if request.user != comment.author and request.user != comment.task.board.owner:
            return Response(status=403)

        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
