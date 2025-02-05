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

        with open("contracts/FactHound.json", "rb") as f:
            self.facthound_contract = json.load(f)


# guide: https://web3py.readthedocs.io/en/v5/examples.html#contract-unit-tests-in-python


class TestQuestions(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

        # Setup accounts
        self.eth_tester = self.provider.ethereum_tester
        self.owner = self.eth_tester.get_accounts()[0]
        self.oracle = self.eth_tester.get_accounts()[1]
        self.asker = self.eth_tester.get_accounts()[2]
        self.asker_user = User.objects.create_user_address(self.asker)
        views.allowed_owners.append(self.owner)

        # Deploy contract
        abi = self.facthound_contract["abi"]
        bytecode = self.facthound_contract["bytecode"]["object"]
        Contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
        tx_hash = Contract.constructor(self.oracle, 100).transact({"from": self.owner})
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        self.contract_address = tx_receipt["contractAddress"]
        self.contract = self.w3.eth.contract(
            address=self.contract_address, abi=abi, decode_tuples=True
        )

    def test_start_thread(self):
        question_dict = {
            "topic": "sometopic",
            "text": "I am wondering what to do about this topic.",
            "tags": ["a", "b", "c"],
        }

        # Create question in contract
        questionHash = Web3.solidity_keccak(
            ["address", "string"], [self.asker, question_dict["text"]]
        )
        tx_hash = self.contract.functions.createQuestion(questionHash).transact(
            {"from": self.asker, "value": 1000000}
        )
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        # Add contract data to question dict
        question_dict["contractAddress"] = self.contract_address
        question_dict["questionHash"] = questionHash.hex()

        request = self.factory.post(
            "/api/question/", data=question_dict, content_type="application/json"
        )
        force_authenticate(request, self.asker_user)
        response = views.question(request)

        # Verify response
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)

        # Verify database objects
        thread = Thread.objects.get(topic=question_dict["topic"])
        post = Post.objects.get(text=question_dict["text"])
        question = Question.objects.get(post=post)

        self.assertEqual(thread.pk, content["thread"])
        self.assertEqual(post.text, question_dict["text"])
        self.assertEqual(self.asker_user, post.poster)
        self.assertEqual(question.contractAddress, self.contract_address)
        self.assertEqual(question.questionHash, questionHash)
        self.assertEqual(question.bounty, 990000)
        self.assertEqual(question.post, post)

        # Verify tags
        self.assertEqual(thread.tag_set.count(), 3)
        for t in question_dict["tags"]:
            self.assertTrue(thread.tag_set.filter(name=t).exists())

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
            "contractAddress": "0xInvalidAddress",
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
        # Deploy contract with different owner
        abi = self.facthound_contract["abi"]
        bytecode = self.facthound_contract["bytecode"]["object"]
        Contract = self.w3.eth.contract(abi=abi, bytecode=bytecode, decode_tuples=True)
        tx_hash = Contract.constructor(self.oracle, 100).transact(
            {"from": self.oracle}
        )  # Different owner
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        questionHash = Web3.solidity_keccak(
            ["address", "string"], [self.asker, question_dict["text"]]
        )
        question_dict["contractAddress"] = tx_receipt["contractAddress"]
        question_dict["questionHash"] = questionHash.hex()

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
        
        # Deploy contract with oracle
        abi = self.facthound_contract["abi"]
        bytecode = self.facthound_contract["bytecode"]["object"]
        Contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
        tx_hash = Contract.constructor(self.oracle, 100).transact({"from": self.owner})
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        # Create question with incorrect text
        questionHash = Web3.solidity_keccak(
            ["address", "string"], [self.oracle, question_dict["text"]]
        )
        
        contract_address = tx_receipt["contractAddress"]
        tx_hash = self.contract.functions.createQuestion(questionHash).transact(
            {"from": self.oracle, "value": 1}
        )
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        # Test with modified text
        question_dict["text"] = question_dict["text"] + "HA!"
        question_dict["contractAddress"] = contract_address
        question_dict["questionHash"] = questionHash.hex()
        
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

        # Setup accounts
        self.eth_tester = self.provider.ethereum_tester
        self.owner = self.eth_tester.get_accounts()[0]
        self.oracle = self.eth_tester.get_accounts()[1]
        self.asker = self.eth_tester.get_accounts()[2]
        self.asker_user = User.objects.create_user_address(self.asker)
        self.answerer = self.eth_tester.get_accounts()[3]
        self.answerer_user = User.objects.create_user_address(self.answerer)
        views.allowed_owners.append(self.owner)

        # Deploy contract
        abi = self.facthound_contract["abi"]
        bytecode = self.facthound_contract["bytecode"]["object"]
        Contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
        tx_hash = Contract.constructor(self.oracle, 100).transact({"from": self.owner})
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        self.contract_address = tx_receipt["contractAddress"]
        self.contract = self.w3.eth.contract(
            address=self.contract_address, abi=abi, decode_tuples=True
        )

        # Create question in contract
        question_dict = {
            "topic": "sometopic",
            "text": "I am wondering what to do about this topic.",
            "tags": ["a", "b", "c"],
        }
        self.question_hash = Web3.solidity_keccak(
            ["address", "string"], [self.asker, question_dict["text"]]
        )
        tx_hash = self.contract.functions.createQuestion(self.question_hash).transact(
            {"from": self.asker, "value": 1000000}
        )
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        # Create question in database
        question_dict["contractAddress"] = self.contract_address
        question_dict["questionHash"] = self.question_hash.hex()
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
        # Create answer in contract
        answer_text = "You should do nothing."
        answer_hash = Web3.solidity_keccak(
            ["address", "string"], [self.answerer, answer_text]
        )
        tx_hash = self.contract.functions.createAnswer(
            self.question_hash, answer_hash
        ).transact({"from": self.answerer})
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        # Post answer through API
        post_dict = {
            "thread": self.thread.pk,
            "text": answer_text,
            "question": self.question.pk,
            "contractAddress": self.contract_address,
            "questionHash": self.question_hash.hex(),
            "answerHash": answer_hash.hex(),
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
            self.contract.caller.getAnswerer(self.question_hash, answer.answerHash),
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
            contractAddress="0x1efF47bc3a10a45D4B230B5d10E37751FE6AA718",
        )
        #
        answerString = "You should do nothing."
        answerHash = Web3.solidity_keccak(
            ["address", "string"], [self.answerer, answerString]
        )
        # make answer object
        self.contract.functions.createAnswer(self.question_hash, answerHash).transact(
            {"from": self.answerer}
        )
        # post it
        post_dict = {
            "thread": self.thread.pk,
            "text": "You should do nothing.",
            "question": wrongQuestion.pk,
            "contractAddress": "0x1efF47bc3a10a45D4B230B5d10E37751FE6AA718",
            "questionHash": self.question_hash.hex(),
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

    def test_mismatched_question_and_contractAddress(self):
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
        self.contract.functions.createAnswer(self.question_hash, answerHash).transact(
            {"from": self.answerer}
        )
        # post it
        post_dict = {
            "thread": self.thread.pk,
            "text": "You should do nothing.",
            "question": wrongQuestion.pk,
            "contractAddress": self.contract.address,
            "questionHash": self.question_hash.hex(),
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
            "This question does not match this contractAddress.",
        )

    def test_unexpected_answerHash(self):
        answerString = "You should do nothing."
        answerHash = Web3.solidity_keccak(
            ["address", "string"], [self.answerer, answerString]
        )
        # make answer object
        self.contract.functions.createAnswer(self.question_hash, answerHash).transact(
            {"from": self.answerer}
        )
        # post it
        post_dict = {
            "thread": self.thread.pk,
            "text": "You should do nothing."
            + "HA!",  # add to the text so the hash will be invalid
            "question": self.question.pk,
            "contractAddress": self.contract.address,
            "questionHash": self.question_hash.hex(),
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
        self.contract.functions.createAnswer(self.question_hash, answerHash).transact(
            {"from": self.answerer}
        )
        # post it
        post_dict = {
            "thread": self.thread.pk,
            "text": "You should do nothing.wrongend",
            "question": self.question.pk,
            "contractAddress": self.contract.address,
            "questionHash": self.question_hash.hex(),
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
