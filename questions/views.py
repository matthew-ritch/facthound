from django.http import JsonResponse
from django.db.models import (
    Case,
    When,
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
from questions.confirm_onchain import (
    confirm_question,
    confirm_answer,
    confirm_selection,
)

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
with open("contracts/FactHound.json", "rb") as f:
    facthound_contract = json.load(f)
facthound_abi = facthound_contract["abi"]
facthound_bytecode = facthound_contract["bytecode"]["object"]


# endpoints for making posts, threads, q + a
def _make_post(user, text, thread=None, topic=None, tags=None):
    now = datetime.datetime.now(tz=pytz.UTC)
    # make thread if neeeded, else get it
    assert (thread is None) ^ (topic is None)  # xor
    if thread is None:
        thread = Thread.objects.create(topic=topic, dt=now)
        if tags:
            for t in tags:
                tag, _ = Tag.objects.get_or_create(name=t.lower())
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
    tags = (
        request.data.getlist("tags")
        if hasattr(request.data, "getlist")
        else request.data.get("tags", [])
    )

    logger.info(
        json.dumps(
            {
                "view": "post",
                "wallet": request.user.wallet,
                "username": request.user.username,
                "thread": thread,
                "topic": topic,
                "tags": tags,
            }
        )
    )

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
    tags = (
        request.data.getlist("tags")
        if hasattr(request.data, "getlist")
        else request.data.get("tags", [])
    )
    contractAddress = request.data.get("contractAddress")
    questionHash = request.data.get("questionHash")

    logger.info(
        json.dumps(
            {
                "view": "question",
                "wallet": request.user.wallet,
                "username": request.user.username,
                "thread": thread,
                "topic": topic,
                "tags": tags,
                "contractAddress": contractAddress,
                "questionHash": questionHash,
            }
        )
    )

    questionHash = hexbytes.HexBytes(questionHash) if questionHash else None
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
    if contractAddress:
        confirmed_onchain = False
        status = "OP"
        bounty = None
    else:
        questionHash, bounty, confirmed_onchain, status = None, None, None, "OP"
    # make post
    post = _make_post(request.user, text, thread, topic, tags)
    # make question
    question = Question.objects.create(
        post=post,
        questionHash=questionHash,
        contractAddress=contractAddress,
        asker=asker,
        bounty=bounty,
        status=status,
        confirmed_onchain=confirmed_onchain,
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
    contractAddress = request.data.get("contractAddress")
    questionHash = request.data.get("questionHash")
    answerHash = request.data.get("answerHash")

    logger.info(
        json.dumps(
            {
                "view": "answer",
                "wallet": request.user.wallet,
                "username": request.user.username,
                "thread": thread,
                "question": question,
                "contractAddress": contractAddress,
                "questionHash": questionHash,
                "answerHash": answerHash,
            }
        )
    )

    questionHash = hexbytes.HexBytes(questionHash) if questionHash else None
    answerHash = hexbytes.HexBytes(answerHash) if answerHash else None
    answerer = request.user

    # Validate basic parameters first
    if text is None:
        return JsonResponse({"message": "Your post needs text."}, status=400)
    if thread is None:
        return JsonResponse({"message": "Your post needs a thread."}, status=400)
    if question is None:
        return JsonResponse({"message": "Your answer needs a question."}, status=400)

    # Get and validate question exists
    try:
        question = Question.objects.get(pk=question)
    except Question.DoesNotExist:
        return JsonResponse({"message": "No question with that id exists."}, status=400)

    # Check thread match
    if question.post.thread.pk != int(thread):
        return JsonResponse(
            {
                "message": "Answers must be posted in the same thread as the question they answer."
            },
            status=400,
        )

    # Check contract parameters last
    if any(
        [questionHash is None, answerHash is None, contractAddress is None]
    ) and not (
        all([questionHash is None, answerHash is None, contractAddress is None])
    ):
        return JsonResponse(
            {
                "message": "If questionHash or answerHash or contractAddress are provided, then all are required"
            },
            status=400,
        )

    # from contracts:
    if questionHash and answerHash and contractAddress:
        if question.contractAddress != contractAddress:
            return JsonResponse(
                {"message": "This question does not match this contractAddress."},
                status=400,
            )
        status = "OP"
        confirmed_onchain = False
    else:
        status = "OP"
        confirmed_onchain = None
    # make post
    post = _make_post(request.user, text, thread, None, None)
    # make answer
    answer = Answer.objects.create(
        post=post,
        question=question,
        answerHash=answerHash,
        answerer=answerer,
        status=status,
        confirmed_onchain=confirmed_onchain,
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

    logger.info(
        json.dumps(
            {
                "view": "selection",
                "wallet": request.user.wallet,
                "username": request.user.username,
                "question": question,
                "answer": answer,
            }
        )
    )

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
    if question.contractAddress and answer.answerHash:
        answer.selection_confirmed_onchain = False
    else:
        if question.asker != request.user:
            return JsonResponse(
                {"message": "Only the question's asker can do this."},
                status=400,
            )
    # Set all other answers to unselected
    Answer.objects.filter(question=question).exclude(pk=answer.pk).update(status="UN")
    # Set selected answer and question status
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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def payout(request):
    question = request.data.get("question")
    answer = request.data.get("answer")

    logger.info(
        json.dumps(
            {
                "view": "payout",
                "wallet": request.user.wallet,
                "username": request.user.username,
                "question": question,
                "answer": answer,
            }
        )
    )

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

    if not question.contractAddress or not answer.answerHash:
        return JsonResponse(
            {"message": "This is not an on-chain question/answer pair."}, status=400
        )

    # Verify contract state
    contract = w3.eth.contract(
        address=question.contractAddress, abi=facthound_abi, decode_tuples=True
    )
    selected_answer = contract.caller.getQuestion(
        question.questionHash
    ).selectedAnswer()

    if selected_answer != answer.answerHash:
        return JsonResponse(
            {"message": "This answer is not selected in the contract."}, status=400
        )

    # Update statuses
    question.status = "RS"  # Resolved
    answer.status = "PO"  # Paid out

    question.save()
    answer.save()

    return JsonResponse(
        {
            "message": "payout processed",
            "question": question.pk,
            "answer": answer.pk,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def confirm(request):
    questionHash = (
        hexbytes.HexBytes(request.data.get("questionHash"))
        if request.data.get("questionHash")
        else None
    )
    answerHash = (
        hexbytes.HexBytes(request.data.get("answerHash"))
        if request.data.get("answerHash")
        else None
    )
    type = request.data.get("confirmType")
    match type:
        case "question":
            success, resp = confirm_question(questionHash)
        case "answer":
            success, resp = confirm_answer(questionHash, answerHash)
        case "selection":
            success, resp = confirm_selection(questionHash, answerHash)

    if not isinstance(resp, dict):
        resp = {"message": resp}

    return JsonResponse(resp, status=200 if success else 400)


def annotate_threads(queryset):
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
        total_bounty_available=Sum(
            Subquery(
                Question.objects.filter(
                    post__thread=OuterRef("pk"), bounty__isnull=False, status="OP"
                ).values("bounty")
            )
        ),
        total_bounty_claimed=Sum(
            Subquery(
                Question.objects.filter(
                    post__thread=OuterRef("pk"),
                    bounty__isnull=False,
                    status__in=["AS", "RS"],
                ).values("bounty")
            )
        ),
    )

    # Manually add tags for each thread
    threads_with_annotations = []
    for thread in queryset:
        thread_dict = {
            "id": thread.id,
            "topic": thread.topic,
            "dt": thread.dt,
            "first_poster_wallet": thread.first_poster_wallet,
            "first_poster_name": thread.first_poster_name,
            "total_bounty_available": thread.total_bounty_available,
            "total_bounty_claimed": thread.total_bounty_claimed,
            "tags": list(thread.tag_set.values_list("name", flat=True)),
        }
        threads_with_annotations.append(thread_dict)

    return threads_with_annotations


# Update the view functions to handle the new return type
@api_view(["GET"])
def threadList(request):
    logger.info(
        json.dumps(
            {
                "view": "threadList",
                "wallet": (
                    request.user.wallet if request.user.is_authenticated else None
                ),
                "username": (
                    request.user.username if request.user.is_authenticated else None
                ),
            }
        )
    )

    queryset = Thread.objects.all().order_by("-dt")
    threads = annotate_threads(queryset)
    return JsonResponse({"threads": threads})


@api_view(["GET"])
def search(request):
    search_string = request.GET.get("search_string")

    logger.info(
        json.dumps(
            {
                "view": "search",
                "wallet": (
                    request.user.wallet if request.user.is_authenticated else None
                ),
                "username": (
                    request.user.username if request.user.is_authenticated else None
                ),
                "search_string": search_string,
            }
        )
    )

    components = search_string.split()
    posts = Post.objects.filter(
        reduce(operator.or_, (Q(text__icontains=x) for x in components))
    ).distinct()
    threads = posts.values_list("thread", flat=True)
    th, c = np.unique(threads, return_counts=True)
    queryset = (
        Thread.objects.filter(pk__in=th)
        | Thread.objects.filter(topic__icontains=search_string)
        | Thread.objects.filter(tag__name__in=components)
    )
    queryset = queryset.order_by("-dt")

    threads = annotate_threads(queryset)
    return JsonResponse({"search_string": search_string, "threads": threads})


@api_view(["GET"])
def threadPosts(request):
    threadId = request.query_params.get("threadId")

    logger.info(
        json.dumps(
            {
                "view": "threadPosts",
                "wallet": (
                    request.user.wallet if request.user.is_authenticated else None
                ),
                "username": (
                    request.user.username if request.user.is_authenticated else None
                ),
                "threadId": threadId,
            }
        )
    )

    response_dict = {}
    queryset = Post.objects.all()
    threadId = request.query_params.get("threadId")
    if threadId is not None:
        queryset = queryset.filter(thread__pk=threadId)
        response_dict["threadId"] = threadId
    if queryset.count() == 0:
        return JsonResponse({"message": "Thread does not exist"}, status=404)
    response_dict["threadTopic"] = queryset.first().thread.topic
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
        contract_address=Case(
            When(question__isnull=True, then=F("answer__question__contractAddress")),
            default=F("question__contractAddress"),
        )
    )
    queryset = queryset.annotate(
        asker_address=Case(
            When(question__isnull=True, then=F("answer__question__asker__wallet")),
            default=F("question__asker__wallet"),
        )
    )
    queryset = queryset.annotate(
        question_hash=Case(
            When(question__isnull=True, then=F("answer__question__questionHash")),
            default=F("question__questionHash"),
        )
    )
    queryset = queryset.annotate(
        bounty=F("question__bounty"),
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
            "id": post.id,
            "text": post.text,
            "dt": post.dt,
            "thread_id": post.thread_id,
            "poster_name": post.poster_name,
            "poster_wallet": post.poster_wallet,
            "asker_address": post.asker_address,
            "asker_username": post.asker_username,
            "answer_status": post.answer_status,
            "question_id": post.question_id,
            "question_hash": post.question_hash.hex() if post.question_hash else None,
            "contract_address": post.contract_address,
            "bounty": post.bounty,
            "answer_id": post.answer_id,
            "answer_hash": post.answer_hash.hex() if post.answer_hash else None,
        }
        posts.append(post_dict)
    response_dict["posts"] = posts
    return JsonResponse(response_dict)


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
