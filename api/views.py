from rest_framework import viewsets, status, generics
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.shortcuts import get_object_or_404
from django.db.models import Q
import random
from rest_framework.generics import GenericAPIView
from drf_spectacular.utils import extend_schema


from .models import User, ClassRoom, Student, Vocabulary, Result, Category, TestSession
from .serializers import (
    UserRegistrationSerializer, UserSerializer, ClassSerializer,
    StudentSerializer, CategorySerializer, VocabularySerializer, BulkVocabularySerializer,
    TestQuestionSerializer, TestAnswerSerializer, ResultSerializer,
    StudentResultSummarySerializer
)
from .permissions import IsTeacher, IsOwnerOrReadOnly


# =============================================================================
# Authentication
# =============================================================================

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]


class RefreshTokenView(TokenRefreshView):
    permission_classes = [AllowAny]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


# =============================================================================
# ClassRoom, Student, Category, Vocabulary ViewSets
# =============================================================================

class ClassRoomViewSet(viewsets.ModelViewSet):
    serializer_class = ClassSerializer
    permission_classes = [IsAuthenticated, IsTeacher]

    def get_queryset(self):
        category_id = self.request.query_params.get('category_id')
        print(f"{category_id=}")
        return ClassRoom.objects.filter(teacher=self.request.user).prefetch_related('students')

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)


class StudentViewSet(viewsets.ModelViewSet):
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated, IsTeacher]

    def get_queryset(self):
        return Student.objects.filter(class_room__teacher=self.request.user).select_related('class_room')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsTeacher]

    def get_queryset(self):
        return Category.objects.filter(teacher=self.request.user)

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)


class VocabularyViewSet(viewsets.ModelViewSet):
    serializer_class = VocabularySerializer
    permission_classes = [IsAuthenticated, IsTeacher]

    def get_queryset(self):
        queryset = Vocabulary.objects.filter(teacher=self.request.user).select_related('category')
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)

# =============================================================================
# Teacher Views
# =============================================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_dashboard_results(request):
    class_id = request.query_params.get('class_id')
    category_id = request.query_params.get('category_id')

    # Faqat ushbu o'qituvchiga tegishli sessiyalarni olamiz
    sessions = TestSession.objects.filter(
        student__class_room__teacher=request.user
    ).select_related('student', 'category')

    if class_id:
        sessions = sessions.filter(student__class_room_id=class_id)
    if category_id:
        sessions = sessions.filter(category_id=category_id)

    # Natijalarni qaytarish
    data = []
    for session in sessions:
        data.append({
            "student_name": session.student.full_name,
            "category": session.category.name,
            "score": f"{session.correct_answers}/{session.total_questions}",
            "percentage": session.percentage,
            "date": session.finished_at.strftime("%Y-%m-%d %H:%M")
        })
    
    return Response(data)

# =============================================================================
# Test Views
# =============================================================================
@action(detail=True, methods=['get'])
def get_options(self, request, pk=None):
    current_word = self.get_object()
    # Xuddi shu kategoriyadan boshqa 2 ta tasodifiy so'z olish
    wrong_options = Vocabulary.objects.filter(
        category=current_word.category
    ).exclude(id=current_word.id).order_by('?')[:2]
    
    # To'g'ri javob bilan birlashtirish va aralashtirish (shuffle)
    options = [current_word.word] + [w.word for w in wrong_options]
    random.shuffle(options)
    
    return Response({"options": options})

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsTeacher])
def get_random_test_question(request, student_id):
    student = get_object_or_404(
        Student, id=student_id, class_room__teacher=request.user
    )
    
    # print('category_id', category_id)

    category_id = request.query_params.get('category')
    
    if not category_id:
        return Response({"error": "Kategoriya ID majburiy"}, status=400)

    # Shu kategoriyadagi barcha so‘zlar
    vocabularies = Vocabulary.objects.filter(
        teacher=request.user,
        category_id=category_id
    )
    

    if vocabularies.count() < 3:
        return Response({"error": "Test hali mavjud emas!"}, status=400)

    print('category_id', category_id)
    # Talabaning oldin javoblagan so‘zlari
    used_vocab_ids = Result.objects.filter(
        session__student=student,
        vocabulary__category_id=category_id
    ).values_list('vocabulary_id', flat=True)

    
    # Takrorlanmaslik uchun filter
    remaining_vocabularies = vocabularies.exclude(id__in=used_vocab_ids)

    if not remaining_vocabularies.exists():
        # Barcha so‘zlar ishlatilgan bo‘lsa, natija tayyor
        return Response({"finished":True, "message": "Barcha savollar tugadi!"})

    correct_vocab = random.choice(list(remaining_vocabularies))
    wrong_vocabs = vocabularies.exclude(id=correct_vocab.id)

    wrong_options = random.sample(list(wrong_vocabs), 2)
    all_options = [correct_vocab] + wrong_options
    random.shuffle(all_options)

    options = [{'id': v.id, 'word': v.word} for v in all_options]

    return Response({
        'finished':False,
        'vocab_id': correct_vocab.id,
        'word': correct_vocab.word,
        'image_url': request.build_absolute_uri(correct_vocab.image.url) if correct_vocab.image else None,
        'options': options
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsTeacher])
def bulk_create_vocabularies(request):
    serializer = BulkVocabularySerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)

    created_vocabularies = serializer.save()  # Serializer create() ishlaydi

    # JSON serializable qilish
    return Response({
        "created": len(created_vocabularies),
        "vocabularies": [
            {
                "id": v.id,
                "word": v.word,
                "image_url": request.build_absolute_uri(v.image.url) if v.image else None,
                "category": v.category.id
            }
            for v in created_vocabularies
        ]
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsTeacher])
def submit_test_answer(request, student_id):
    student = get_object_or_404(Student, id=student_id, class_room__teacher=request.user)
    
    serializer = TestAnswerSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    vocab_id = serializer.validated_data['vocab_id']
    selected_option_id = serializer.validated_data['selected_option_id']

    vocab = get_object_or_404(Vocabulary, id=vocab_id, teacher=request.user)
    
    # To'g'ri javobni tekshirish
    is_correct = (vocab.id == selected_option_id)

    # TestSession yaratish yoki olish (har bir test uchun)
    session, _ = TestSession.objects.get_or_create(
        student=student,
        category=vocab.category,
        defaults={'total_questions': 0, 'correct_answers': 0}
    )

    # Result yaratish
    result = Result.objects.create(
        session=session,
        vocabulary=vocab,
        is_correct=is_correct
    )

    # Session statistikasini yangilash
    session.total_questions += 1
    if is_correct:
        session.correct_answers += 1
    session.save()

    return Response({
        'correct': is_correct,
        'correct_word': vocab.word if is_correct else None,
        'result_id': result.id,
        'total_questions': session.total_questions,
        'correct_answers': session.correct_answers,
        'percentage': session.percentage
    }, status=201)


# =============================================================================
# Results Views
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsTeacher])
def get_student_results(request, student_id):
    student = get_object_or_404(Student, id=student_id, class_room__teacher=request.user)

    results = Result.objects.filter(student=student).select_related('vocab__category')

    summary_data = {
        'student_id': student.id,
        'student_name': student.full_name,
        'total_tests': student.total_tests,
        'correct_answers': student.correct_answers,
        'incorrect_answers': student.incorrect_answers,
        'accuracy_percentage': student.accuracy_percentage,
        'results': results  # ResultSerializer many=True bilan ishlaydi
    }

    serializer = StudentResultSummarySerializer(summary_data, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsTeacher])
def get_students_results(request, class_id):
    category_id = request.query_params.get('category')
    if not category_id:
        return Response({"error": "category param majburiy"}, status=400)

    # Class va teacher tekshiruvi
    class_room = get_object_or_404(ClassRoom, id=class_id, teacher=request.user)

    # Barcha studentlar
    students = class_room.students.all()

    # Shu category bo‘yicha TestSession natijalari
    sessions = TestSession.objects.filter(
        student__class_room=class_room,
        category_id=category_id
    ).select_related('student', 'category')

    # Map qilib studentga natijalarni biriktiramiz
    student_data = []
    for student in students:
        # Shu student uchun session bormi?
        session = next((s for s in sessions if s.student.id == student.id), None)
        student_data.append({
            "id": student.id,
            "full_name": student.full_name,
            "total_tests": session.total_questions if session else 0,
            "correct_answers": session.correct_answers if session else 0,
            "incorrect_answers": (session.total_questions - session.correct_answers) if session else 0,
            "accuracy_percentage": session.percentage if session else 0
        })

    return Response({
        "class": class_room.name,
        "teacher": request.user.full_name,
        "category_id": category_id,
        "students": student_data
    })



@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsTeacher])
def clear_student_results(request, student_id):
    student = get_object_or_404(Student, id=student_id, class_room__teacher=request.user)
    sessions = TestSession.objects.filter(student=student)
    sessions.delete()
    # deleted_count = Result.objects.filter(student=student).delete()[0]
    return Response({
        'message': f"Natija o‘chirildi.",
        'student_id': student.id
    })