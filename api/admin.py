from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, ClassRoom, Student, Vocabulary, Result, Category, TestSession


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model."""
    list_display = ['username', 'full_name', 'is_teacher', 'is_staff', 'date_joined']
    list_filter = ['is_teacher', 'is_staff', 'is_superuser']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('full_name', 'is_teacher')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('full_name', 'is_teacher')}),
    )


@admin.register(ClassRoom)
class ClassRoomAdmin(admin.ModelAdmin):
    """Admin interface for ClassRoom model."""
    list_display = ['name', 'teacher', 'student_count', 'created_at']
    list_filter = ['teacher', 'created_at']
    search_fields = ['name', 'teacher__full_name']
    readonly_fields = ['created_at']


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    """Admin interface for Student model."""
    list_display = ['full_name', 'class_room', 'total_tests', 'accuracy_percentage', 'created_at']
    list_filter = ['class_room', 'created_at']
    search_fields = ['full_name', 'class_room__name']
    readonly_fields = ['created_at']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin interface for Category model."""
    list_display = ['name', 'teacher']
    list_filter = ['teacher']
    search_fields = ['name', 'teacher__full_name']


@admin.register(Vocabulary)
class VocabularyAdmin(admin.ModelAdmin):
    """Admin interface for Vocabulary model."""
    list_display = ['word', 'category', 'teacher', 'created_at']
    list_filter = ['category', 'teacher', 'created_at']
    search_fields = ['word', 'category__name', 'teacher__full_name']
    readonly_fields = ['created_at']


@admin.register(TestSession)
class TestSessionAdmin(admin.ModelAdmin):
    """Admin interface for TestSession model."""
    list_display = ['student', 'category', 'total_questions', 'correct_answers', 'percentage', 'finished_at']
    list_filter = ['category', 'finished_at']
    search_fields = ['student__full_name', 'category__name']
    readonly_fields = ['created_at', 'finished_at']


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    """Admin interface for Result model."""
    list_display = ['get_student', 'vocabulary', 'is_correct', 'get_session', 'created_at']
    list_filter = ['is_correct', 'created_at']
    search_fields = ['session__student__full_name', 'vocabulary__word']
    readonly_fields = ['created_at']

    def get_student(self, obj):
        return obj.session.student.full_name
    get_student.short_description = 'Student'

    def get_session(self, obj):
        return f"{obj.session.category.name} ({obj.session.created_at.strftime('%Y-%m-%d')})"
    get_session.short_description = 'Test Session'
