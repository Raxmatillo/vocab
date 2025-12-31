from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.files.base import ContentFile
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFit
from PIL import Image
import io

# import FileSizeValidator from a suitable package or define it


from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFit, Adjust

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


class FileSizeValidatorOrResize:
    def __init__(self, limit_mb=2):
        self.limit_mb = limit_mb

    def __call__(self, image_field):
        # Fayl hajmi MB
        size_mb = image_field.size / (1024 * 1024)
        if size_mb <= self.limit_mb:
            return  # Hajmi mos, o'zgartirish shart emas

        # Hajmi katta bo'lsa, rasmni kichraytirish
        img = Image.open(image_field)
        img_format = img.format

        # Maksimal o'lchamni hisoblash: masalan, 800x800
        img.thumbnail((800, 800), Image.ANTIALIAS)

        # Yangi faylga saqlash
        temp_io = io.BytesIO()
        img.save(temp_io, format=img_format, quality=85)
        temp_content = ContentFile(temp_io.getvalue(), name=image_field.name)

        # Rasm maydonini yangilash
        image_field.file = temp_content
        image_field.size = temp_content.size


@deconstructible
class FileSizeValidator:
    def __init__(self, limit_mb):
        self.limit_mb = limit_mb

    def __call__(self, value):
        if value.size > self.limit_mb * 1024 * 1024:
            raise ValidationError(f"Rasm hajmi {self.limit_mb} MB dan oshmasligi kerak.")

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


class ClassRoom(models.Model):
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
        verbose_name = 'ClassRoom'
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
        ClassRoom, 
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
        return f"{self.name} / {self.teacher.full_name}"


class Vocabulary(models.Model):    
    # Kategoriya o'qituvchiga tegishli ekanini filtrlaymiz (Admin panel uchun foydali)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='vocabularies'
    )
    
    word = models.CharField(max_length=255, verbose_name="So'z")
    
    image = ProcessedImageField(
        upload_to='vocabularies/%Y/%m/%d/',
        processors=[ResizeToFit(800, 800)],
        format='JPEG',
        options={'quality': 85},
        blank=True,
        null=True
    )

    
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    MAX_IMAGE_MB = 2

    def save(self, *args, **kwargs):
        if self.image and self.image.size > self.MAX_IMAGE_MB * 1024 * 1024:
            img = Image.open(self.image)
            img_format = img.format or 'JPEG'

            # Thumbnail bilan rasmni kichraytirish
            img.thumbnail((800, 800), Image.Resampling.LANCZOS)

            temp_io = io.BytesIO()
            img.save(temp_io, format=img_format, quality=85)
            temp_content = ContentFile(temp_io.getvalue(), name=self.image.name)

            # Rasmni yangilash
            self.image.save(self.image.name, temp_content, save=False)

        super().save(*args, **kwargs)


    class Meta:
        verbose_name = 'Lug\'at'
        verbose_name_plural = 'Lug\'atlar'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['teacher']),
            models.Index(fields=['word']), # Qidiruvni tezlashtirish uchun
        ]

    def __str__(self):
        return f"{self.word} ({self.category.name})"



class TestSession(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='test_sessions'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE
    )
    total_questions = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    finished_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def percentage(self):
        if self.total_questions == 0: return 0
        return round((self.correct_answers / self.total_questions) * 100, 2)
    
    def __str__(self):
        return f"{self.student} - {self.category}"


class Result(models.Model):
    session = models.ForeignKey(TestSession, on_delete=models.CASCADE, related_name='details')
    vocabulary = models.ForeignKey(Vocabulary, on_delete=models.CASCADE)
    is_correct = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Result'
        verbose_name_plural = 'Results'
        ordering = ['-created_at']
    
    # def __str__(self):
    #     status = "✓" if self.correct else "✗"
    #     return f"{self.session.student.full_name} - {self.vocabulary.word} {status}"

