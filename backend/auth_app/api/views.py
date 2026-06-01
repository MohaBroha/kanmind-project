from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.views import APIView
from django.db.models import Q
from django.contrib.auth.models import User

from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    BoardSerializer,
    BoardDetailSerializer,
    TaskSerializer,
    CommentSerializer,
)
from ..models import Board, Task, Comment

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            "token": token.key,
            "user": {
                "username": user.username,
                "email": user.email,
            }
        })


class MeView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "id": request.user.id,
            "username": request.user.username,
            "email": request.user.email
        })


class BoardView(generics.ListCreateAPIView):
    queryset = Board.objects.all()
    serializer_class = BoardSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class BoardDetailView(APIView):

    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            return Board.objects.get(
                Q(id=pk) & (Q(owner=user) | Q(members=user))
            )
        except Board.DoesNotExist:
            return None

    
    def get(self, request, pk):

        board = self.get_object(pk, request.user)

        if not board:
            return Response(
                {"error": "Board not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = BoardDetailSerializer(board)
        return Response(serializer.data, status=status.HTTP_200_OK)

    
    def patch(self, request, pk):

        board = self.get_object(pk, request.user)

        if not board:
            return Response(
                {"error": "Board not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        
        if request.user != board.owner:
            return Response(
                {"error": "Only owner can update board"},
                status=status.HTTP_403_FORBIDDEN
            )

        data = request.data

        
        if "title" in data:
            board.title = data["title"]

        
        if "members" in data:
            member_ids = data["members"]

            users = User.objects.filter(id__in=member_ids)

            if len(users) != len(member_ids):
                return Response(
                    {"error": "One or more users not found"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            board.members.set(users)

        board.save()

        return Response({
            "id": board.id,
            "title": board.title,
            "owner_id": board.owner.id,
            "members": [
                {
                    "id": u.id,
                    "email": u.email,
                    "username": u.username
                }
                for u in board.members.all()
            ]
        }, status=status.HTTP_200_OK)

    
    def delete(self, request, pk):

        board = self.get_object(pk, request.user)

        if not board:
            return Response(
                {"error": "Board not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        
        if board.owner != request.user:
            return Response(
                {"error": "Only owner can delete board"},
                status=status.HTTP_403_FORBIDDEN
            )

        board.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        status_param = request.query_params.get("status")

        tasks = Task.objects.filter(board__owner=request.user)

        if status_param:
            tasks = tasks.filter(status=status_param)

        serializer = TaskSerializer(tasks, many=True)

        return Response(serializer.data)

    def post(self, request):
        serializer = TaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        board_id = request.data.get("board")

        if not Board.objects.filter(id=board_id, owner=request.user).exists():
            return Response(
                {"error": "Invalid board"},
                status=status.HTTP_403_FORBIDDEN
            )

        task = serializer.save(owner=request.user)

        return Response(
            TaskSerializer(task).data,
            status=status.HTTP_201_CREATED
        )


class TaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        return Task.objects.get(id=pk, board__owner=user)

    def get(self, request, pk):
        try:
            task = self.get_object(pk, request.user)
            serializer = TaskSerializer(task)
            return Response(serializer.data)
        except Task.DoesNotExist:
            return Response(
                {"error": "Task not found"},
                status=404
            )

    def patch(self, request, pk):
        try:
            task = self.get_object(pk, request.user)

            serializer = TaskSerializer(
                task,
                data=request.data,
                partial=True
            )

            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(serializer.data)

        except Task.DoesNotExist:
            return Response(
                {"error": "Task not found"},
                status=404
            )

    def delete(self, request, pk):
        try:
            task = self.get_object(pk, request.user)
            task.delete()

            return Response(
                {"message": "Task deleted"},
                status=204
            )

        except Task.DoesNotExist:
            return Response(
                {"error": "Task not found"},
                status=404
            )


class CommentListCreateView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_task(self, task_id, user):
        return Task.objects.get(id=task_id, board__owner=user)

    def get(self, request, task_id):
        try:
            task = self.get_task(task_id, request.user)
        except Task.DoesNotExist:
            return Response(
                {"error": "Task not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        comments = task.comments.all().order_by("created_at")
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

    def post(self, request, task_id):
        try:
            task = self.get_task(task_id, request.user)
        except Task.DoesNotExist:
            return Response(
                {"error": "Task not found"},
                status=status.HTTP_404_NOT_FOUND
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
            comment = Comment.objects.get(
                id=comment_id,
                task__id=task_id,
                task__board__owner=request.user
            )
        except Comment.DoesNotExist:
            return Response(
                {"error": "Comment not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        if comment.author != request.user and comment.task.board.owner != request.user:
            return Response(
                {"error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN
            )

        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
