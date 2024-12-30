from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser

from web3 import Web3


def validate_ethereum_address(value):
    if not Web3.isChecksumAddress(value):
        raise ValidationError


class Nonce(models.Model):
    value = models.CharField(max_length=24, primary_key=True)
    expiration = models.DateTimeField()

    def __str__(self):
        return self.value


class WalletManager(BaseUserManager):
    def create_user(self, address):
        """
        Creates and saves a User with the given eth address
        """
        if not address:
            raise ValueError("Users must have an eth address")

        user = self.model(
            address=address,
        )

        user.save(using=self._db)
        return user

    def create_superuser(self, address):
        """
        Creates and saves a superuser with the given eth address
        """
        u = self.create_user(address, password=address)
        u.is_admin = True
        u.save(using=self._db)
        return u


class Wallet(AbstractBaseUser):
    address = models.CharField(
        verbose_name="Wallet Address",
        max_length=42,
        unique=True,
        validators=[
            RegexValidator(regex=r"^0x[a-fA-F0-9]{40}$"),
            validate_ethereum_address,
        ],
    )

    username = models.CharField(max_length=150, blank=True, null=True)
    is_admin = models.BooleanField(default=False)
    objects = WalletManager()

    #TODO is this the right way to handle this?
    USERNAME_FIELD = 'address'
    REQUIRED_FIELDS = []

