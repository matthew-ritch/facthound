# TODO add fail cases for Answer
from django.test import TestCase
from django.test import RequestFactory
from rest_framework.test import force_authenticate

from web3 import (
    EthereumTesterProvider,
    Web3,
)
import json, datetime, pytz

from siweauth.models import User

from questions import views
from questions.models import Thread, Post, Question, Answer, Tag
from questions.serializers import (
    ThreadSerializer,
    PostSerializer,
    QuestionSerializer,
    AnswerSerializer,
    TagSerializer,
)

class BaseTestCase(TestCase):
    def setUp(self):
        # change views's w3 provider to this test provider
        self.provider = EthereumTesterProvider()
        self.w3 = Web3(self.provider)
        views.w3 = self.w3

        with open("contracts/Question.json", "rb") as f:
            self.question_contract = json.load(f)


# guide: https://web3py.readthedocs.io/en/v5/examples.html#contract-unit-tests-in-python


class TestQuestions(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        #
        self.eth_tester = self.provider.ethereum_tester
        self.owner = self.eth_tester.get_accounts()[0]
        self.oracle = self.eth_tester.get_accounts()[1]
        self.asker = self.eth_tester.get_accounts()[2]
        self.asker_user = User.objects.create_user_address(self.asker)
        views.allowed_owners.append(self.owner)

    def test_start_thread(self):
        question_dict = {
            "topic": "sometopic",
            "text": "I am wondering what to do about this topic.",
            "tags": ["a", "b", "c"],
        }
        # deploy question
        abi = self.question_contract["abi"]
        bytecode = self.question_contract["bytecode"]["object"]
        questionContract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
        questionHash = Web3.solidity_keccak(
            ["address", "string"], [self.asker, question_dict["text"]]
        )
        tx_hash = questionContract.constructor(
            self.owner, self.oracle, self.asker, questionHash
        ).transact({"from": self.asker, "value": 1})
        # wait for the transaction to be mined
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, 180)
        # pack the required info
        question_dict["questionAddress"] = tx_receipt["contractAddress"]
        # post about question
        request = self.factory.post(
            "/api/question/",
            data=question_dict,
            format='json'
        )
        force_authenticate(request, self.asker_user)
        response = views.question(request)
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        # make sure thread was created
        thread = Thread.objects.get(topic=question_dict["topic"])
        self.assertEqual(thread.pk, content["thread"])
        # make sure post was created
        post = Post.objects.get(text=question_dict["text"], thread=thread)
        postpk = Post.objects.get(pk=content["post"])
        self.assertEqual(post, postpk)
        self.assertEqual(post.text, question_dict["text"])
        self.assertEqual(self.asker_user, post.poster)
        # make sure question was created
        question = Question.objects.get(
            post__text=question_dict["text"], post__thread=thread
        )
        questionpk = Question.objects.get(pk=content["question"])
        self.assertEqual(question, questionpk)
        self.assertEqual(question.post.text, question_dict["text"])
        self.assertEqual(self.asker_user, question.asker)
        # check contract properties
        self.assertEqual(question.questionAddress, tx_receipt["contractAddress"])
        self.assertEqual(question.questionHash, questionHash)
        self.assertEqual(question.bounty, 1)
        # make sure question and post are identified together
        self.assertEqual(question.post, post)
        # thread should have 1 post. test associations
        self.assertEqual(thread.post_set.all().count(), 1)
        self.assertEqual(thread, post.thread)
        self.assertEqual(thread.dt, post.dt)
        # thread should have the right tags
        for t in question_dict["tags"]:
            qs = Tag.objects.filter(thread=thread, name=t)
            self.assertEqual(qs.count(), 1)

    def test_question_no_text(self):
        question_dict = {
            "topic": "sometopic",
            "tags": ["a", "b", "c"],
        }
        request = self.factory.post(
            "/api/question/",
            question_dict,
        )
        force_authenticate(request, self.asker_user)
        response = views.question(request)
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(content["message"], "Your post needs text.")

    def test_question_both_thread_and_topic(self):
        question_dict = {
            "thread": 1,
            "topic": "sometopic",
            "text": "I am wondering what to do about this topic.",
            "tags": ["a", "b", "c"],
        }
        request = self.factory.post(
            "/api/question/",
            question_dict,
        )
        force_authenticate(request, self.asker_user)
        response = views.question(request)
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            content["message"],
            "One of thread or topic must be specified. You cannot specify both.",
        )

    def test_question_invalid_contract(self):
        question_dict = {
            "topic": "sometopic",
            "text": "I am wondering what to do about this topic.",
            "tags": ["a", "b", "c"],
            "questionAddress": "0xInvalidAddress",
        }
        request = self.factory.post(
            "/api/question/",
            question_dict,
        )
        force_authenticate(request, self.asker_user)
        response = views.question(request)
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(content["message"], "Failed to load contract.")

    def test_question_invalid_owner(self):
        question_dict = {
            "topic": "sometopic",
            "text": "I am wondering what to do about this topic.",
            "tags": ["a", "b", "c"],
        }
        # deploy question with invalid owner
        abi = self.question_contract["abi"]
        bytecode = self.question_contract["bytecode"]["object"]
        questionContract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
        questionHash = Web3.solidity_keccak(
            ["address", "string"], [self.asker, question_dict["text"]]
        )
        tx_hash = questionContract.constructor(
            self.oracle, self.oracle, self.asker, questionHash
        ).transact({"from": self.asker, "value": 1})
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, 180)
        question_dict["questionAddress"] = tx_receipt["contractAddress"]
        request = self.factory.post(
            "/api/question/",
            question_dict,
        )
        force_authenticate(request, self.asker_user)
        response = views.question(request)
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(content["message"], "Invalid owner.")

    def test_question_unexpected_questionHash(self):
        question_dict = {
            "topic": "sometopic",
            "text": "I am wondering what to do about this topic.",
            "tags": ["a", "b", "c"],
        }
        # deploy question with invalid asker
        abi = self.question_contract["abi"]
        bytecode = self.question_contract["bytecode"]["object"]
        questionContract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
        questionHash = Web3.solidity_keccak(
            ["address", "string"], [self.oracle, question_dict["text"]]
        )
        tx_hash = questionContract.constructor(
            self.owner, self.oracle, self.oracle, questionHash
        ).transact({"from": self.oracle, "value": 1})
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, 180)
        question_dict["questionAddress"] = tx_receipt["contractAddress"]
        # modify text so the hash does not match
        question_dict["text"] = question_dict["text"] + "HA!"
        request = self.factory.post(
            "/api/question/",
            question_dict,
        )
        force_authenticate(request, self.asker_user)
        response = views.question(request)
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(content["message"], "Unexpected questionHash.")


class TestAnswers(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        #
        self.eth_tester = self.provider.ethereum_tester
        self.owner = self.eth_tester.get_accounts()[0]
        self.oracle = self.eth_tester.get_accounts()[1]
        self.asker = self.eth_tester.get_accounts()[2]
        self.asker_user = User.objects.create_user_address(self.asker)
        self.answerer = self.eth_tester.get_accounts()[3]
        self.answerer_user = User.objects.create_user_address(self.answerer)
        views.allowed_owners.append(self.owner)
        # make a question post
        question_dict = {
            "topic": "sometopic",
            "text": "I am wondering what to do about this topic.",
            "tags": ["a", "b", "c"],
        }
        # deploy question
        abi = self.question_contract["abi"]
        bytecode = self.question_contract["bytecode"]["object"]
        self.questionContract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
        questionHash = Web3.solidity_keccak(
            ["address", "string"], [self.asker, question_dict["text"]]
        )
        tx_hash = self.questionContract.constructor(
            self.owner, self.oracle, self.asker, questionHash
        ).transact({"from": self.asker, "value": 1})
        # wait for the transaction to be mined
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, 180)
        self.questionContract = self.w3.eth.contract(
            address=tx_receipt["contractAddress"], abi=abi
        )
        # pack the required info
        question_dict["questionAddress"] = tx_receipt["contractAddress"]
        # post about question
        request = self.factory.post(
            "/api/question/",
            question_dict,
        )
        force_authenticate(request, self.asker_user)
        response = views.question(request)
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.thread = Thread.objects.get(pk=content["thread"])
        self.question = Question.objects.get(pk=content["question"])

    def test_reply_to_thread(self):
        answerString = "You should do nothing."
        answerHash = Web3.solidity_keccak(
            ["address", "string"], [self.answerer, answerString]
        )
        # make answer object
        self.questionContract.functions.createAnswer(answerHash).transact(
            {"from": self.answerer}
        )
        # post it
        post_dict = {
            "thread": self.thread.pk,
            "text": "You should do nothing.",
            "question": self.question.pk,
            "questionAddress": self.questionContract.address,
            "answerHash": answerHash.hex(),
        }
        request = self.factory.post(
            "/api/post/",
            post_dict,
        )
        force_authenticate(request, self.answerer_user)
        response = views.answer(request)
        content = json.loads(response.content)
        # make sure post was created
        post = Post.objects.get(text=post_dict["text"], thread=post_dict["thread"])
        postpk = Post.objects.get(pk=content["post"])
        self.assertEqual(post, postpk)
        self.assertEqual(post.text, post_dict["text"])
        self.assertEqual(self.answerer_user, post.poster)
        # make sure answer was created
        answer = Answer.objects.get(
            post__text=post_dict["text"], post__thread=self.thread
        )
        answerpk = Answer.objects.get(pk=content["answer"])
        self.assertEqual(answer, answerpk)
        self.assertEqual(answer.post.text, post_dict["text"])
        self.assertEqual(self.answerer_user, answer.answerer)
        # check answer's contract fields
        self.assertEqual(answer.answerHash.hex(), post_dict["answerHash"])
        self.assertEqual(
            answer.answerer.wallet,
            self.questionContract.caller.answerInfoMap(answer.answerHash),
        )
        # make sure answer and post are identified together
        self.assertEqual(answer.post, post)
        # make sure answer answers the right question
        self.assertEqual(answer.question, self.question)
        # thread should have 2 post. test associations
        self.assertEqual(self.thread.post_set.all().count(), 2)
        self.assertEqual(self.thread, post.thread)

    def test_undeployed_contract_fails(self):
        qp = Post.objects.create(
            thread=self.thread,
            text="Wrong Question Text",
            dt=datetime.datetime.now(tz=pytz.UTC),
            poster=self.asker_user,
        )
        wrongQuestion = Question.objects.create(
            post=qp,
            asker=self.asker_user,
            status="OP",
            questionAddress="0x1efF47bc3a10a45D4B230B5d10E37751FE6AA718",
        )
        #
        answerString = "You should do nothing."
        answerHash = Web3.solidity_keccak(
            ["address", "string"], [self.answerer, answerString]
        )
        # make answer object
        self.questionContract.functions.createAnswer(answerHash).transact(
            {"from": self.answerer}
        )
        # post it
        post_dict = {
            "thread": self.thread.pk,
            "text": "You should do nothing.",
            "question": wrongQuestion.pk,
            "questionAddress": "0x1efF47bc3a10a45D4B230B5d10E37751FE6AA718",
            "answerHash": answerHash.hex(),
        }
        request = self.factory.post(
            "/api/post/",
            post_dict,
        )
        force_authenticate(request, self.answerer_user)
        response = views.answer(request)
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            content["message"],
            "Failed to load contract.",
        )

    def test_mismatched_question_and_questionAddress(self):
        qp = Post.objects.create(
            thread=self.thread,
            text="Wrong Question Text",
            dt=datetime.datetime.now(tz=pytz.UTC),
            poster=self.asker_user,
        )
        wrongQuestion = Question.objects.create(
            post=qp, asker=self.asker_user, status="OP"
        )
        # answer the wrong question
        answerString = "You should do nothing."
        answerHash = Web3.solidity_keccak(
            ["address", "string"], [self.answerer, answerString]
        )
        # make answer object
        self.questionContract.functions.createAnswer(answerHash).transact(
            {"from": self.answerer}
        )
        # post it
        post_dict = {
            "thread": self.thread.pk,
            "text": "You should do nothing.",
            "question": wrongQuestion.pk,
            "questionAddress": self.questionContract.address,
            "answerHash": answerHash.hex(),
        }
        request = self.factory.post(
            "/api/post/",
            post_dict,
        )
        #
        force_authenticate(request, self.answerer_user)
        response = views.answer(request)
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            content["message"],
            "This question does not match this questionAddress.",
        )

    def test_unexpected_answerHash(self):
        answerString = "You should do nothing."
        answerHash = Web3.solidity_keccak(
            ["address", "string"], [self.answerer, answerString]
        )
        # make answer object
        self.questionContract.functions.createAnswer(answerHash).transact(
            {"from": self.answerer}
        )
        # post it
        post_dict = {
            "thread": self.thread.pk,
            "text": "You should do nothing."
            + "HA!",  # add to the text so the hash will be invalid
            "question": self.question.pk,
            "questionAddress": self.questionContract.address,
            "answerHash": answerHash.hex(),
        }
        request = self.factory.post(
            "/api/post/",
            post_dict,
        )
        force_authenticate(request, self.answerer_user)
        response = views.answer(request)
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            content["message"],
            "Unexpected answerHash.",
        )

    def test_wrong_answerHash_fails(self):
        answerString = "You should do nothing."
        answerHash = Web3.solidity_keccak(
            ["address", "string"], [self.answerer, answerString]
        )
        wrongAnswerHash = Web3.solidity_keccak(
            ["address", "string"], [self.answerer, answerString + "wrongend"]
        )
        # make answer object
        self.questionContract.functions.createAnswer(answerHash).transact(
            {"from": self.answerer}
        )
        # post it
        post_dict = {
            "thread": self.thread.pk,
            "text": "You should do nothing.wrongend",
            "question": self.question.pk,
            "questionAddress": self.questionContract.address,
            "answerHash": wrongAnswerHash.hex(),
        }
        request = self.factory.post(
            "/api/post/",
            post_dict,
        )
        force_authenticate(request, self.answerer_user)
        response = views.answer(request)
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            content["message"],
            "Invalid answerHash.",
        )
