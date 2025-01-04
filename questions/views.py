from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets

import datetime

from siweauth.models import User, Nonce
from siweauth.auth import IsAdminOrReadOnly
from questions.models import Thread, Post, Question, Answer, Tag
from questions.serializers import (
    ThreadSerializer,
    PostSerializer,
    QuestionSerializer,
    AnswerSerializer,
    TagSerializer,
)


# endpoints for making posts, threads, q + a
def _make_post(user, text, thread=None, topic=None, tags=None):
    now = datetime.datetime.now()
    # make thread if neeeded, else get it
    assert thread is None ^ topic is None  # xor
    if thread is None:
        thread = Thread.objects.create(topic=topic, dt=now)
        for t in tags:
            tag, _ = Tag.objects.get_or_create(name=t)
            thread.tags.add(tag)
    else:
        thread = Thread.objects.get(pk=thread)
    # make and return post
    return Post.objects.create(poster=user, thread=thread, text=text, dt=now)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def post(request):
    thread = request.query_params.get("thread")
    topic = request.query_params.get("topic")
    text = request.query_params.get("text")
    tags = request.query_params.get("tags")

    # check if params make sense
    if text is None:
        return JsonResponse({"message": "your post needs text"}, status=400)
    if not (thread is None ^ topic is None):
        return JsonResponse(
            {"message": "cannot set topic on existing thread"}, status=400
        )
    # make post
    post = _make_post(request.user, text, thread, topic, tags)
    return JsonResponse(
        {"message": "post created", "thread": post.thread.pk, "post": post.pk}
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def question(request):
    thread = request.query_params.get("thread")
    topic = request.query_params.get("topic")
    text = request.query_params.get("text")
    tags = request.query_params.get("tags")
    questionAddress = request.query_params.get("questionAddress")
    # check if params make sense
    if text is None:
        return JsonResponse({"message": "text is required"}, status=400)
    if not (thread is None ^ topic is None):
        return JsonResponse(
            {"message": "only provide one of either thread or topic"}, status=400
        )
    if questionAddress is None:
        return JsonResponse({"message": "questionAddress is required"}, status=400)
    # TODO verify questionaddress exists and get questionHash, asker, bounty, status
    questionHash, asker, bounty, status = None, None, None, None
    # TODO verify that asker == request.user
    # TODO verify questionHash is hash of correct text
    # make post
    post = _make_post(request.user, text, thread, topic, tags)
    # make question
    question = Question.objects.create(
        post=post,
        questionHash=questionHash,
        questionAddress=questionAddress,
        asker=asker,
        bounty=bounty,
        status=status,
    )
    return JsonResponse(
        {
            "message": "question posted",
            "thread": post.thread.pk,
            "post": post.pk,
            "question": question.pk,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def answer(request):
    thread = request.query_params.get("thread")
    text = request.query_params.get("text")
    questionAddress = request.query_params.get("questionAddress")
    answerHash = request.query_params.get("questionAddress")
    # check if params make sense
    if text is None:
        return JsonResponse({"message": "text is required"}, status=400)
    if thread is None:
        return JsonResponse({"message": "thread is required"}, status=400)
    if questionAddress is None:
        return JsonResponse({"message": "questionAddress is required"}, status=400)
    if answerHash is None:
        return JsonResponse({"message": "questionAddress is required"}, status=400)
    try:
        question = Question.objects.get(questionAddress=questionAddress)
    except Question.DoesNotExist:
        return JsonResponse(
            {"message": "question with that address does not exist in db"}, status=400
        )
    if question.thread.pk != thread:
        return JsonResponse(
            {
                "message": "answers must be posted in the same thread as the question they answer"
            },
            status=400,
        )
    # from contracts:
    # TODO verify questionaddress exists and has answerHash as ananswer
    # then get answerer, status
    answerer, status = None, None
    # TODO verify that answerer == request.user
    # TODO verify answerHash is hash of correct text
    # make post
    post = _make_post(request.user, text, thread, None, None)
    # make answer
    answer = Answer.objects.create(
        post=post,
        question=question,
        answerHash=answerHash,
        answerer=answerer,
        status=status,
    )
    return JsonResponse(
        {
            "message": "answer posted",
            "thread": post.thread.pk,
            "post": post.pk,
            "question": question.pk,
            "answer": answer.pk,
        }
    )


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
