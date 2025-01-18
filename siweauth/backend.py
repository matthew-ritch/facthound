from django.contrib.auth.backends import BaseBackend

from web3 import Web3
from eth_account.messages import SignableMessage
import logging

from siweauth.models import User
from siweauth.auth import check_for_siwe


logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logging.basicConfig(
    filename="facthound.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

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
        user = User.objects.filter(wallet=recovered_address).first()
        # if user doesn't exist, make a user for this wallet
        if user is None:
            user = User.objects.create_user_address(recovered_address)
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
