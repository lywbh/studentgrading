# -*- coding: utf-8 -*-

import datetime

from django.db import models
from django.db.models import F
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

def validate_all_digits_in_string(string):
    if not string.isdigit():
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
        verbose_name=_("Class's id"),
        unique=True,
        max_length=255,
        validators=[validate_all_digits_in_string],
    )

    def __str__(self):
        return self.class_id

    # TODO: delete after test
    @classmethod
    def get_all_classes(cls):
        return cls.objects.all().values()

class Student(UserProfile):
    s_id = models.CharField(
        verbose_name=_("student's id"),
        unique=True,
        max_length=255,
        validators=[validate_all_digits_in_string],
    )
    s_class = models.ForeignKey(Class, verbose_name=_("student's class"))

    def __str__(self):
        if not self.name:
            return self.s_id
        return '%s-%s' % (self.name, self.s_id)

    # TODO: delete after test
    @classmethod
    def get_all_students(cls):
        return cls.objects.all().values()

class Course(models.Model):

    SEMESTER_CHOICES = (
        ('SPG', 'Spring'),
        ('AUT', 'Autumn'),
    )

    classes = models.ManyToManyField(Class)
    title = models.CharField(max_length=255)
    year = models.IntegerField(
        default=timezone.now().year,
        validators=[MinValueValidator(0), MaxValueValidator(9999), ]
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

    # TODO: delete after test
    @classmethod
    def get_all_courses(cls):
        return cls.objects.all().values()

    def __str__(self):
        return '{year}-{semester}-{title}'.format(
            **dict(title=self.title, year=self.get_year_display(), semester=self.get_semester_display())
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

    def __str__(self):
        return '%s-%s'.format(self.name, self.inst_id)

    # TODO: delete after test
    @classmethod
    def get_all_instructors(cls):
        return cls.objects.all().values()


class Group(models.Model):

    NUMBERS_LIST = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')

    def get_list_of_available_numbers(self):
        numbers_set = set(self.NUMBERS_LIST)
        numbers_used_set = set(
            Course.objects.get(
                pk=F('course__pk')
            ).group_set.values_list('number', flat=True)
        )
        return list(numbers_set - numbers_used_set)

    # get first available number for default number
    def number_default(self):
        return sorted(self.get_available_number_list())[0]

    # automatically generated group no
    number = models.CharField(
        verbose_name=_('group number'),
        max_length=10,
        unique=True,
        default=number_default,
    )
    name = models.CharField(
        verbose_name=_('group name'),
        max_length=255,
        default='',
        null=True,
        blank=True,
    )
    course = models.ForeignKey(Course)
    leader = models.ForeignKey(Student, related_name='leader_of')
    members = models.ManyToManyField(Student, related_name='member_of')
    contact_info = models.OneToOneField(ContactInfo, null=True, blank=True)

    # return class full name: YEAR-SEMESTER-NUM[-NAME]
    def __str__(self):
        return (
            ('%s-%s-%s' % (F('course__year'), F('course__semester'), self.number)) +
            (('-%s' % self.name) if self.name else '')
        )

    def clean(self):
        # check if number is in the list
        if self.number not in self.NUMBERS_LIST:
            raise ValidationError('Invalid group number.')

    # TODO: delete after test
    @classmethod
    def get_all_groups(cls):
        return cls.objects.all().values()


class CourseAssignment(models.Model):

    def no_in_course_default(self):
        Course.objects.get(
            pk=F('course__pk')
        ).assignments.aggregate(models.Count('pk'))

    course = models.ForeignKey(Course, related_name='assignments')
    no_in_course = models.IntegerField()
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    deadline_dtm = models.DateTimeField(default=timezone.now() + datetime.timedelta(days=7))
    assigned_dtm = models.DateTimeField(default=timezone.now())
    grade_ratio = models.DecimalField(max_digits=3, decimal_places=2)

    # TODO: add course info
    def __str__(self):
        return 'No.%s-%s'.format(self.no_in_course, self.title)

    # TODO: delete after test
    @classmethod
    def get_all_assignments(cls):
        return cls.objects.all().values()


class Teaches(models.Model):
    instructor = models.ForeignKey(Instructor)
    course = models.ForeignKey(Course)
    assignments = models.ManyToManyField(CourseAssignment, db_table='assigns')


