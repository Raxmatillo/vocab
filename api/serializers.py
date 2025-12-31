from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, ClassRoom, Student, Vocabulary, Result, Category


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'password', 'password2', 'is_teacher']
        extra_kwargs = {'is_teacher': {'read_only': True}}

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Parollar mos kelmadi."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(
            username=validated_data['username'],
            full_name=validated_data['full_name'],
            password=validated_data['password'],
            is_teacher=True
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'is_teacher', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class StudentSerializer(serializers.ModelSerializer):
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
        read_only_fields = ['id', 'created_at', 'total_tests', 'correct_answers', 'incorrect_answers', 'accuracy_percentage']

    def validate_class_room(self, value):
        request = self.context.get('request')
        if request and value.teacher != request.user:
            raise serializers.ValidationError("Faqat o‘z sinflaringizga o‘quvchi qo‘shishingiz mumkin.")
        return value


class ClassSerializer(serializers.ModelSerializer):
    students = StudentSerializer(many=True, read_only=True)
    student_count = serializers.IntegerField(read_only=True)
    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True)

    class Meta:
        model = ClassRoom
        fields = ['id', 'name', 'teacher', 'teacher_name', 'students', 'student_count', 'created_at']
        read_only_fields = ['id', 'teacher', 'created_at', 'student_count']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'teacher']
        read_only_fields = ['id', 'teacher']

    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return super().create(validated_data)


class VocabularySerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Vocabulary
        fields = ['id', 'category', 'category_name', 'word', 'image', 'image_url', 'teacher', 'teacher_name', 'created_at']
        read_only_fields = ['id', 'teacher', 'created_at']

    def get_image_url(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(obj.image.url) if obj.image and request else None

class BulkVocabularySerializer(serializers.Serializer):
    images = serializers.ListField(
        child=serializers.ImageField(),
        allow_empty=False
    )
    words = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False
    )
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all()
    )

    def validate(self, data):
        if len(data['images']) != len(data['words']):
            raise serializers.ValidationError(
                "Images va words soni bir xil bo'lishi kerak."
            )
        return data

    def create(self, validated_data):
        teacher = self.context['request'].user
        images = validated_data['images']
        words = validated_data['words']
        category = validated_data['category']

        created_vocabularies = []
        for img, word in zip(images, words):
            vocab = Vocabulary.objects.create(
                teacher=teacher,
                category=category,
                word=word,
                image=img
            )
            created_vocabularies.append(vocab)
        return created_vocabularies




class TestQuestionSerializer(serializers.Serializer):
    vocab_id = serializers.IntegerField()
    word = serializers.CharField()
    image_url = serializers.CharField()
    options = serializers.ListField(child=serializers.DictField())


class TestAnswerSerializer(serializers.Serializer):
    vocab_id = serializers.IntegerField(required=True)
    selected_option_id = serializers.IntegerField(required=True)

    def validate_vocab_id(self, value):
        if not Vocabulary.objects.filter(id=value).exists():
            raise serializers.ValidationError("Noto‘g‘ri so‘z ID.")
        return value


class ResultSerializer(serializers.ModelSerializer):
    vocab_word = serializers.CharField(source='vocab.word', read_only=True)
    vocab_category = serializers.CharField(source='vocab.category.name', read_only=True)
    vocab_image_url = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Result
        fields = ['id', 'vocab_word', 'vocab_category', 'vocab_image_url', 'correct', 'status', 'timestamp']
        read_only_fields = ['id', 'timestamp']

    def get_vocab_image_url(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(obj.vocab.image.url) if obj.vocab.image and request else None

    def get_status(self, obj):
        return '+' if obj.correct else '-'

class StudentTestSession(serializers.Serializer):
    pass


class StudentResultSummarySerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    student_name = serializers.CharField()
    category_name = serializers.CharField(allow_null=True, default=None)  # yangi
    total_tests = serializers.IntegerField()
    correct_answers = serializers.IntegerField()
    incorrect_answers = serializers.IntegerField()
    accuracy_percentage = serializers.FloatField()
    results = ResultSerializer(many=True)

    # Agar bitta kategoriya bo‘yicha kerak bo‘lsa, quyidagini qo‘shing:
    # category_name = serializers.CharField()  # yoki SerializerMethodField bilan