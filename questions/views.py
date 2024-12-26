from django.http import HttpResponse
from rest_framework import viewsets
from .serializers import MyModelSerializer

def index(request):
    return HttpResponse("Hello, world. You're at the questions index.")