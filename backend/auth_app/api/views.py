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
    TaskSerializer
)
from ..models import Board, Task

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


class BoardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        boards = Board.objects.filter(owner=request.user)
        serializer = BoardSerializer(boards, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = BoardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(owner=request.user)
        return Response(serializer.data, status=201)


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