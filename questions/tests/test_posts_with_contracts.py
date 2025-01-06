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


# change views's w3 provider to this test provider
provider = EthereumTesterProvider()
w3 = Web3(provider)
views.w3 = w3

question_contract = json.load(open("contracts/question.json"))


# guide: https://web3py.readthedocs.io/en/v5/examples.html#contract-unit-tests-in-python


class TestQuestions(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        #
        self.eth_tester = provider.ethereum_tester
        self.owner = self.eth_tester.get_accounts()[0]
        self.oracle = self.eth_tester.get_accounts()[1]
        self.asker = self.eth_tester.get_accounts()[2]
        self.asker_user = User.objects.create_user_address(self.asker)
        views.allowed_owners.append(self.owner)

    def test_start_thread(self):
        question_dict = {
            "topic": "sometopic",
            "text": "I am wondering what to do about this topic.",
            "tags": ["A", "B", "C"],
        }
        # deploy question
        abi = question_contract["abi"]
        bytecode = question_contract["bytecode"]["object"]
        questionContract = w3.eth.contract(abi=abi, bytecode=bytecode)
        questionHash = Web3.solidity_keccak(['address', 'string'], [self.asker, question_dict["text"]])
        tx_hash = questionContract.constructor(
            self.owner, self.oracle, self.asker, questionHash
        ).transact(
            {
                "from": self.asker,
                "value": 1
            }
        )
        # wait for the transaction to be mined
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, 180)
        #pack the required info
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

    # def test_reply_to_thread(self):
    #     # make thread
    #     request = self.factory.post(
    #         "/api/post/",
    #         question_dict,
    #     )
    #     request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token}"
    #     response = views.post(request)
    #     content = json.loads(response.content)
    #     self.assertEqual(response.status_code, 200)
    #     thread = Thread.objects.get(pk=content["thread"])
    #     # post again
    #     post_dict = {"thread": thread.pk, "text": "follow up post"}
    #     request = self.factory.post(
    #         "/api/post/",
    #         post_dict,
    #     )
    #     request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token2}"
    #     response = views.question(request)
    #     content = json.loads(response.content)
    #     # make sure post was created
    #     post = Post.objects.get(text=post_dict["text"], thread=thread)
    #     postpk = Post.objects.get(pk=content["post"])
    #     self.assertEqual(post, postpk)
    #     self.assertEqual(post.text, post_dict["text"])
    #     self.assertEqual(self.user2, post.poster)
    #     # make sure question was created
    #     question = Question.objects.get(
    #         post__text=post_dict["text"], post__thread=thread
    #     )
    #     questionpk = Question.objects.get(pk=content["question"])
    #     self.assertEqual(question, questionpk)
    #     self.assertEqual(question.post.text, post_dict["text"])
    #     self.assertEqual(self.user2, question.asker)
    #     # make sure question and post are identified together
    #     self.assertEqual(question.post, post)
    #     # thread should have 2 post. test associations
    #     self.assertEqual(thread.post_set.all().count(), 2)
    #     self.assertEqual(thread, post.thread)

    # def test_question_no_thread_fails(self):
    #     post_dict = {"text": "follow up post"}
    #     request = self.factory.post(
    #         "/api/post/",
    #         post_dict,
    #     )
    #     request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token2}"
    #     response = views.question(request)
    #     content = json.loads(response.content)
    #     self.assertNotIn("post", content.keys())
    #     self.assertEqual(
    #         content["message"],
    #         "One of thread or topic must be specified. You cannot specify both.",
    #     )

    # def test_thread_no_text_fails(self):
    #     post_dict = {"topic": "topic"}
    #     request = self.factory.post(
    #         "/api/post/",
    #         post_dict,
    #     )
    #     request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token2}"
    #     response = views.question(request)
    #     content = json.loads(response.content)
    #     self.assertNotIn("post", content.keys())
    #     self.assertEqual(content["message"], "Your post needs text.")

    # def test_reply_to_thread_no_text_fails(self):
    #     # make thread
    #     request = self.factory.post(
    #         "/api/post/",
    #         question_dict,
    #     )
    #     request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token}"
    #     response = views.post(request)
    #     content = json.loads(response.content)
    #     self.assertEqual(response.status_code, 200)
    #     thread = Thread.objects.get(pk=content["thread"])
    #     # post again
    #     post_dict = {"thread": thread.pk}
    #     request = self.factory.post(
    #         "/api/post/",
    #         post_dict,
    #     )
    #     request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token2}"
    #     response = views.question(request)
    #     content = json.loads(response.content)
    #     self.assertNotIn("post", content.keys())
    #     self.assertEqual(content["message"], "Your post needs text.")
