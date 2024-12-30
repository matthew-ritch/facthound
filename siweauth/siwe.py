from functools import wraps
import datetime, pytz
from web3 import Web3, EthereumTesterProvider

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import JsonResponse
from rest_framework import permissions

from siweauth.models import Nonce, Wallet



def _nonce_is_valid(nonce: str) -> bool:
    """
    Check if given nonce exists and has not yet expired.
    :param nonce: The nonce string to validate.
    :return: True if valid else False.
    """
    n = Nonce.objects.get(value=nonce)
    is_valid = False
    if n is not None and n.expiration > datetime.datetime.now(tz=pytz.UTC):
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


def check_for_siwe(request):
        # request must have nonce, address, message fields
        address = request.GET.get("address") or request.POST.get("address")
        message = request.GET.get("message") or request.POST.get("message")
        signed_message = request.GET.get("signed_message") or request.POST.get(
            "signed_message"
        )
        if None in [address, message, signed_message]:
            return False
        # check for format
        # TODO make sure message ends in timestamp and nonce
        len(message.split("\n")) >= 7
        # check for nonce in db
        nonce = message.split("\n")[-2][7:]  # char 7 and on from second to last line
        if not _nonce_is_valid(nonce):
            return False
        # recover message from nonce / signed message
        recovered_address = Web3.eth.account.recover_message(
            message, signature=signed_message
        )
        # if all good, pass on to api view
        if address == recovered_address:
            return True


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
        return len(Wallet.filter(address=address, is_admin = True)) > 0
    

# TODO for posting question/answers, verify chain state
