from django.http import JsonResponse
from django.db.models import (
    Count,
    Case,
    When,
    IntegerField,
    Q,
    F,
    Sum,
    Subquery,
    OuterRef,
)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets

import datetime
import pytz
import os
from web3 import Web3
import json
import hexbytes
import operator
from functools import reduce
import numpy as np
import logging

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

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logging.basicConfig(
    filename="facthound.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

w3 = Web3(
    Web3.HTTPProvider(
        f"{os.getenv('ALCHEMY_API_ENDPOINT')}/{os.getenv('ALCHEMY_API_KEY')}"
    )
)
with open("contracts/question.json", "rb") as f:
    question_contract = json.load(f)
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
    tags = request.data.get("tags")

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
        {"message": "success", "thread": post.thread.pk, "post": post.pk}
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def question(request):
    thread = request.data.get("thread")
    topic = request.data.get("topic")
    text = request.data.get("text")
    tags = request.data.get("tags")
    questionAddress = request.data.get("questionAddress")
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
            contract = w3.eth.contract(address=questionAddress, abi=question_abi)
        except:
            return JsonResponse(
                {"message": "Failed to load contract."},
                status=400,
            )
        # verify that we own this contract
        owner = contract.caller.owner()
        if not owner in allowed_owners:
            return JsonResponse(
                {"message": "Invalid owner."},
                status=400,
            )
        questionHash = contract.caller.questionHash()
        expectedQuestionHash = Web3.solidity_keccak(
            ["address", "string"], [asker.wallet, text]
        )
        asker = contract.caller.asker()
        if questionHash != expectedQuestionHash:
            return JsonResponse(
                {"message": "Unexpected questionHash."},
                status=400,
            )
        asker, _ = User.objects.get_or_create(wallet=asker)
        bounty = w3.eth.get_balance(contract.address)
        status = (
            "CA"
            if contract.caller.isCancelled()
            else (
                "RS"
                if contract.caller.isResolved()
                else (
                    "AS"
                    if (contract.caller.selectedAnswer().hex() == 32 * "0")
                    else "OP"
                )
            )
        )
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
            "message": "success",
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
    answerHash = request.data.get("answerHash")
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
    if questionAddress and answerHash:
        # verify that this contract matches the question id
        if not question.questionAddress == questionAddress:
            return JsonResponse(
                {"message": "This question does not match this questionAddress."},
                status=400,
            )
        try:
            contract = w3.eth.contract(address=questionAddress, abi=question_abi)
            owner = contract.caller.owner()
        except:
            return JsonResponse(
                {"message": "Failed to load contract."},
                status=400,
            )
        # verify that we own this contract
        if not owner in allowed_owners:
            return JsonResponse(
                {"message": "Invalid owner."},
                status=400,
            )
        expectedAnswerHash = Web3.solidity_keccak(
            ["address", "string"], [answerer.wallet, text]
        )
        answerHash = hexbytes.HexBytes(answerHash)
        if answerHash != expectedAnswerHash:
            return JsonResponse(
                {"message": "Unexpected answerHash."},
                status=400,
            )
        # verify that answerHash is an answer for this contract and was posted by this answerer
        answerer = contract.caller.answerInfoMap(answerHash)
        if answerer == ("0x" + 40 * "0"):
            return JsonResponse(
                {"message": "Invalid answerHash."},
                status=400,
            )
        if answerer != request.user.wallet:
            return JsonResponse(
                {"message": "Invalid answerer."},
                status=400,
            )
        answerer, _ = User.objects.get_or_create(wallet=answerer)
        status = "SE" if answerHash == contract.caller.selectedAnswer().hex() else "UN"
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
            "message": "success",
            "thread": post.thread.pk,
            "post": post.pk,
            "question": question.pk,
            "answer": answer.pk,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def selection(request):
    question = request.data.get("question")
    answer = request.data.get("answer")
    try:
        question = Question.objects.get(pk=question)
    except Question.DoesNotExist:
        return JsonResponse({"message": "No question with that id exists."}, status=400)
    try:
        answer = Answer.objects.get(pk=answer)
    except Answer.DoesNotExist:
        return JsonResponse({"message": "No answer with that id exists."}, status=400)
    if answer.question != question:
        return JsonResponse(
            {"message": "This answer does not answer this question."}, status=400
        )
    if question.asker.wallet != request.user.wallet:
        return JsonResponse(
            {"message": "Only the question's asker can do this."},
            status=400,
        )
    if question.questionAddress and answer.answerHash:
        # make sure this answer was selected in the contract
        contract = w3.eth.contract(address=question.questionAddress, abi=question_abi)
        selectedAnswer = contract.caller.selectedAnswer()
        if selectedAnswer != answer.answerHash:
            return JsonResponse(
                {
                    "message": f"This answer must be selected in the contract at address {question.questionAddress}."
                },
                status=400,
            )
    answer.status = "SE"
    question.status = "AS"

    answer.save()
    question.save()
    

    return JsonResponse(
        {
            "message": "answer selected",
            "question": question.pk,
            "answer": answer.pk,
        }
    )


@api_view(["GET"])
def search(request):
    search_string = request.GET.get("search_string")
    components = search_string.split()

    posts = Post.objects.filter(
        reduce(operator.or_, (Q(text__icontains=x) for x in components))
    ).distinct()

    threads = posts.values_list("thread", flat=True)
    th, c = np.unique(threads, return_counts=True)
    th = th[np.argsort(-c)]
    th = [int(x) for x in th]
    

    return JsonResponse({"search_string": search_string, "threads": list(th)})


@api_view(["GET"])
def threadList(request):
    queryset = Thread.objects.all().order_by("-dt")
    queryset = queryset.annotate(
        first_poster_wallet=Subquery(
            Post.objects.filter(thread=OuterRef("pk"))
            .order_by("dt")
            .values("poster__wallet")[:1]
        ),
        first_poster_name=Subquery(
            Post.objects.filter(thread=OuterRef("pk"))
            .order_by("dt")
            .values("poster__username")[:1]
        ),
        total_bounty=Sum(
            Subquery(
                Question.objects.filter(
                    post__thread=OuterRef("pk"), bounty__isnull=False, status="OP"
                ).values("bounty")
            )
        ),
    )
    queryset = list(queryset.values())
    
    return JsonResponse({"threads": queryset})


@api_view(["GET"])
def threadPosts(request):
    queryset = Post.objects.all()
    threadId = request.query_params.get("threadId")
    if threadId is not None:
        queryset = queryset.filter(thread__pk=threadId)
    queryset = queryset.order_by("dt")
    queryset = queryset.annotate(poster_name=F("poster__username"))
    queryset = queryset.annotate(poster_wallet=F("poster__wallet"))
    queryset = queryset.annotate(
        question_id=Case(
            When(question__isnull=True, then=F("answer__question")),
            default=F("question"),
        )
    )
    queryset = queryset.annotate(
        question_address=Case(
            When(question__isnull=True, then=F("answer__question__questionAddress")),
            default=F("question__questionAddress"),
        )
    )
    queryset = queryset.annotate(
        asker_address=Case(
            When(question__isnull=True, then=F("answer__question__asker__wallet")),
            default=F("question__asker__wallet"),
        )
    )
    queryset = queryset.annotate(
        asker_username=Case(
            When(question__isnull=True, then=F("answer__question__asker__username")),
            default=F("question__asker__username"),
        )
    )
    queryset = queryset.annotate(
        answer_status=F("answer__status"),
    )
    queryset = queryset.annotate(answer_id=F("answer"))
    queryset = queryset.annotate(answer_hash=F("answer__answerHash"))
    
    # Convert queryset to list of dicts and handle bytes serialization
    posts = []
    for post in queryset:
        post_dict = {
            'id': post.id,
            'text': post.text,
            'dt': post.dt,
            'thread_id': post.thread_id,
            'poster_name': post.poster_name,
            'poster_wallet': post.poster_wallet,
            'asker_address': post.asker_address,
            'asker_username': post.asker_username,
            'answer_status': post.answer_status,
            'question_id': post.question_id,
            'question_address': post.question_address,
            'answer_id': post.answer_id,
            'answer_hash': post.answer_hash.hex() if post.answer_hash else None
        }
        posts.append(post_dict)
    
    return JsonResponse({"threadId": threadId, "posts": posts})


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
