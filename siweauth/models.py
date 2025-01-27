from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.contrib.auth.hashers import make_password
from web3 import Web3


def validate_ethereum_address(value):
    if not Web3.isChecksumAddress(value):
        raise ValidationError


class Nonce(models.Model):
    value = models.CharField(max_length=24, primary_key=True)
    expiration = models.DateTimeField()

    def __str__(self):
        return self.value


class UserManager(BaseUserManager):
    def create_user_address(self, address):
        """
        Creates and saves a User with the given eth address
        """
        if not address:
            raise ValueError("Users must have an eth address")

        user = self.model(
            wallet=address,
        )

        user.save(using=self._db)
        return user

    def create_user_username_email_password(self, username, email, password):
        """
        Creates and saves a User with the given username, email, and password
        """

        for field in [username, password, email]:
            if not field:
                raise ValueError("Users must have a username, password, and email")

        email = self.normalize_email(email)
        user = self.model(email=email, username=username)
        user.password = make_password(password)
        user.save()
        return user

    def create_superuser(self, username, password):
        """
        Creates and saves a superuser with the given eth address
        """
        u = self.create_user_username_email_password(username, "matt.ritch.33@gmail.com", password)
        u.is_admin = True
        u.is_staff = True
        u.save(using=self._db)
        return u


class User(AbstractBaseUser):
    wallet = models.CharField(
        verbose_name="Wallet Address",
        max_length=42,
        unique=True,
        null=True,
        validators=[
            RegexValidator(regex=r"^0x[a-fA-F0-9]{40}$"),
            validate_ethereum_address,
        ],
    )

    username = models.CharField(max_length=150, blank=True, null=True, unique=True)
    email = models.CharField(max_length=150, blank=True, null=True, unique=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    objects = UserManager()

    # TODO is this the right way to handle this?
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return self.is_admin

    def __str__(self):
        return self.username or self.wallet or "User"
