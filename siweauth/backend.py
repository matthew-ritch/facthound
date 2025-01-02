from django.contrib.auth.backends import BaseBackend

from web3 import Web3
from eth_account.messages import SignableMessage

from siweauth.models import Wallet
from siweauth.auth import check_for_siwe


w3 = Web3()


class SiweBackend(BaseBackend):
    """
    Authenticate via siwe
    """

    def authenticate(
        self, request, message: SignableMessage = None, signed_message=None
    ):
        # request must have message and signed_message fields
        if None in [message, signed_message]:
            return None
        recovered_address = check_for_siwe(message, signed_message)
        if recovered_address is None:
            return None
        # if user exists, return user
        wallet = Wallet.objects.filter(address=recovered_address).first()
        # if user doesn't exist, make a user for this wallet
        if wallet is None:
            wallet = Wallet.objects.create_user(recovered_address)
        return wallet

    def get_user(self, wallet_id):
        try:
            return Wallet.objects.get(pk=wallet_id)
        except Wallet.DoesNotExist:
            return None
