from rest_framework import viewsets, status, generics
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.db.models import Q
from django.shortcuts import get_object_or_404
import random

from .models import User, Class, Student, Vocabulary, Result, Category
from .serializers import (
    UserRegistrationSerializer, UserSerializer, ClassSerializer,
    StudentSerializer, CategorySerializer, VocabularySerializer, TestQuestionSerializer,
    TestAnswerSerializer, ResultSerializer, StudentResultSummarySerializer
)
from .permissions import IsTeacher, IsOwnerOrReadOnly


# ============================================================================
# Authentication Views
# ============================================================================

class RegisterView(generics.CreateAPIView):
    """
    API endpoint for teacher registration.
    Public endpoint - no authentication required.
    """
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer


class LoginView(TokenObtainPairView):
    """
    API endpoint for JWT token authentication.
    Returns access and refresh tokens.
    """
    permission_classes = [AllowAny]


class RefreshTokenView(TokenRefreshView):
    """
    API endpoint for refreshing JWT access token.
    """
    permission_classes = [AllowAny]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    """
    Get current authenticated teacher profile.
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


# ============================================================================
# Class ViewSet
# ============================================================================

class ClassViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing classes.
    Teachers can create, read, update, and delete their own classes.
    """
    serializer_class = ClassSerializer
    permission_classes = [IsAuthenticated, IsTeacher]
    
    def get_queryset(self):
        """Return only classes belonging to the current teacher."""
        return Class.objects.filter(teacher=self.request.user).prefetch_related('students')
    
    def perform_create(self, serializer):
        """Automatically set the teacher to current user."""
        serializer.save(teacher=self.request.user)
    
    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        """
        Custom action to get all students in a specific class.
        GET /api/classes/{id}/students/
        """
        class_instance = self.get_object()
        students = class_instance.students.all()
        serializer = StudentSerializer(students, many=True)
        return Response(serializer.data)


# ============================================================================
# Student ViewSet
# ============================================================================

class StudentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing students.
    Teachers can add, update, and delete students in their classes.
    """
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated, IsTeacher]
    
    def get_queryset(self):
        """Return only students from classes belonging to current teacher."""
        return Student.objects.filter(
            class_room__teacher=self.request.user
        ).select_related('class_room')
    
    def get_serializer_context(self):
        """Pass request context to serializer for validation."""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


# ============================================================================
# Vocabulary ViewSet
# ============================================================================

class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsTeacher]

    def get_queryset(self):
        return Category.objects.filter(teacher=self.request.user)

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)


class VocabularyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing vocabularies.
    Teachers can create, read, update, and delete their vocabularies.
    Supports filtering by category.
    """
    serializer_class = VocabularySerializer
    permission_classes = [IsAuthenticated, IsTeacher]
    
    def get_queryset(self):
        """Return only vocabularies belonging to current teacher."""
        queryset = Vocabulary.objects.filter(teacher=self.request.user)
        
        # Filter by category if provided
        category_id = self.request.query_params.get('category', None)
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        
        return queryset
    
    def perform_create(self, serializer):
        """Automatically set the teacher to current user."""
        serializer.save(teacher=self.request.user)


# ============================================================================
# Test Views
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsTeacher])
def get_random_test_question(request, student_id):

    student = get_object_or_404(
        Student,
        id=student_id,
        class_room__teacher=request.user
    )

    vocabularies = Vocabulary.objects.filter(teacher=request.user)

    # ✅ CATEGORY FILTER
    category_id = request.query_params.get('category')
    if category_id:
        vocabularies = vocabularies.filter(category_id=category_id)

    # ✅ OLD QUESTIONS FILTER
    used_vocab_ids = Result.objects.filter(
        student=student,
        vocab__category_id=category_id
    ).values_list('vocab_id', flat=True)


    vocabularies = vocabularies.exclude(id__in=used_vocab_ids)

    # ❗ Agar hammasi tugab qolsa
    if not vocabularies.exists():
        return Response(
            {'message': 'All questions completed'},
            status=status.HTTP_204_NO_CONTENT
        )

    # 🎯 RANDOM QUESTION
    correct_vocab = random.choice(list(vocabularies))

    wrong_vocabs = vocabularies.exclude(id=correct_vocab.id)

    if wrong_vocabs.count() < 2:
        return Response(
            {'error': 'Not enough vocabularies for test.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    wrong_options = random.sample(list(wrong_vocabs), 2)

    all_options = [correct_vocab] + wrong_options
    random.shuffle(all_options)

    options = [
        {'id': v.id, 'word': v.word}
        for v in all_options
    ]

    return Response({
        'vocab_id': correct_vocab.id,
        'image_url': request.build_absolute_uri(correct_vocab.image.url),
        'options': options
    })



@api_view(['POST'])
@permission_classes([IsAuthenticated, IsTeacher])
def submit_test_answer(request, student_id):
    """
    Submit a test answer for a student.
    Records whether the answer was correct or incorrect.
    
    POST /api/test/<student_id>/answer/
    Body: {
        "vocab_id": 1,
        "selected_option_id": 2
    }
    """
    # Verify student belongs to teacher's class
    student = get_object_or_404(
        Student, 
        id=student_id, 
        class_room__teacher=request.user
    )
    
    serializer = TestAnswerSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    vocab_id = serializer.validated_data['vocab_id']
    selected_option_id = serializer.validated_data['selected_option_id']
    
    # Get vocabulary
    vocab = get_object_or_404(Vocabulary, id=vocab_id, teacher=request.user)
    
    # Check if answer is correct
    is_correct = (vocab_id == selected_option_id)
    
    # Save result
    result = Result.objects.create(
        student=student,
        vocab=vocab,
        correct=is_correct
    )
    
    return Response({
        'correct': is_correct,
        'correct_answer': vocab.word,
        'result_id': result.id
    }, status=status.HTTP_201_CREATED)


# ============================================================================
# Results Views
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsTeacher])
def get_student_results(request, student_id):
    """
    Get complete results summary for a student.
    Returns all test attempts with statistics.
    
    GET /api/results/<student_id>/
    """
    # Verify student belongs to teacher's class
    student = get_object_or_404(
        Student, 
        id=student_id, 
        class_room__teacher=request.user
    )
    
    # Get all results for student
    results = Result.objects.filter(student=student).select_related('vocab')
    
    # Build summary data
    summary_data = {
        'student_id': student.id,
        'student_name': student.full_name,
        'total_tests': student.total_tests,
        'correct_answers': student.correct_answers,
        'incorrect_answers': student.incorrect_answers,
        'accuracy_percentage': student.accuracy_percentage,
        'results': results
    }
    
    serializer = StudentResultSummarySerializer(
        summary_data, 
        context={'request': request}
    )
    return Response(serializer.data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsTeacher])
def clear_student_results(request, student_id):
    """
    Clear all test results for a student.
    Useful for resetting student progress.
    
    DELETE /api/results/<student_id>/clear/
    """
    # Verify student belongs to teacher's class
    student = get_object_or_404(
        Student, 
        id=student_id, 
        class_room__teacher=request.user
    )
    
    # Delete all results
    deleted_count = Result.objects.filter(student=student).delete()[0]
    
    return Response({
        'message': f'Successfully cleared {deleted_count} test results.',
        'student_id': student.id
    })

