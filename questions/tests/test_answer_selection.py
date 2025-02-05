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


# guide: https://web3py.readthedocs.io/en/v5/examples.html#contract-unit-tests-in-python


class TestSelectionSansContracts(TestCase):
    def setUp(self):
        # change views's w3 provider to this test provider
        provider = EthereumTesterProvider()
        self.w3 = Web3(provider)
        views.w3 = self.w3

        with open("contracts/FactHound.json", "rb") as f:
            facthound_contract = json.load(f)
        #
        self.factory = RequestFactory()
        #
        self.eth_tester = provider.ethereum_tester
        self.owner = self.eth_tester.get_accounts()[0]
        self.oracle = self.eth_tester.get_accounts()[1]
        self.asker = self.eth_tester.get_accounts()[2]
        self.answerer = self.eth_tester.get_accounts()[3]
        self.asker_user = User.objects.create_user_address(self.asker)
        self.answerer_user = User.objects.create_user_address(self.answerer)
        views.allowed_owners.append(self.owner)
        #
        self.thread = Thread.objects.create(
            topic="nothing of import", dt=datetime.datetime.now(pytz.UTC)
        )
        qp = Post.objects.create(
            thread=self.thread,
            text="Question Text",
            dt=datetime.datetime.now(tz=pytz.UTC),
            poster=self.asker_user,
        )
        self.question = Question.objects.create(
            post=qp,
            asker=self.asker_user,
            status="OP",
        )
        ap = Post.objects.create(
            thread=self.thread,
            text="Answer Text",
            dt=datetime.datetime.now(tz=pytz.UTC),
            poster=self.answerer_user,
        )
        self.answer = Answer.objects.create(
            question=self.question,
            post=ap,
            answerer=self.answerer_user,
            status="OP",
        )

    def test_select_answer(self):
        selection_dict = {"question": self.question.pk, "answer": self.answer.pk}
        request = self.factory.post(
            "/api/selection/",
            selection_dict,
        )
        force_authenticate(request, self.asker_user)
        response = views.selection(request)
        content = json.loads(response.content)
        question = Question.objects.get(pk=content["question"])
        answer = Answer.objects.get(pk=content["answer"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(question.status, "AS")
        self.assertEqual(answer.status, "SE")
        self.assertEqual(question.answer_set.filter(status="SE").first(), answer)

    def test_no_question(self):
        selection_dict = {"question": 999, "answer": self.answer.pk}
        request = self.factory.post(
            "/api/selection/",
            selection_dict,
        )
        force_authenticate(request, self.asker_user)
        response = views.selection(request)
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(content["message"], "No question with that id exists.")

    def test_no_answer(self):
        selection_dict = {"question": self.question.pk, "answer": 999}
        request = self.factory.post(
            "/api/selection/",
            selection_dict,
        )
        force_authenticate(request, self.asker_user)
        response = views.selection(request)
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(content["message"], "No answer with that id exists.")

    def test_mismatch(self):
        qp2 = Post.objects.create(
            thread=self.thread,
            text="Question Text 2",
            dt=datetime.datetime.now(tz=pytz.UTC),
            poster=self.asker_user,
        )
        question2 = Question.objects.create(
            post=qp2,
            asker=self.asker_user,
            status="OP",
        )
        selection_dict = {"question": question2.pk, "answer": self.answer.pk}
        request = self.factory.post(
            "/api/selection/",
            selection_dict,
        )
        force_authenticate(request, self.asker_user)
        response = views.selection(request)
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            content["message"], "This answer does not answer this question."
        )

    def test_not_asker(self):
        selection_dict = {"question": self.question.pk, "answer": self.answer.pk}
        request = self.factory.post(
            "/api/selection/",
            selection_dict,
        )
        force_authenticate(request, self.answerer_user)
        response = views.selection(request)
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(content["message"], "Only the question's asker can do this.")


class TestSelectionWithContracts(TestCase):
    def setUp(self):
        # change views's w3 provider to this test provider
        provider = EthereumTesterProvider()
        self.w3 = Web3(provider)
        views.w3 = self.w3

        with open("contracts/FactHound.json", "rb") as f:
            facthound_contract = json.load(f)
        self.factory = RequestFactory()
        
        # Setup accounts
        self.eth_tester = provider.ethereum_tester
        self.owner = self.eth_tester.get_accounts()[0]
        self.oracle = self.eth_tester.get_accounts()[1]
        self.asker = self.eth_tester.get_accounts()[2]
        self.answerer = self.eth_tester.get_accounts()[3]
        self.asker_user = User.objects.create_user_address(self.asker)
        self.answerer_user = User.objects.create_user_address(self.answerer)
        views.allowed_owners.append(self.owner)

        # Deploy contract
        abi = facthound_contract["abi"]
        bytecode = facthound_contract["bytecode"]["object"]
        Contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
        tx_hash = Contract.constructor(self.oracle, 100).transact({"from": self.owner})
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        self.contract_address = tx_receipt["contractAddress"]
        self.contract = self.w3.eth.contract(address=self.contract_address, abi=abi, decode_tuples=True)

        # Create question
        question_text = "I am wondering what to do about this topic."
        self.question_hash = Web3.solidity_keccak(
            ["address", "string"], [self.asker, question_text]
        )
        
        tx_hash = self.contract.functions.createQuestion(
            self.question_hash
        ).transact({"from": self.asker, "value": 1000000})
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        # Create DB entries
        self.thread = Thread.objects.create(
            topic="nothing of import", dt=datetime.datetime.now(pytz.UTC)
        )
        qp = Post.objects.create(
            thread=self.thread,
            text=question_text,
            dt=datetime.datetime.now(tz=pytz.UTC),
            poster=self.asker_user,
        )
        self.question = Question.objects.create(
            questionHash=self.question_hash,
            contractAddress=self.contract_address,
            post=qp,
            asker=self.asker_user,
            bounty=1000000,
            status="OP",
        )

        # Create answer
        answer_text = "You should do everything."
        self.answer_hash = Web3.solidity_keccak(
            ["address", "string"], [self.answerer, answer_text]
        )
        tx_hash = self.contract.functions.createAnswer(
            self.question_hash,
            self.answer_hash
        ).transact({"from": self.answerer})
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        ap = Post.objects.create(
            thread=self.thread,
            text=answer_text,
            dt=datetime.datetime.now(tz=pytz.UTC),
            poster=self.answerer_user,
        )
        self.answer = Answer.objects.create(
            answerHash=self.answer_hash,
            question=self.question,
            post=ap,
            answerer=self.answerer_user,
            status="UN",
        )

    def test_select_answer(self):
        # Select answer in contract
        tx_hash = self.contract.functions.selectAnswer(
            self.question_hash,
            self.answer_hash
        ).transact({"from": self.asker})
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        # Select in backend
        selection_dict = {"question": self.question.pk, "answer": self.answer.pk}
        request = self.factory.post("/api/selection/", selection_dict)
        force_authenticate(request, self.asker_user)
        response = views.selection(request)
        content = json.loads(response.content)
        
        question = Question.objects.get(pk=content["question"])
        answer = Answer.objects.get(pk=content["answer"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(question.status, "AS")
        self.assertEqual(answer.status, "SE")
        self.assertEqual(question.answer_set.filter(status="SE").first(), answer)

    def test_not_in_contract(self):
        selection_dict = {"question": self.question.pk, "answer": self.answer.pk}
        request = self.factory.post("/api/selection/", selection_dict)
        force_authenticate(request, self.asker_user)
        response = views.selection(request)
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            content["message"],
            f"This answer must be selected in the contract at address {self.question.contractAddress}."
        )

    def test_oracle_can_select(self):
        # Oracle selects answer in contract
        tx_hash = self.contract.functions.selectAnswer(
            self.question_hash,
            self.answer_hash
        ).transact({"from": self.oracle})
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        # Oracle selects in backend
        oracle_user = User.objects.create_user_address(self.oracle)
        selection_dict = {"question": self.question.pk, "answer": self.answer.pk}
        request = self.factory.post("/api/selection/", selection_dict)
        force_authenticate(request, oracle_user)
        response = views.selection(request)
        
        self.assertEqual(response.status_code, 200)
        question = Question.objects.get(pk=self.question.pk)
        answer = Answer.objects.get(pk=self.answer.pk)
        self.assertEqual(question.status, "AS")
        self.assertEqual(answer.status, "SE")
