from django.urls import path, include

from . import views

from rest_framework.routers import DefaultRouter

# register the ViewSets with a DefaultRouter
router = DefaultRouter()
router.register(r"threads", views.ThreadViewSet, basename="thread")
router.register(r"posts", views.PostViewSet, basename="post")
router.register(r"questions", views.QuestionViewSet, basename="question")
router.register(r"answers", views.AnswerViewSet, basename="answer")
router.register(r"tags", views.TagViewSet, basename="tag")

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path("", include(router.urls)),
    path("/api/post/", include(router.urls)),
    path('api/post/', views.post, name='post'),
    path('api/question/', views.question, name='question'),
    path('api/answer/', views.answer, name='answer'),
]
