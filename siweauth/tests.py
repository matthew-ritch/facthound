from django.test import TestCase
from django.test import RequestFactory

from django.contrib.auth import authenticate
from siweauth.backend import SiweBackend

from siweauth.models import Nonce, Wallet
from siweauth.views import get_nonce, TokenObtainPairView

from web3 import Web3
from eth_account.messages import encode_defunct
import json
import datetime

from hexbytes import HexBytes
from siwe.siwe import SiweMessage

# print(f'private key={w3.to_hex(acc.key)}, account={acc.address}')

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


# class TestGetNonce(TestCase):

#     def setUp(self):
#         self.factory = RequestFactory()
#         self.w3 = Web3()
#         self.acc = self.w3.eth.account.create()

#     def test_get_nonce(self):
#         request = self.factory.get("/api/get_nonce/")
#         response = get_nonce(request)
#         nonce = json.loads(response.content)["nonce"]
#         match_query = Nonce.objects.filter(value=nonce)
#         self.assertEqual(len(match_query), 1)


# class TestSiweAuth(TestCase):

#     def setUp(self):
#         self.factory = RequestFactory()
#         self.w3 = Web3()
#         self.acc = self.w3.eth.account.create()
#         # get nonce
#         request = self.factory.get("/api/get_nonce/")
#         response = get_nonce(request)
#         self.nonce = json.loads(response.content)["nonce"]

#     def test_authenticate_new_user(self):
#         # this will also create the user
#         self.assertEqual(len(Wallet.objects.filter(address=self.acc.address)), 0)
#         # create verification triple
#         message = make_message(self.acc.address, self.nonce)
#         encoded_message = encode_defunct(text=message)
#         signed_message = self.w3.eth.account.sign_message(
#             encoded_message,
#             self.w3.to_hex(self.acc.key),
#         )

#         wallet = authenticate(message = encoded_message, signed_message = signed_message)
#         self.assertIsNotNone(wallet)
#         #try again with same nonce - will not work
#         wallet = authenticate(message = encoded_message, signed_message = signed_message)
#         self.assertIsNone(wallet)

#     def test_authenticate_returning_user(self):
#         # this will also create the user
#         self.assertEqual(len(Wallet.objects.filter(address=self.acc.address)), 0)
#         # create verification triple
#         message = make_message(self.acc.address, self.nonce)
#         encoded_message = encode_defunct(text=message)
#         signed_message = self.w3.eth.account.sign_message(
#             encoded_message,
#             self.w3.to_hex(self.acc.key),
#         )

#         wallet = authenticate(message = encoded_message, signed_message = signed_message)
#         self.assertIsNotNone(wallet)
#         #try again with same nonce - will not work
#         wallet = authenticate(message = encoded_message, signed_message = signed_message)
#         self.assertIsNone(wallet)
#         # make new nonce and message
#         self.assertEqual(len(Wallet.objects.filter(address=self.acc.address)), 1)
#         request = self.factory.get("/api/get_nonce/")
#         response = get_nonce(request)
#         self.nonce = json.loads(response.content)["nonce"]
#         message = make_message(self.acc.address, self.nonce)
#         encoded_message = encode_defunct(text=message)
#         signed_message = self.w3.eth.account.sign_message(
#             encoded_message,
#             self.w3.to_hex(self.acc.key),
#         )

#         wallet = authenticate(message = encoded_message, signed_message = signed_message)
#         self.assertIsNotNone(wallet)
#         self.assertEqual(len(Wallet.objects.filter(address=self.acc.address)), 1)
#         #try again with same nonce - will not work
#         wallet = authenticate(message = encoded_message, signed_message = signed_message)
#         self.assertIsNone(wallet)



class TestGetJWTToken(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.w3 = Web3()
        self.acc = self.w3.eth.account.create()
        # get nonce
        request = self.factory.get("//api/get_nonce/")
        response = get_nonce(request)
        self.nonce = json.loads(response.content)["nonce"]
        message = make_message(self.acc.address, self.nonce)
        self.encoded_message = encode_defunct(text=message)
        self.signed_message = self.w3.eth.account.sign_message(
            self.encoded_message,
            self.w3.to_hex(self.acc.key),
        )
        # self.wallet = authenticate(message = self.encoded_message, signed_message = self.signed_message)
    
    def test_get_token(self):
        request = self.factory.post("/api/token/", {"address":self.acc.address, "message": self.encoded_message, "signed_message": self.signed_message})
        # request.user = self.wallet
        response = TokenObtainPairView.as_view()(request)
        print(response)