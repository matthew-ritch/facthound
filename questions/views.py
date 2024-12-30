import datetime
import pytz
import secrets

from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from rest_framework import viewsets

from questions.models import Thread, Post, Question, Answer, Tag
from siweauth.models import Wallet, Nonce

from questions.serializers import (
    ThreadSerializer,
    PostSerializer,
    QuestionSerializer,
    AnswerSerializer,
    TagSerializer,
)
from siweauth.siwe import IsAdminOrReadOnly


# viewsets for simple crud. 

class ThreadViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Thread objects to be viewed or edited.
    """

    queryset = Thread.objects.all().order_by("-dt")
    serializer_class = ThreadSerializer
    permission_classes = [IsAdminOrReadOnly]


class PostViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Post objects to be viewed or edited.
    """

    queryset = Post.objects.all().order_by("-dt")
    serializer_class = PostSerializer
    permission_classes = [IsAdminOrReadOnly]


class QuestionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Question objects to be viewed or edited.
    """

    queryset = Question.objects.all().order_by("-post__dt")
    serializer_class = QuestionSerializer
    permission_classes = [IsAdminOrReadOnly]


class AnswerViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Answer objects to be viewed or edited.
    """

    queryset = Answer.objects.all().order_by("-post__dt")
    serializer_class = AnswerSerializer
    permission_classes = [IsAdminOrReadOnly]


class TagViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Tag objects to be viewed or edited.
    """

    queryset = Tag.objects.all().order_by("name")
    serializer_class = TagSerializer
    permission_classes = [IsAdminOrReadOnly]
