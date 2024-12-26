from rest_framework import serializers

class MyModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = None
        fields = '__all__'

    def create(self, validated_data):
        # Add custom logic here, e.g., setting default values
        return None