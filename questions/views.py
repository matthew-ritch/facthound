from rest_framework import permissions, viewsets
from models import Thread, Post, Question, Answer, Tag
from serializers import ThreadSerializer, PostSerializer, QuestionSerializer, AnswerSerializer, TagSerializer

class ThreadViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Thread objects to be viewed or edited.
    """
    queryset = Thread.objects.all().order_by('-dt')
    serializer_class = ThreadSerializer
    permission_classes = [permissions.IsAuthenticated]


class PostViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Post objects to be viewed or edited.
    """
    queryset = Post.objects.all().order_by('-dt')
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]


class QuestionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Question objects to be viewed or edited.
    """
    queryset = Question.objects.all().order_by('-post__dt')
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAuthenticated]


class AnswerViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Answer objects to be viewed or edited.
    """
    queryset = Answer.objects.all().order_by('-post__dt')
    serializer_class = AnswerSerializer
    permission_classes = [permissions.IsAuthenticated]
    

class TagViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Tag objects to be viewed or edited.
    """
    queryset = Tag.objects.all().order_by('name')
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticated]
    