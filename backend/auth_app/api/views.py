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
    serializer_class = RegisterSerializer


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request):
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


class MeView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "id": request.user.id,
                "fullname": request.user.username.replace("_", " "),
                "email": request.user.email,
            }
        )


class BoardView(generics.ListCreateAPIView):
    queryset = Board.objects.all()
    serializer_class = BoardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Board.objects.filter(
            Q(owner=self.request.user) | Q(members=self.request.user)
        ).distinct()

    def perform_create(self, serializer):
        board = serializer.save(owner=self.request.user)
        board.members.add(self.request.user)


class BoardDetailView(APIView):

    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            board = Board.objects.get(id=pk)
        except Board.DoesNotExist:
            return None

        if board.owner != user and not board.members.filter(id=user.id).exists():
            return "FORBIDDEN"

        return board

    def get(self, request, pk):

        board = self.get_object(pk, request.user)

        if board is None:
            return Response({"error": "Board not found"}, status=404)

        if board == "FORBIDDEN":
            return Response({"error": "Forbidden"}, status=403)

        serializer = BoardDetailSerializer(board)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):

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
    permission_classes = [IsAuthenticated]

    def get(self, request):

        status_param = request.query_params.get("status")

        tasks = Task.objects.filter(
            Q(board__owner=request.user) | Q(board__members=request.user)
        ).distinct()

        if status_param:
            tasks = tasks.filter(status=status_param)

        serializer = TaskSerializer(tasks, many=True)

        return Response(serializer.data)

    def post(self, request):
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
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return Task.objects.get(id=pk)

    def get(self, request, pk):
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
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        tasks = Task.objects.filter(assignee=user)

        serializer = TaskSerializer(tasks, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


class EmailCheckView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
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
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_task(self, task_id, user):
        task = Task.objects.get(id=task_id)

        if user not in task.board.members.all():
            raise PermissionDenied("You are not a member of this board")

        return task

    def get(self, request, task_id):
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
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, task_id, comment_id):
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
