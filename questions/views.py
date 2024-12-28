import datetime
import pytz
import secrets

from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from rest_framework import permissions, viewsets

from models import Thread, Post, Question, Answer, Tag, Wallet, Nonce
from serializers import (
    ThreadSerializer,
    PostSerializer,
    QuestionSerializer,
    AnswerSerializer,
    TagSerializer,
)
from siwe import siwe_required


@require_http_methods(["GET"])
def nonce(request):
    now = datetime.now(tz=pytz.UTC)

    for n in Nonce.objects.filter(expiration__lte=datetime.now(tz=pytz.UTC)):
        n.delete()
    n = Nonce(value=secrets.token_hex(12), expiration=now + datetime.timedelta(hours=3))
    n.save()

    return JsonResponse({"nonce": n.value})


# TODO disable deleting / updating / etc


@siwe_required
class ThreadViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Thread objects to be viewed or edited.
    """

    queryset = Thread.objects.all().order_by("-dt")
    serializer_class = ThreadSerializer


@siwe_required
class PostViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Post objects to be viewed or edited.
    """

    queryset = Post.objects.all().order_by("-dt")
    serializer_class = PostSerializer


@siwe_required
class QuestionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Question objects to be viewed or edited.
    """

    queryset = Question.objects.all().order_by("-post__dt")
    serializer_class = QuestionSerializer


@siwe_required
class AnswerViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Answer objects to be viewed or edited.
    """

    queryset = Answer.objects.all().order_by("-post__dt")
    serializer_class = AnswerSerializer


@siwe_required
class TagViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Tag objects to be viewed or edited.
    """

    queryset = Tag.objects.all().order_by("name")
    serializer_class = TagSerializer
