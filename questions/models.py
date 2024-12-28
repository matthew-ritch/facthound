from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser

from web3 import Web3


### siwe


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

    is_admin = models.BooleanField(default=False)
    objects = WalletManager()


### for this app


class Thread(models.Model):
    topic = models.CharField(max_length=1000)
    dt = models.DateTimeField()
    n_replies = models.IntegerField(default=0)

    def __str__(self):
        return self.topic


class Post(models.Model):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE)
    thread_index = models.IntegerField(default=0)
    text = models.TextField()
    dt = models.DateTimeField()

    def __str__(self):
        return f"{self.thread.topic}: reply {self.thread_index}"


class Question(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    questionHash = models.BinaryField()
    questionAddress = models.CharField(
        verbose_name="FactHound Question Address",
        max_length=42,
        unique=True,
        validators=[
            RegexValidator(regex=r"^0x[a-fA-F0-9]{40}$"),
            validate_ethereum_address,
        ],
    )
    asker = models.ForeignKey(Wallet)
    bounty = models.IntegerField()  # units of wei
    status = models.CharField(
        choices=[
            ("OP", "Open"),
            ("AS", "Answer Selected"),
            ("RS", "Resolved"),
            ("CA", "Canceled"),
        ],
        max_length=100,
    )

    def __str__(self):
        return f"{self.post.thread.topic}: {self.asker}'s question {self.questionHash}"


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    answerHash = models.BinaryField()
    answerer = models.ForeignKey(Wallet)
    status = models.CharField(
        choices=[
            ("OP", "Open"),
            ("SE", "Selected"),
            ("CE", "Certified"),
            ("PO", "Paid Out"),
        ],
        max_length=100,
    )

    def __str__(self):
        return f"{self.post.thread.topic}: {self.answerer}'s answer {self.answerHash}"


class Tag(models.Model):
    name = models.CharField(max_length=100)
    thread = models.ManyToManyField(Thread)

    def __str__(self):
        return self.name
