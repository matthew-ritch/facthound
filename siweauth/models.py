"""
Database models for the Sign-In with Ethereum (SIWE) authentication system.

This module defines the User model with both traditional and Ethereum wallet authentication,
as well as the Nonce model for securing SIWE authentication requests.
"""

from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.contrib.auth.hashers import make_password
from web3 import Web3


def validate_ethereum_address(value):
    """
    Validate that an Ethereum address is correctly checksummed.
    
    Args:
        value: The Ethereum address to validate
        
    Raises:
        ValidationError: If the address is not a valid checksummed Ethereum address
    """
    if not Web3.isChecksumAddress(value):
        raise ValidationError


class Nonce(models.Model):
    """
    A temporary nonce used for SIWE authentication.
    
    Nonces are single-use random values that prevent replay attacks during
    authentication and have expiration times.
    """
    value = models.CharField(max_length=24, primary_key=True)
    expiration = models.DateTimeField()

    def __str__(self):
        return self.value


class UserManager(BaseUserManager):
    """
    Manager for the custom User model.
    
    This manager provides methods for creating users either with Ethereum
    addresses or with traditional username/email/password credentials.
    """
    def create_user_address(self, address):
        """
        Create and save a User with the given Ethereum address.
        
        Args:
            address: The Ethereum wallet address
            
        Returns:
            User: The created user instance
            
        Raises:
            ValueError: If no address is provided
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
        Create and save a User with traditional credentials.
        
        Args:
            username: The username for the new user
            email: The email address for the new user
            password: The password for the new user
            
        Returns:
            User: The created user instance
            
        Raises:
            ValueError: If any of the required fields are missing
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
        Create and save a superuser.
        
        Args:
            username: The username for the superuser
            password: The password for the superuser
            
        Returns:
            User: The created superuser instance
        """
        u = self.create_user_username_email_password(username, "matt.ritch.33@gmail.com", password)
        u.is_admin = True
        u.is_staff = True
        u.save(using=self._db)
        return u


class User(AbstractBaseUser):
    """
    Custom User model supporting both Ethereum wallet and traditional authentication.
    
    This model extends AbstractBaseUser to support authentication via Ethereum
    wallet addresses as well as traditional username/password authentication.
    """
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
        """
        Check if the user has a specific permission.
        
        Admin users have all permissions.
        
        Args:
            perm: The permission to check
            obj: Optional object to check against
            
        Returns:
            bool: True if the user has the permission
        """
        return self.is_admin

    def has_module_perms(self, app_label):
        """
        Check if the user has permissions to view the app with the given label.
        
        Admin users have access to all modules.
        
        Args:
            app_label: The label of the app to check
            
        Returns:
            bool: True if the user has permission to access the module
        """
        return self.is_admin

    def __str__(self):
        """
        Return a string representation of the user.
        
        Returns:
            str: The username, wallet address, or "User" as fallback
        """
        return self.username or self.wallet or "User"
