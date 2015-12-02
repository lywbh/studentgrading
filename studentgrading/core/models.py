# -*- coding: utf-8 -*-

import datetime

from django.db import models
from django.db.models import F
from django.db.models import Max
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

def validate_all_digits_in_string(string):
    if not string.isdigit():
        raise ValidationError('%s is not of all digits' % string)

class UserProfile(models.Model):

    SEX_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, verbose_name='username')
    name = models.CharField(max_length=255)
    sex = models.CharField(max_length=10, choices=SEX_CHOICES, blank=True,)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class ContactInfoType(models.Model):
    type_string = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.type_string


class ContactInfo(models.Model):

    info_type = models.ForeignKey(
        ContactInfoType,
        related_name='%(class)s',
    )
    content = models.CharField(max_length=255)

    class Meta:
        abstract = True

    def __str__(self):
        return '{}'.format(self.content)


class Class(models.Model):
    class_id = models.CharField(
        verbose_name=_("Class's id"),
        unique=True,
        max_length=255,
        validators=[validate_all_digits_in_string],
    )

    class Meta:
        verbose_name_plural = 'Classes'

    def __str__(self):
        return self.class_id

    # TODO: delete after test
    @classmethod
    def get_all_classes(cls):
        return cls.objects.all().values()

class Course(models.Model):

    SEMESTER_CHOICES = (
        ('SPG', 'Spring'),
        ('AUT', 'Autumn'),
    )

    title = models.CharField(max_length=255)
    year = models.IntegerField(
        default=timezone.now().year,
        validators=[MinValueValidator(0), MaxValueValidator(9999), ]
    )
    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES)
    description = models.TextField(blank=True)
    min_group_size = models.IntegerField(
        validators=[MinValueValidator(0)],
        default=0,
    )
    max_group_size = models.IntegerField(
        validators=[MinValueValidator(0)],
        default=0,
    )

    class Meta:
        unique_together = (('title', 'year', 'semester'), )

    # TODO: delete after test
    @classmethod
    def get_all_courses(cls):
        return cls.objects.all().values()

    def __str__(self):
        return '{title}-{year}-{semester}'.format(
            title=self.title, year=self.year, semester=self.semester,
        )

    def clean(self):
        if self.min_group_size > self.max_group_size:
            raise ValidationError('Min size of groups must not be greater than max size.')


class Student(UserProfile):
    s_id = models.CharField(
        verbose_name=_("student's id"),
        unique=True,
        max_length=255,
        validators=[validate_all_digits_in_string],
    )
    s_class = models.ForeignKey(Class, verbose_name=_("student's class"))
    courses = models.ManyToManyField(
        Course,
        null=True,
        blank=True,
        through='Takes',
        through_fields=('student', 'course')
    )

    def __str__(self):
        return '{name}-{id}'.format(name=self.name, id=self.s_id)

    # TODO: delete after test
    @classmethod
    def get_all_students(cls):
        return cls.objects.all().values()


class StudentContactInfo(ContactInfo):
    student = models.ForeignKey(Student)


class Instructor(UserProfile):

    inst_id = models.CharField(
        verbose_name=_("instructor's ID"),
        unique=True,
        max_length=255,
        validators=[validate_all_digits_in_string],
    )
    courses = models.ManyToManyField(Course, through='Teaches', through_fields=('instructor', 'course'))

    def __str__(self):
        return '{name}-{id}'.format(name=self.name, id=self.inst_id)

    # TODO: delete after test
    @classmethod
    def get_all_instructors(cls):
        return cls.objects.all().values()


class InstructorContactInfo(ContactInfo):
    instructor = models.ForeignKey(Instructor)


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
        blank=True,
    )
    course = models.ForeignKey(Course)
    leader = models.ForeignKey(Student, related_name='leader_of')
    members = models.ManyToManyField(Student, related_name='member_of')

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


class GroupContactInfo(ContactInfo):
    group = models.ForeignKey(Group)


class CourseAssignment(models.Model):

    def default_no_in_course(self):
        return self.course.assignments.all().aggregate(Max('no_in_course')) + 1

    course = models.ForeignKey(Course, related_name='assignments')
    no_in_course = models.IntegerField(default=default_no_in_course)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    deadline_dtm = models.DateTimeField(
        default=timezone.now() + datetime.timedelta(days=7),
        verbose_name='deadline',
    )
    assigned_dtm = models.DateTimeField(
        default=timezone.now(),
        verbose_name='assigned time',
    )
    grade_ratio = models.DecimalField(max_digits=3, decimal_places=2)

    class Meta:
        verbose_name = "course assignment"
        verbose_name_plural = "course assignments"

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

    class Meta:
        verbose_name_plural = "Teaches"

    def __str__(self):
        return '{course_title}-{inst}-{course_year}-{course_semester}'.format(
            course_title=self.course.title,
            course_year=self.course.year,
            course_semester=self.course.get_semester_display(),
            inst=self.instructor.name,
        )

    def assignments_count(self):
        return self.assignments.count()
    assignments_count.short_description = 'number of assignments'


class Takes(models.Model):
    student = models.ForeignKey(Student)
    course = models.ForeignKey(Course)
    grade = models.DecimalField(max_digits=5, decimal_places=2, )

    class Meta:
        verbose_name_plural = 'Takes'

    def __str__(self):
        return '{stu}-{course}'.format(
            stu=self.student.__str__(),
            course=self.course.__str__(),
        )
