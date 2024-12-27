from rest_framework import serializers
from models import Thread, Post, Question, Answer, Tag

class ThreadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Thread
        fields = '__all__'

    def create(self, validated_data):
        # Add custom logic here, e.g., setting default values
        return Thread.objects.create(**validated_data)
    
class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = '__all__'

    def create(self, validated_data):
        # Add custom logic here, e.g., setting default values
        return Post.objects.create(**validated_data)
    
class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'

    def create(self, validated_data):
        # Add custom logic here, e.g., setting default values
        return Question.objects.create(**validated_data)
    
class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = '__all__'

    def create(self, validated_data):
        # Add custom logic here, e.g., setting default values
        return Answer.objects.create(**validated_data)
    
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'

    def create(self, validated_data):
        # Add custom logic here, e.g., setting default values
        return Tag.objects.create(**validated_data)
    