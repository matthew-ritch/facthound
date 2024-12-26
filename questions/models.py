from django.db import models
from django.core.validators import RegexValidator


class Thread(models.Model):
    topic = models.CharField(max_length=1000)
    dt = models.DateTimeField()


class Post(models.Model):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE)
    text = models.TextField()
    dt = models.DateTimeField()


class Question(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    questionHash = models.BinaryField()
    answerer = models.CharField(
        verbose_name="Wallet Address",
        max_length=42,
        unique=True,
        validators=[RegexValidator(regex=r"^0x[a-fA-F0-9]{40}$")],
    )
    status = models.CharField(
        choices=[
            ("OP", "Open"),
            ("AS", "Answer Selected"),
            ("RS", "Resolved"),
            ("CA", "Canceled"),
        ],
        max_length=100,
    )


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    answerHash = models.BinaryField()
    questionAddress = models.CharField(
        verbose_name="FactHound Question Address",
        max_length=42,
        unique=True,
        validators=[RegexValidator(regex=r"^0x[a-fA-F0-9]{40}$")],
    )
    asker = models.CharField(
        verbose_name="Wallet Address",
        max_length=42,
        unique=True,
        validators=[RegexValidator(regex=r"^0x[a-fA-F0-9]{40}$")],
    )
    bounty = models.IntegerField()  # units of wei
    status = models.CharField(
        choices=[
            ("CH", "Chosen"),
            ("CE", "Certified"),
            ("PO", "Paid Out"),
        ],
        max_length=100,
    )


class Tag(models.Model):
    name = models.CharField(max_length=100)
