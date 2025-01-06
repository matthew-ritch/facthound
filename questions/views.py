# TODO verify hashs are correct in contracts
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets

import datetime
import pytz
import os
from web3 import Web3
import json

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
from questions.settings import allowed_owners


w3 = Web3(
    Web3.HTTPProvider(
        f"{os.getenv('ALCHEMY_API_ENDPOINT')}/{os.getenv('ALCHEMY_API_KEY')}"
    )
)
question_contract = json.load(open("contracts/question.json"))
question_abi = question_contract["abi"]
question_bytecode = question_contract["bytecode"]["object"]


# endpoints for making posts, threads, q + a
def _make_post(user, text, thread=None, topic=None, tags=None):
    now = datetime.datetime.now(tz=pytz.UTC)
    # make thread if neeeded, else get it
    assert (thread is None) ^ (topic is None)  # xor
    if thread is None:
        thread = Thread.objects.create(topic=topic, dt=now)
        if tags:
            for t in tags:
                tag, _ = Tag.objects.get_or_create(name=t)
                thread.tag_set.add(tag)
    else:
        thread = Thread.objects.get(pk=thread)
    # make and return post
    return Post.objects.create(poster=user, thread=thread, text=text, dt=now)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def post(request):
    thread = request.data.get("thread")
    topic = request.data.get("topic")
    text = request.data.get("text")
    tags = request.data.getlist("tags")

    # check if params make sense
    if text is None:
        return JsonResponse({"message": "Your post needs text."}, status=400)
    if not (thread is None) ^ (topic is None):
        return JsonResponse(
            {
                "message": "One of thread or topic must be specified. You cannot specify both."
            },
            status=400,
        )
    # make post
    post = _make_post(request.user, text, thread, topic, tags)
    return JsonResponse(
        {"message": "post created", "thread": post.thread.pk, "post": post.pk}
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def question(request):
    thread = request.data.get("thread")
    topic = request.data.get("topic")
    text = request.data.get("text")
    tags = request.data.getlist("tags")
    questionAddress = request.query_params.get("questionAddress")
    asker = request.user
    # check if params make sense
    if text is None:
        return JsonResponse({"message": "Your post needs text."}, status=400)
    if not (thread is None) ^ (topic is None):
        return JsonResponse(
            {
                "message": "One of thread or topic must be specified. You cannot specify both."
            },
            status=400,
        )
    if questionAddress:
        try:
            contract = w3.eth.Contract(address=questionAddress, abi=question_abi)
        except:
            return JsonResponse(
                {"message": "Failed to load contract."},
                status=400,
            )
        # verify that we own this contract
        owner = contract.functions.owner().call()
        if not owner in allowed_owners:
            return JsonResponse(
                {"message": "Invalid owner."},
                status=400,
            )
        questionHash = contract.functions.questionHash().call()
        asker = contract.functions.asker().call()
        if asker != request.user.wallet:
            return JsonResponse(
                {"message": "Invalid asker."},
                status=400,
            )
        bounty = contract.functions.storedValue().call()
        status = contract.functions.storedValue().call()
    else:
        questionHash, bounty, status = None, None, "OP"
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
    thread = request.data.get("thread")
    text = request.data.get("text")
    question = request.data.get("question")
    questionAddress = request.data.get("questionAddress")
    answerHash = request.data.get("questionAddress")
    answerer = request.user
    # check if params make sense
    if text is None:
        return JsonResponse({"message": "Your post needs text."}, status=400)
    if thread is None:
        return JsonResponse({"message": "Your post needs a thread."}, status=400)
    if question is None:
        return JsonResponse({"message": "Your answer needs a question."}, status=400)
    if (questionAddress is None) ^ (answerHash is None):
        return JsonResponse(
            {
                "message": "If questionAddress or answerHash are provided, then both are required"
            },
            status=400,
        )
    try:
        question = Question.objects.get(pk=question)
    except Question.DoesNotExist:
        return JsonResponse({"message": "No question with that id exists."}, status=400)
    if question.post.thread.pk != int(thread):
        return JsonResponse(
            {
                "message": "Answers must be posted in the same thread as the question they answer."
            },
            status=400,
        )
    # from contracts:
    if questionAddress:
        try:
            contract = w3.eth.Contract(address=questionAddress, abi=question_abi)
        except:
            return JsonResponse(
                {"message": "Failed to load contract."},
                status=400,
            )
        # verify that we own this contract
        owner = contract.functions.owner().call()
        if not owner in allowed_owners:
            return JsonResponse(
                {"message": "Invalid owner."},
                status=400,
            )
        # verify that answerHash is an answer for this contract and was posted by this answerer
        answerInfoMap = contract.functions.answerInfoMap().call()
        if not answerHash in answerInfoMap.keys():
            return JsonResponse(
                {"message": "Invalid answerHash."},
                status=400,
            )
        answerer = answerInfoMap[answerHash]
        if answerer != request.user.wallet:
            return JsonResponse(
                {"message": "Invalid answerer."},
                status=400,
            )
        status = "SE" if answerHash == contract.functions.selectedAnswer().call() else "UN"
    else:
        status = "OP"
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
