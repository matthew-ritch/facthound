from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser

from web3 import Web3

from siweauth.models import validate_ethereum_address, Wallet


### siwe


class Thread(models.Model):
    topic = models.CharField(max_length=1000)
    dt = models.DateTimeField()

    def __str__(self):
        return self.topic


class Post(models.Model):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE)
    text = models.TextField()
    dt = models.DateTimeField()
    poster = models.ForeignKey(Wallet, on_delete=models.CASCADE)

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
    asker = models.ForeignKey(Wallet, on_delete=models.CASCADE)
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
    answerHash = models.BinaryField(unique=True)
    answerer = models.ForeignKey(Wallet, on_delete=models.CASCADE)
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
