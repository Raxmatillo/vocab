from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, Class, Student, Vocabulary, Result, Category


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for teacher registration.
    Validates and creates new teacher accounts.
    """
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'password', 'password2', 'is_teacher']
        extra_kwargs = {
            'is_teacher': {'read_only': True}
        }
    
    def validate(self, attrs):
        """Validate that both passwords match."""
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                "password": "Password fields didn't match."
            })
        return attrs
    
    def create(self, validated_data):
        """Create new teacher user."""
        validated_data.pop('password2')
        user = User.objects.create_user(
            username=validated_data['username'],
            full_name=validated_data['full_name'],
            password=validated_data['password'],
            is_teacher=True
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile information.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'is_teacher', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class StudentSerializer(serializers.ModelSerializer):
    """
    Serializer for student CRUD operations.
    Includes computed fields for test statistics.
    """
    class_name = serializers.CharField(source='class_room.name', read_only=True)
    total_tests = serializers.IntegerField(read_only=True)
    correct_answers = serializers.IntegerField(read_only=True)
    incorrect_answers = serializers.IntegerField(read_only=True)
    accuracy_percentage = serializers.FloatField(read_only=True)
    
    class Meta:
        model = Student
        fields = [
            'id', 'full_name', 'class_room', 'class_name', 
            'total_tests', 'correct_answers', 'incorrect_answers', 
            'accuracy_percentage', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate_class_room(self, value):
        """Ensure teacher can only add students to their own classes."""
        request = self.context.get('request')
        if request and value.teacher != request.user:
            raise serializers.ValidationError(
                "You can only add students to your own classes."
            )
        return value


class ClassSerializer(serializers.ModelSerializer):
    """
    Serializer for class CRUD operations.
    Includes nested student information.
    """
    students = StudentSerializer(many=True, read_only=True)
    student_count = serializers.IntegerField(read_only=True)
    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True)
    
    class Meta:
        model = Class
        fields = [
            'id', 'name', 'teacher', 'teacher_name', 
            'students', 'student_count', 'created_at'
        ]
        read_only_fields = ['id', 'teacher', 'created_at']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'teacher']
        read_only_fields = ['id', 'teacher']

    def create(self, validated_data):
        # Teacherni avtomatik qo‘shish
        validated_data['teacher'] = self.context['request'].user
        return super().create(validated_data)


class VocabularySerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Vocabulary
        fields = [
            'id', 'category', 'category_name', 'word', 'image', 'image_url',
            'teacher', 'teacher_name', 'created_at'
        ]
        read_only_fields = ['id', 'teacher', 'created_at']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None



class TestQuestionSerializer(serializers.Serializer):
    """
    Serializer for test question with multiple choice options.
    Returns random vocabulary image with 3 options.
    """
    vocab_id = serializers.IntegerField()
    word = serializers.CharField()
    image_url = serializers.CharField()
    options = serializers.ListField(child=serializers.DictField())
    
    class Meta:
        fields = ['vocab_id', 'word', 'image_url', 'options']


class TestAnswerSerializer(serializers.Serializer):
    """
    Serializer for submitting test answers.
    Records whether student answered correctly.
    """
    vocab_id = serializers.IntegerField(required=True)
    selected_option_id = serializers.IntegerField(required=True)
    
    class Meta:
        fields = ['vocab_id', 'selected_option_id']
    
    def validate_vocab_id(self, value):
        """Ensure vocabulary exists."""
        if not Vocabulary.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid vocabulary ID.")
        return value


class ResultSerializer(serializers.ModelSerializer):
    """
    Serializer for viewing student test results.
    """
    vocab_word = serializers.CharField(source='vocab.word', read_only=True)
    vocab_category = serializers.CharField(source='vocab.category.name', read_only=True)
    vocab_image_url = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = Result
        fields = [
            'id', 'vocab_word', 'vocab_category', 'vocab_image_url',
            'correct', 'status', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']
    
    def get_vocab_image_url(self, obj):
        """Return full URL for vocabulary image."""
        request = self.context.get('request')
        if obj.vocab.image and request:
            return request.build_absolute_uri(obj.vocab.image.url)
        return None
    
    def get_status(self, obj):
        """Return + for correct, - for incorrect."""
        return '+' if obj.correct else '-'


class StudentResultSummarySerializer(serializers.Serializer):
    """
    Serializer for student result summary with statistics.
    """
    student_id = serializers.IntegerField()
    student_name = serializers.CharField()
    total_tests = serializers.IntegerField()
    correct_answers = serializers.IntegerField()
    incorrect_answers = serializers.IntegerField()
    accuracy_percentage = serializers.FloatField()
    results = ResultSerializer(many=True)
    
    class Meta:
        fields = [
            'student_id', 'student_name', 'total_tests', 
            'correct_answers', 'incorrect_answers', 
            'accuracy_percentage', 'results'
        ]
