from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView, LoginView, RefreshTokenView, get_user_profile,
    ClassViewSet, StudentViewSet, CategoryViewSet, VocabularyViewSet,
    get_random_test_question, submit_test_answer,
    get_student_results, clear_student_results
)

# Create router for viewsets
router = DefaultRouter()
router.register(r'classes', ClassViewSet, basename='class')
router.register(r'students', StudentViewSet, basename='student')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'vocabularies', VocabularyViewSet, basename='vocabulary')

urlpatterns = [
    # Authentication endpoints
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/refresh/', RefreshTokenView.as_view(), name='token_refresh'),
    path('auth/me/', get_user_profile, name='user_profile'),
    
    # Test endpoints
    path('test/<int:student_id>/random/', get_random_test_question, name='test_random'),
    path('test/<int:student_id>/answer/', submit_test_answer, name='test_answer'),
    
    # Results endpoints
    path('results/<int:student_id>/', get_student_results, name='student_results'),
    path('results/<int:student_id>/clear/', clear_student_results, name='clear_results'),
    
    # Router URLs (classes, students, vocabularies)
    path('', include(router.urls)),
]
