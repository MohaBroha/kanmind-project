from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.views import APIView

from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    BoardSerializer,
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

        board = serializer.save(owner=request.user)

        return Response(BoardSerializer(board).data, status=201)


class BoardDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            board = Board.objects.get(id=pk, owner=request.user)
            board.delete()
            return Response({"message": "Board deleted"})
        except Board.DoesNotExist:
            return Response({"error": "Not found"}, status=404)


class TaskView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tasks = Task.objects.filter(owner=request.user)
        serializer = TaskSerializer(tasks, many=True)

        return Response(serializer.data)

    def post(self, request):
        serializer = TaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

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