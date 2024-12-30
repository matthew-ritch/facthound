from django.conf import settings
from django.contrib.auth.backends import BaseBackend
import datetime, pytz
from web3 import Web3, EthereumTesterProvider
from eth_account.messages import SignableMessage
from eth_account.datastructures import SignedMessage

from siweauth.models import Nonce, Wallet

w3 = Web3()


def _nonce_is_valid(nonce: str) -> bool:
    """
    Check if given nonce exists and has not yet expired.
    :param nonce: The nonce string to validate.
    :return: True if valid else False.
    """
    n = Nonce.objects.filter(value=nonce).first()
    is_valid = False
    if n is not None and n.expiration > datetime.datetime.now(tz=pytz.UTC):
        is_valid = True
        n.delete()
    return is_valid


class SiweBackend(BaseBackend):
    """
    Authenticate via siwe
    """

    def authenticate(self, request, message: SignableMessage = None, signed_message: SignedMessage = None):
        # request must have nonce, address, message fields
        if None in [message, signed_message]:
            return None
        # check for format
        # TODO make sure message ends in timestamp and nonce
        if type(message.body) != str:
            body = str(message.body.decode())
        else:
            body = message.body
        len(body.split("\n")) >= 7
        # check for nonce in db
        nonce = body.split("\n")[-3][7:]  # char 7 and on from second to last line
        if not _nonce_is_valid(nonce):
            return None
        # recover address from nonce / signed message
        address = body.split("\n")[1]
        recovered_address = w3.eth.account.recover_message(
            signable_message=message, signature=signed_message.signature
        )
        # make sure recovered address is correct
        if address != recovered_address:
            return None
        # if user exists, return user
        wallet = Wallet.objects.filter(address=address).first()
        # if user doesn't exist, make a user for this wallet
        if wallet is None:
            wallet = Wallet.objects.create_user(address)
        return wallet

    def get_user(self, wallet_id):
        try:
            return Wallet.objects.get(pk=wallet_id)
        except Wallet.DoesNotExist:
            return None
