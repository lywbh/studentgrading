# -*- coding: utf-8 -*-

import datetime

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

def validate_all_digits_in_string(string):
    if string.isdigit():
        raise ValidationError('%s is not of all digits' % string)

class ContactInfo(models.Model):

    qq = models.CharField(
        max_length=50,
        validators=[validate_all_digits_in_string],
        blank=True,
        null=True,
    )
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(
        max_length=50,
        validators=[validate_all_digits_in_string],
        blank=True,
        null=True,
    )

class UserProfile(models.Model):

    SEX_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL)
    name = models.CharField(max_length=255)
    sex = models.CharField(max_length=10, choices=SEX_CHOICES, blank=True, null=True)
    contact_info = models.OneToOneField(ContactInfo, null=True, blank=True)

    class Meta:
        abstract = True


class Class(models.Model):
    class_id = models.CharField(
        verbose_name=_("student's id"),
        unique=True,
        max_length=255,
        validators=[validate_all_digits_in_string],
    )


class Student(UserProfile):
    s_id = models.CharField(
        verbose_name=_("student's id"),
        unique=True,
        max_length=255,
        validators=[validate_all_digits_in_string],
    )
    s_class = models.ForeignKey(Class, verbose_name=_("student's class"))


class Course(models.Model):

    YEAR_CHOICES = []
    for r in range(timezone.now().year - 50, timezone.now().year + 1):
        YEAR_CHOICES.append((r, r))

    SEMESTER_CHOICES = (
        ('SPG', 'Spring'),
        ('AUT', 'Autumn'),
    )

    classes = models.ManyToManyField(Class)
    title = models.CharField(),
    year = models.IntegerField(
        verbose_name=_('year'),
        choices=YEAR_CHOICES,
        default=timezone.now().year,
    )
    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES)
    description = models.TextField(null=True, blank=True)
    min_group_size = models.IntegerField(
        validators=[MinValueValidator(0)],
        default=0,
    )
    max_group_size = models.IntegerField(
        validators=[MinValueValidator(0)],
        default=0,
    )

    def clean(self):
        if self.min_group_size > self.max_group_size:
            raise ValidationError('Min size of groups must not be greater than max size.')


class Instructor(UserProfile):
    inst_id = models.CharField(
        verbose_name=_("instructor's id"),
        unique=True,
        max_length=255,
        validators=[validate_all_digits_in_string],
    )
    courses = models.ManyToManyField(Course, through='Teaches', through_fields=('instructor', 'course'))


class Group(models.Model):
    course = models.ForeignKey(Course)
    leader = models.ForeignKey(Student, related_name='leader_of')
    members = models.ManyToManyField(Student, related_name='member_of')
    contact_info = models.OneToOneField(ContactInfo, null=True, blank=True)


class CourseAssignment(models.Model):
    course = models.ForeignKey(Course)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    deadline_dtm = models.DateTimeField(default=timezone.now() + datetime.timedelta(days=7))
    assigned_dtm = models.DateTimeField(default=timezone.now())
    grade_ratio = models.DecimalField(max_digits=3, decimal_places=2)


class Teaches(models.Model):
    instructor = models.ForeignKey(Instructor)
    course = models.ForeignKey(Course)
    assignments = models.ManyToManyField(CourseAssignment, db_table='assigns')


