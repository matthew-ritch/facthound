from django.test import TestCase
from django.test import RequestFactory

from web3 import Web3
import json, datetime, pytz, logging

from siweauth.views import TokenObtainPairView
from siweauth.models import User

from questions import views
from questions.models import Thread, Post, Question, Answer, Tag
from questions.serializers import (
    ThreadSerializer,
    PostSerializer,
    QuestionSerializer,
    AnswerSerializer,
    TagSerializer,
)

logging.disable(logging.CRITICAL)


class TestPosts(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user_username_email_password(
            "testuser", "test@test.com", "testpass"
        )
        request = self.factory.post(
            "/api/token/",
            {
                "username": "testuser",
                "password": "testpass",
            },
        )
        response = TokenObtainPairView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.token = json.loads(response.render().content)["access"]
        self.user2 = User.objects.create_user_username_email_password(
            "testuser2", "test2@test.com", "testpass2"
        )
        request = self.factory.post(
            "/api/token/",
            {
                "username": "testuser2",
                "password": "testpass2",
            },
        )
        response = TokenObtainPairView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.token2 = json.loads(response.render().content)["access"]
        self.thread_dict = {
            "topic": "sometopic",
            "text": "I am wondering what to do about this topic.",
            "tags": ["a", "b", "c"],
        }

    def test_start_thread(self):
        request = self.factory.post(
            "/api/post/",
            self.thread_dict,
        )
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token}"
        response = views.post(request)
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        # make sure thread was created
        thread = Thread.objects.get(topic=self.thread_dict["topic"])
        self.assertEqual(thread.pk, content["thread"])
        # make sure post was created
        post = Post.objects.get(text=self.thread_dict["text"], thread=thread)
        postpk = Post.objects.get(pk=content["post"])
        self.assertEqual(post, postpk)
        self.assertEqual(post.text, self.thread_dict["text"])
        self.assertEqual(self.user, post.poster)
        # thread should have 1 post. test associations
        self.assertEqual(thread.post_set.all().count(), 1)
        self.assertEqual(thread, post.thread)
        self.assertEqual(thread.dt, post.dt)
        # thread should have the right tags
        for t in self.thread_dict["tags"]:
            qs = Tag.objects.filter(thread=thread, name=t)
            self.assertEqual(qs.count(), 1)

    def test_reply_to_thread(self):
        # make thread
        request = self.factory.post(
            "/api/post/",
            self.thread_dict,
        )
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token}"
        response = views.post(request)
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        thread = Thread.objects.get(pk=content["thread"])
        # post again
        post_dict = {"thread": thread.pk, "text": "follow up post"}
        request = self.factory.post(
            "/api/post/",
            post_dict,
        )
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token2}"
        response = views.post(request)
        content = json.loads(response.content)
        # make sure post was created
        post = Post.objects.get(text=post_dict["text"], thread=thread)
        postpk = Post.objects.get(pk=content["post"])
        self.assertEqual(post, postpk)
        self.assertEqual(post.text, post_dict["text"])
        self.assertEqual(self.user2, post.poster)
        # thread should have 2 posts. test associations
        self.assertEqual(thread.post_set.all().count(), 2)
        self.assertEqual(thread, post.thread)

    def test_post_no_thread_fails(self):
        post_dict = {"text": "follow up post"}
        request = self.factory.post(
            "/api/post/",
            post_dict,
        )
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token2}"
        response = views.post(request)
        content = json.loads(response.content)
        self.assertNotIn("post", content.keys())
        self.assertEqual(
            content["message"],
            "One of thread or topic must be specified. You cannot specify both.",
        )

    def test_thread_no_text_fails(self):
        post_dict = {"topic": "topic"}
        request = self.factory.post(
            "/api/post/",
            post_dict,
        )
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token2}"
        response = views.post(request)
        content = json.loads(response.content)
        self.assertNotIn("post", content.keys())
        self.assertEqual(content["message"], "Your post needs text.")

    def test_reply_to_thread_no_text_fails(self):
        # make thread
        request = self.factory.post(
            "/api/post/",
            self.thread_dict,
        )
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token}"
        response = views.post(request)
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        thread = Thread.objects.get(pk=content["thread"])
        # post again
        post_dict = {"thread": thread.pk}
        request = self.factory.post(
            "/api/post/",
            post_dict,
        )
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token2}"
        response = views.post(request)
        content = json.loads(response.content)
        self.assertNotIn("post", content.keys())
        self.assertEqual(content["message"], "Your post needs text.")


class TestQuestions(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user_username_email_password(
            "testuser", "test@test.com", "testpass"
        )
        request = self.factory.post(
            "/api/token/",
            {
                "username": "testuser",
                "password": "testpass",
            },
        )
        response = TokenObtainPairView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.token = json.loads(response.render().content)["access"]
        self.user2 = User.objects.create_user_username_email_password(
            "testuser2", "test2@test.com", "testpass2"
        )
        request = self.factory.post(
            "/api/token/",
            {
                "username": "testuser2",
                "password": "testpass2",
            },
        )
        response = TokenObtainPairView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.token2 = json.loads(response.render().content)["access"]
        self.thread_dict = {
            "topic": "sometopic",
            "text": "I am wondering what to do about this topic.",
            "tags": ["a", "b", "c"],
        }

    def test_start_thread(self):
        request = self.factory.post(
            "/api/question/",
            self.thread_dict,
        )
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token}"
        response = views.question(request)
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        # make sure thread was created
        thread = Thread.objects.get(topic=self.thread_dict["topic"])
        self.assertEqual(thread.pk, content["thread"])
        # make sure post was created
        post = Post.objects.get(text=self.thread_dict["text"], thread=thread)
        postpk = Post.objects.get(pk=content["post"])
        self.assertEqual(post, postpk)
        self.assertEqual(post.text, self.thread_dict["text"])
        self.assertEqual(self.user, post.poster)
        # make sure question was created
        question = Question.objects.get(
            post__text=self.thread_dict["text"], post__thread=thread
        )
        questionpk = Question.objects.get(pk=content["question"])
        self.assertEqual(question, questionpk)
        self.assertEqual(question.post.text, self.thread_dict["text"])
        self.assertEqual(self.user, question.asker)
        # make sure question and post are identified together
        self.assertEqual(question.post, post)
        # thread should have 1 post. test associations
        self.assertEqual(thread.post_set.all().count(), 1)
        self.assertEqual(thread, post.thread)
        self.assertEqual(thread.dt, post.dt)
        # thread should have the right tags
        for t in self.thread_dict["tags"]:
            qs = Tag.objects.filter(thread=thread, name=t)
            self.assertEqual(qs.count(), 1)

    def test_reply_to_thread(self):
        # make thread
        request = self.factory.post(
            "/api/post/",
            self.thread_dict,
        )
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token}"
        response = views.post(request)
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        thread = Thread.objects.get(pk=content["thread"])
        # post again
        post_dict = {"thread": thread.pk, "text": "follow up post"}
        request = self.factory.post(
            "/api/post/",
            post_dict,
        )
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token2}"
        response = views.question(request)
        content = json.loads(response.content)
        # make sure post was created
        post = Post.objects.get(text=post_dict["text"], thread=thread)
        postpk = Post.objects.get(pk=content["post"])
        self.assertEqual(post, postpk)
        self.assertEqual(post.text, post_dict["text"])
        self.assertEqual(self.user2, post.poster)
        # make sure question was created
        question = Question.objects.get(
            post__text=post_dict["text"], post__thread=thread
        )
        questionpk = Question.objects.get(pk=content["question"])
        self.assertEqual(question, questionpk)
        self.assertEqual(question.post.text, post_dict["text"])
        self.assertEqual(self.user2, question.asker)
        # make sure question and post are identified together
        self.assertEqual(question.post, post)
        # thread should have 2 post. test associations
        self.assertEqual(thread.post_set.all().count(), 2)
        self.assertEqual(thread, post.thread)

    def test_question_no_thread_fails(self):
        post_dict = {"text": "follow up post"}
        request = self.factory.post(
            "/api/post/",
            post_dict,
        )
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token2}"
        response = views.question(request)
        content = json.loads(response.content)
        self.assertNotIn("post", content.keys())
        self.assertEqual(
            content["message"],
            "One of thread or topic must be specified. You cannot specify both.",
        )

    def test_thread_no_text_fails(self):
        post_dict = {"topic": "topic"}
        request = self.factory.post(
            "/api/post/",
            post_dict,
        )
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token2}"
        response = views.question(request)
        content = json.loads(response.content)
        self.assertNotIn("post", content.keys())
        self.assertEqual(content["message"], "Your post needs text.")

    def test_reply_to_thread_no_text_fails(self):
        # make thread
        request = self.factory.post(
            "/api/post/",
            self.thread_dict,
        )
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token}"
        response = views.post(request)
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        thread = Thread.objects.get(pk=content["thread"])
        # post again
        post_dict = {"thread": thread.pk}
        request = self.factory.post(
            "/api/post/",
            post_dict,
        )
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token2}"
        response = views.question(request)
        content = json.loads(response.content)
        self.assertNotIn("post", content.keys())
        self.assertEqual(content["message"], "Your post needs text.")


class TestAnswers(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user_username_email_password(
            "testuser", "test@test.com", "testpass"
        )
        request = self.factory.post(
            "/api/token/",
            {
                "username": "testuser",
                "password": "testpass",
            },
        )
        response = TokenObtainPairView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.token = json.loads(response.render().content)["access"]
        self.user2 = User.objects.create_user_username_email_password(
            "testuser2", "test2@test.com", "testpass2"
        )
        request = self.factory.post(
            "/api/token/",
            {
                "username": "testuser2",
                "password": "testpass2",
            },
        )
        response = TokenObtainPairView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.token2 = json.loads(response.render().content)["access"]
        self.thread_dict = {
            "topic": "sometopic",
            "text": "I am wondering what to do about this topic.",
            "tags": ["a", "b", "c"],
        }

    def test_reply_to_thread(self):
        # make thread
        request = self.factory.post(
            "/api/post/",
            self.thread_dict,
        )
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token}"
        response = views.question(request)
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        thread = Thread.objects.get(pk=content["thread"])
        question = Question.objects.get(pk=content["question"])
        # post again
        post_dict = {
            "thread": thread.pk,
            "text": "follow up post",
            "question": question.pk,
        }
        request = self.factory.post(
            "/api/post/",
            post_dict,
        )
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token2}"
        response = views.answer(request)
        content = json.loads(response.content)
        # make sure post was created
        post = Post.objects.get(text=post_dict["text"], thread=post_dict["thread"])
        postpk = Post.objects.get(pk=content["post"])
        self.assertEqual(post, postpk)
        self.assertEqual(post.text, post_dict["text"])
        self.assertEqual(self.user2, post.poster)
        # make sure answer was created
        answer = Answer.objects.get(post__text=post_dict["text"], post__thread=thread)
        answerpk = Answer.objects.get(pk=content["answer"])
        self.assertEqual(answer, answerpk)
        self.assertEqual(answer.post.text, post_dict["text"])
        self.assertEqual(self.user2, answer.answerer)
        # make sure answer and post are identified together
        self.assertEqual(answer.post, post)
        # make sure answer answers the right question
        self.assertEqual(answer.question, question)
        # thread should have 2 post. test associations
        self.assertEqual(thread.post_set.all().count(), 2)
        self.assertEqual(thread, post.thread)

    def test_no_text_fails(self):
        post_dict = {"thread": 0, "question": 0}
        request = self.factory.post(
            "/api/post/",
            post_dict,
        )
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token2}"
        response = views.answer(request)
        content = json.loads(response.content)
        self.assertNotIn("answer", content.keys())
        self.assertEqual(content["message"], "Your post needs text.")

    def test_no_thread_fails(self):
        post_dict = {"text": "A", "question": 0}
        request = self.factory.post(
            "/api/post/",
            post_dict,
        )
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token2}"
        response = views.answer(request)
        content = json.loads(response.content)
        self.assertNotIn("answer", content.keys())
        self.assertEqual(content["message"], "Your post needs a thread.")
        # post_dict = {"text": 'A', "thread":0, "question":0}

    def test_no_question_fails(self):
        post_dict = {
            "text": "A",
            "thread": 0,
        }
        request = self.factory.post(
            "/api/post/",
            post_dict,
        )
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token2}"
        response = views.answer(request)
        content = json.loads(response.content)
        self.assertNotIn("answer", content.keys())
        self.assertEqual(content["message"], "Your answer needs a question.")

    def test_question_dne_fails(self):
        post_dict = {"text": "A", "thread": 0, "question": 0}
        request = self.factory.post(
            "/api/post/",
            post_dict,
        )
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token2}"
        response = views.answer(request)
        content = json.loads(response.content)
        self.assertNotIn("answer", content.keys())
        self.assertEqual(content["message"], "No question with that id exists.")

    def test_question_in_wrong_thread_fails(self):
        t1 = Thread.objects.create(topic="A", dt=datetime.datetime.now(tz=pytz.UTC))
        t2 = Thread.objects.create(topic="B", dt=datetime.datetime.now(tz=pytz.UTC))
        qp = Post.objects.create(
            thread=t1,
            text="AA",
            dt=datetime.datetime.now(tz=pytz.UTC),
            poster=self.user,
        )
        q = Question.objects.create(post=qp, asker=self.user, status="OP")
        post_dict = {"text": "B", "thread": t2.pk, "question": q.pk}
        request = self.factory.post(
            "/api/post/",
            post_dict,
        )
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.token2}"
        response = views.answer(request)
        content = json.loads(response.content)
        self.assertNotIn("answer", content.keys())
        self.assertEqual(
            content["message"],
            "Answers must be posted in the same thread as the question they answer.",
        )
