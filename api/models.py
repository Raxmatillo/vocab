from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator


class User(AbstractUser):
    """
    Custom User model for teachers.
    Extends Django's AbstractUser to add custom fields.
    """
    full_name = models.CharField(max_length=255)
    is_teacher = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.full_name} ({self.username})"


class Class(models.Model):
    """
    Represents a classroom managed by a teacher.
    Each class contains 20-30 students.
    """
    name = models.CharField(max_length=255)
    teacher = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='classes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Class'
        verbose_name_plural = 'Classes'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.teacher.full_name}"
    
    @property
    def student_count(self):
        """Return the number of students in this class."""
        return self.students.count()


class Student(models.Model):
    """
    Represents a student belonging to a class.
    Students take vocabulary tests and have results tracked.
    """
    full_name = models.CharField(max_length=255)
    class_room = models.ForeignKey(
        Class, 
        on_delete=models.CASCADE, 
        related_name='students'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Student'
        verbose_name_plural = 'Students'
        ordering = ['full_name']
    
    def __str__(self):
        return f"{self.full_name} - {self.class_room.name}"
    
    @property
    def total_tests(self):
        """Return total number of tests taken by student."""
        return self.results.count()
    
    @property
    def correct_answers(self):
        """Return number of correct answers."""
        return self.results.filter(correct=True).count()
    
    @property
    def incorrect_answers(self):
        """Return number of incorrect answers."""
        return self.results.filter(correct=False).count()
    
    @property
    def accuracy_percentage(self):
        """Calculate accuracy percentage."""
        total = self.total_tests
        if total == 0:
            return 0
        return round((self.correct_answers / total) * 100, 2)


class Category(models.Model):
    """
    Represents a vocabulary category, e.g., Fruits, Animals.
    Teachers can create categories for their vocabularies.
    """
    name = models.CharField(max_length=100)
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='categories'
    )

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        unique_together = ['name', 'teacher']  # har bir teacher uchun nom takrorlanmasligi
        ordering = ['name']

    def __str__(self):
        return self.name


class Vocabulary(models.Model):
    """
    Vocabulary word with category and image.
    Now category is a ForeignKey to Category.
    """
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='vocabularies'
    )
    word = models.CharField(max_length=255)
    image = models.ImageField(
        upload_to='vocabularies/%Y/%m/%d/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif', 'webp'])]
    )
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='vocabularies'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Vocabulary'
        verbose_name_plural = 'Vocabularies'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['teacher']),
        ]

    def __str__(self):
        return f"{self.word} ({self.category.name})"



class Result(models.Model):
    """
    Stores student test results.
    Tracks whether a student answered correctly for each vocabulary item.
    """
    student = models.ForeignKey(
        Student, 
        on_delete=models.CASCADE, 
        related_name='results',
        db_index=True
    )
    vocab = models.ForeignKey(
        Vocabulary, 
        on_delete=models.CASCADE, 
        related_name='results'
    )
    correct = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Result'
        verbose_name_plural = 'Results'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['student', 'timestamp']),
        ]
    
    def __str__(self):
        status = "✓" if self.correct else "✗"
        return f"{self.student.full_name} - {self.vocab.word} {status}"

