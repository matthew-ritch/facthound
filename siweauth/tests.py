from web3 import Web3
from eth_account.messages import encode_defunct
import json
import datetime
from hexbytes import HexBytes
from siwe.siwe import SiweMessage
from eth_account.messages import SignableMessage
from eth_account.datastructures import SignedMessage

from django.test import TestCase
from django.test import RequestFactory
from django.contrib.auth import authenticate

from siweauth.backend import SiweBackend
from siweauth.models import Nonce, Wallet
from siweauth.views import get_nonce, TokenObtainPairView, who_am_i
from siweauth.auth import check_for_siwe, _nonce_is_valid


def make_message(address, nonce):
    message = f"""testhost wants you to sign in with your Ethereum account:
{address}

To make posts.

URI: https://testhost/api/token/
Version: 1
Chain ID: 1
Nonce: {nonce}
Issued At: {datetime.datetime.now()}
        """
    return message


class TestGetNonce(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.w3 = Web3()
        self.acc = self.w3.eth.account.create()

    def test_get_nonce(self):
        request = self.factory.get("/api/get_nonce/")
        response = get_nonce(request)
        nonce = json.loads(response.content)["nonce"]
        match_query = Nonce.objects.filter(value=nonce)
        self.assertEqual(len(match_query), 1)


class TestNonceIsValid(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.w3 = Web3()
        self.acc = self.w3.eth.account.create()

    def test_check_new_nonce(self):
        request = self.factory.get("/api/get_nonce/")
        response = get_nonce(request)
        nonce = json.loads(response.content)["nonce"]
        match_query = Nonce.objects.filter(value=nonce)
        self.assertEqual(len(match_query), 1)
        self.assertTrue(_nonce_is_valid(nonce))
        # test with already-used nonce
        self.assertFalse(_nonce_is_valid(nonce))

    def test_check_expired_nonce(self):
        nonce = Nonce.objects.create(
            value="test", expiration=datetime.datetime.now(datetime.timezone.utc)
        )
        match_query = Nonce.objects.filter(value=nonce)
        self.assertEqual(len(match_query), 1)
        self.assertFalse(_nonce_is_valid(nonce))
        # test again with expired nonce
        self.assertFalse(_nonce_is_valid(nonce))


class TestSiweAuth(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.w3 = Web3()
        self.acc = self.w3.eth.account.create()
        # get nonce
        request = self.factory.get("/api/get_nonce/")
        response = get_nonce(request)
        self.nonce = json.loads(response.content)["nonce"]

    def test_authenticate_new_user(self):
        # this will also create the user
        self.assertEqual(len(Wallet.objects.filter(address=self.acc.address)), 0)
        # create verification triple
        message = make_message(self.acc.address, self.nonce)
        encoded_message = encode_defunct(text=message)
        signed_message = self.w3.eth.account.sign_message(
            encoded_message,
            self.w3.to_hex(self.acc.key),
        )

        wallet = authenticate(message=encoded_message, signed_message=signed_message)
        self.assertIsNotNone(wallet)
        # try again with same nonce - will not work
        wallet = authenticate(message=encoded_message, signed_message=signed_message)
        self.assertIsNone(wallet)

    def test_authenticate_returning_user(self):
        # this will also create the user
        self.assertEqual(len(Wallet.objects.filter(address=self.acc.address)), 0)
        # create verification triple
        message = make_message(self.acc.address, self.nonce)
        encoded_message = encode_defunct(text=message)
        signed_message = self.w3.eth.account.sign_message(
            encoded_message,
            self.w3.to_hex(self.acc.key),
        )

        wallet = authenticate(message=encoded_message, signed_message=signed_message)
        self.assertIsNotNone(wallet)
        # try again with same nonce - will not work
        wallet = authenticate(message=encoded_message, signed_message=signed_message)
        self.assertIsNone(wallet)
        # make new nonce and message
        self.assertEqual(len(Wallet.objects.filter(address=self.acc.address)), 1)
        request = self.factory.get("/api/get_nonce/")
        response = get_nonce(request)
        self.nonce = json.loads(response.content)["nonce"]
        message = make_message(self.acc.address, self.nonce)
        encoded_message = encode_defunct(text=message)
        signed_message = self.w3.eth.account.sign_message(
            encoded_message,
            self.w3.to_hex(self.acc.key),
        )

        wallet = authenticate(message=encoded_message, signed_message=signed_message)
        self.assertIsNotNone(wallet)
        self.assertEqual(len(Wallet.objects.filter(address=self.acc.address)), 1)
        # try again with same nonce - will not work
        wallet = authenticate(message=encoded_message, signed_message=signed_message)
        self.assertIsNone(wallet)


class TestGetJWTToken(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.w3 = Web3()
        self.acc = self.w3.eth.account.create()
        # get nonce
        request = self.factory.get("/api/get_nonce/")
        response = get_nonce(request)
        self.nonce = json.loads(response.content)["nonce"]
        message = make_message(self.acc.address, self.nonce)
        self.encoded_message = encode_defunct(text=message)
        self.signed_message = self.w3.eth.account.sign_message(
            self.encoded_message,
            self.w3.to_hex(self.acc.key),
        )

    def test_get_token(self):
        message_serialized = [x.decode() for x in self.encoded_message]
        signed_message_serialized = [
            self.signed_message.messageHash.hex(),
            self.signed_message.r,
            self.signed_message.s,
            self.signed_message.v,
            self.signed_message.signature.hex(),
        ]
        request = self.factory.post(
            "/api/token/",
            {
                "message": message_serialized,
                "signed_message": signed_message_serialized,
            },
        )
        # request.user = self.wallet
        response = TokenObtainPairView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    # test use token
    def test_use_token(self):
        message_serialized = [x.decode() for x in self.encoded_message]
        signed_message_serialized = [
            self.signed_message.messageHash.hex(),
            self.signed_message.r,
            self.signed_message.s,
            self.signed_message.v,
            self.signed_message.signature.hex(),
        ]
        request = self.factory.post(
            "/api/token/",
            {
                "message": message_serialized,
                "signed_message": signed_message_serialized,
            },
        )
        response = TokenObtainPairView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        token = json.loads(response.render().content)["access"]
        request = self.factory.get(
            "/api/who_am_i/",
            {},
        )
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {token}"

        response = who_am_i(request=request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["message"], self.acc.address)


class TestCheckForSiwe(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.w3 = Web3()
        self.acc = self.w3.eth.account.create()
        # get nonce
        request = self.factory.get("/api/get_nonce/")
        response = get_nonce(request)
        self.nonce = json.loads(response.content)["nonce"]

    def test_check_for_siwe_valid(self):
        message = make_message(self.acc.address, self.nonce)
        encoded_message = encode_defunct(text=message)
        signed_message = self.w3.eth.account.sign_message(
            encoded_message,
            self.w3.to_hex(self.acc.key),
        )
        message_serialized = [x.decode() for x in encoded_message]
        signed_message_serialized = [
            signed_message.messageHash.hex(),
            signed_message.r,
            signed_message.s,
            signed_message.v,
            signed_message.signature.hex(),
        ]
        recovered_address = check_for_siwe(
            message_serialized, signed_message_serialized
        )
        self.assertEqual(recovered_address, self.acc.address)

    def test_check_for_siwe_invalid_nonce(self):
        message = make_message(self.acc.address, "invalid_nonce")
        encoded_message = encode_defunct(text=message)
        signed_message = self.w3.eth.account.sign_message(
            encoded_message,
            self.w3.to_hex(self.acc.key),
        )
        message_serialized = [x.decode() for x in encoded_message]
        signed_message_serialized = [
            signed_message.messageHash.hex(),
            signed_message.r,
            signed_message.s,
            signed_message.v,
            signed_message.signature.hex(),
        ]
        recovered_address = check_for_siwe(
            message_serialized, signed_message_serialized
        )
        self.assertIsNone(recovered_address)

    def test_check_for_siwe_invalid_signature(self):
        message = make_message(self.acc.address, self.nonce)
        encoded_message = encode_defunct(text=message)
        signed_message = self.w3.eth.account.sign_message(
            encoded_message,
            self.w3.to_hex(self.acc.key),
        )
        message_serialized = [x.decode() for x in encoded_message]
        tampered_signature_string = (
            "0x" + signed_message.signature.hex()[2:][::-1]
        )  # tamper with the signature
        signed_message_serialized = [
            signed_message.messageHash.hex(),
            signed_message.r,
            signed_message.s,
            signed_message.v,
            tampered_signature_string,
        ]
        recovered_address = check_for_siwe(
            message_serialized, signed_message_serialized
        )
        self.assertIsNone(recovered_address)


bytes
