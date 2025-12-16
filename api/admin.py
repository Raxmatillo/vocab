from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Class, Student, Vocabulary, Result, Category


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


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    """Admin interface for Class model."""
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
    list_display = ['name', 'teacher']
    list_filter = ['teacher']
    search_fields = ['name', 'teacher__full_name']

@admin.register(Vocabulary)
class VocabularyAdmin(admin.ModelAdmin):
    """Admin interface for Vocabulary model."""
    list_display = ['word', 'category', 'teacher', 'created_at']
    list_filter = ['category', 'teacher', 'created_at']
    search_fields = ['word', 'category', 'teacher__full_name']
    readonly_fields = ['created_at']


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    """Admin interface for Result model."""
    list_display = ['student', 'vocab', 'correct', 'timestamp']
    list_filter = ['correct', 'timestamp']
    search_fields = ['student__full_name', 'vocab__word']
    readonly_fields = ['timestamp']
