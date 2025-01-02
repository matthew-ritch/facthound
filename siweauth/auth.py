from functools import wraps
import datetime, pytz
from web3 import Web3, EthereumTesterProvider
from hexbytes import HexBytes
from eth_account.messages import SignableMessage
from eth_account.datastructures import SignedMessage
from eth_keys.exceptions import BadSignature
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import JsonResponse
from rest_framework import permissions
from datetime import datetime, timedelta
from .settings import (
    SIWE_MESSAGE_VALIDITY,
    SIWE_CHAIN_ID,
    SIWE_DOMAIN,
    SIWE_URI
)

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
    if n is not None: 
        if n.expiration > datetime.now(tz=pytz.UTC):
            is_valid = True
        n.delete()
    return is_valid


def request_passes_test(test_func, fail_message):
    """
    Decorator for views that checks that the request passes the given test,
    rejecting if not. The test should be a callable
    that takes the request object and returns True if the request passes.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapper_view(request, *args, **kwargs):
            if test_func(request):
                return view_func(request, *args, **kwargs)
            return JsonResponse({"status": 401, "message": fail_message})

        return _wrapper_view

    return decorator


def parse_siwe_message(message_body: str) -> dict:
    """Parse SIWE message into components"""
    lines = message_body.split('\n')
    try:
        domain = lines[0].split(' ')[0]
        address = lines[1].strip()
        uri = lines[5].split(': ')[1].strip()
        chain_id = int(lines[7].split(': ')[1])
        nonce = lines[8].split(': ')[1].strip()
        issued_at = datetime.fromisoformat(lines[9].split(': ')[1].strip())
        
        return {
            'domain': domain,
            'address': address,
            'uri': uri,
            'chain_id': chain_id,
            'nonce': nonce,
            'issued_at': issued_at
        }
    except (IndexError, ValueError):
        return None


def check_for_siwe(message, signed_message):
    message = SignableMessage(
        *[x.encode() if type(x) == str else x for x in message]
    )
    signed_message = SignedMessage(*signed_message)
    # check for format
    if type(message.body) != str:
        body = str(message.body.decode())
    else:
        body = message.body
    len(body.split("\n")) >= 7
    # Parse message components
    parsed = parse_siwe_message(body)
    if not parsed:
        return None
    # Validate message components
    # Validate timestamp
    now = datetime.now(parsed['issued_at'].tzinfo)
    if abs((now - parsed['issued_at']).total_seconds()) > SIWE_MESSAGE_VALIDITY * 60:
        return None
        
    # Validate chain ID
    # TODO multi-chain support
    if parsed['chain_id'] != SIWE_CHAIN_ID:
        return None
        
    # Validate domain and URI
    if parsed['domain'] != SIWE_DOMAIN or parsed['uri'] != SIWE_URI:
        return None
        
    # check for nonce in db
    if not _nonce_is_valid(parsed['nonce']):
        return None

    # recover address from nonce / signed message
    address = parsed['address']
    try:
        recovered_address = w3.eth.account.recover_message(
            signable_message=message, signature=HexBytes(signed_message.signature)
        )
    except:
        return None
    # make sure recovered address is correct
    if address != recovered_address:
        return None
    return recovered_address


def siwe_required(function=None):
    """
    Decorator for views that checks that the request contains correct siwe creds
    """

    actual_decorator = request_passes_test(check_for_siwe, "Failed SIWE authentication")
    if function:
        return actual_decorator(function)
    return actual_decorator


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow admins to edit objects.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Otherwise see if this wallet is an admin
        check_for_siwe(request)
        address = request.GET.get("address") or request.POST.get("address")
        return len(Wallet.filter(address=address, is_admin=True)) > 0


# TODO for posting question/answers, verify chain state
