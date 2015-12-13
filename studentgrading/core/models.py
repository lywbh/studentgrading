# -*- coding: utf-8 -*-

import datetime
from decimal import Decimal


from django.db import models
from django.db.models import F
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from ..utils.import_data import get_student_dataset, handle_uploaded_file, delete_uploaded_file
from django.shortcuts import get_object_or_404
from ..users.models import User


def validate_all_digits_in_string(string):
    if not string.isdigit():
        raise ValidationError('%s is not of all digits' % string)


class UserProfile(models.Model):

    SEX_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name='username')
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

    def __str__(self):
        return '{title}-{year}-{semester}'.format(
            title=self.title, year=self.year, semester=self.semester,
        )

    def clean(self):
        if self.min_group_size > self.max_group_size:
            raise ValidationError(
                {'min_group_size': 'Min size of groups must not be greater than max size.',
                 'max_group_size': 'Min size of groups must not be greater than max size.'}
            )

    def get_students(self):
        return self.student_set.all()

    def get_groups(self):
        return self.group_set.all()

    def get_assignments(self):
        return self.assignments.all()

    def add_group(self, members=(), *args, **kwargs):
        _group = self.group_set.create(*args, **kwargs)
        _group.members.add(*members)

    def delete_group(self, group):
        group.delete()

    def add_assignment(self, *args, **kwargs):
        assi = self.assignments.create(*args, **kwargs)

    def delete_assignment(self, assignement):
        assignement.delete()


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

    def get_courses(self):
        return self.courses.all()


class StudentContactInfo(ContactInfo):
    student = models.ForeignKey(Student)


class Instructor(UserProfile):

    inst_id = models.CharField(
        verbose_name=_("instructor's ID"),
        unique=True,
        max_length=255,
        validators=[validate_all_digits_in_string],
    )
    courses = models.ManyToManyField(
        Course,
        related_name='instructors',
        through='Teaches',
        through_fields=('instructor', 'course')
    )

    def import_student_takes(f, course_pk):

        xlpath = handle_uploaded_file(f)
        data = get_student_dataset(xlpath)
        data.append_col(course_pk, header='course')

        rows = data.dict
        for row in rows:

            stu = get_object_or_404(Student, s_id=row['s_id'])
            if not (stu.courses.filter(pk=row['course'])):
                cours = Course.objects.get(pk=row['course'])
                Takes.objects.create(student=stu, course=cours)

        delete_uploaded_file(xlpath)

    def __str__(self):
        return '{name}-{id}'.format(name=self.name, id=self.inst_id)

    #@classmethod
    def get_courses(self, inst_pk):
        return self.courses.all()

    def add_course(self, *args, **kwargs):
        new_course = Course.objects.create(*args, **kwargs)
        Teaches.objects.create(instructor=self, course=new_course)

    def delete_course(self, d_course):
        d_course.delete()


class InstructorContactInfo(ContactInfo):
    instructor = models.ForeignKey(Instructor)


class Group(models.Model):

    NUMBERS_LIST = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')

    def get_list_of_available_numbers(self):
        """
        Get a list of available group number in the course it belongs to
        """
        numbers_set = set(self.NUMBERS_LIST)
        numbers_used_set = set(
            self.course.group_set.values_list('number', flat=True)
        )
        return list(numbers_set - numbers_used_set)

    def number_default(self):
        """
        Get the first available group number in the course it belongs to
        """
        return sorted(self.get_list_of_available_numbers())[0]

    # automatically generated group no
    number = models.CharField(
        verbose_name=_('group number'),
        max_length=10,
        # default=number_default,
        null=True,
    )
    name = models.CharField(
        verbose_name=_('group name'),
        max_length=255,
        default='',
        blank=True,
    )
    course = models.ForeignKey(Course)
    leader = models.ForeignKey(
        Student,
        related_name='leader_of',
        null=True,
        blank=True)
    members = models.ManyToManyField(
        Student,
        related_name='member_of',
        null=True,
        blank=True)

    # return class full name: YEAR-SEMESTER-NUM[-NAME]
    def __str__(self):
        return ('{year}-{semester}-{number}'.format(
            year=self.course.year,
            semester=self.course.semester,
            number=self.number,
        ) + ('-{}'.format(self.name) if self.name else '')
        )

    def clean(self):
        # check if number is in the list
        if self.number not in self.NUMBERS_LIST:
            raise ValidationError({'number': 'Invalid group number.'})


class GroupContactInfo(ContactInfo):
    group = models.ForeignKey(Group)


class CourseAssignment(models.Model):

    course = models.ForeignKey(Course, related_name='assignments')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
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

    def __str__(self):
        return '{course}-#{no}-{title}'.format(
            no=self.no_in_course,
            title=self.title,
            course=self.course,
        )

    def clean(self):
        # validate grade ratio: (0, 1]
        if not (Decimal(0) < self.grade_ratio <= Decimal(1.0)):
            raise ValidationError({'grade_ratio': 'Invalid grade ratio.'})

    def get_no_in_course(self):
        """
        Return the ranking digital number of this assignment in its course
        according to the time assigned
        """
        qs_list = []
        for assignmt in self.course.assignments.all():
            qs_list.append((assignmt.id, assignmt.assigned_dtm))
        ranking = 1
        while qs_list:
            oldest = min(qs_list, key=lambda e: e[1])
            if oldest[0] == self.id:
                break
            else:
                ranking += 1
                qs_list.remove(oldest)
        return ranking


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
    grade = models.DecimalField(max_digits=5, decimal_places=2,
                                null=True, blank=True, )

    class Meta:
        verbose_name_plural = 'Takes'

    def __str__(self):
        return '{stu}-{course}'.format(
            stu=self.student.__str__(),
            course=self.course.__str__(),
        )


def import_student(f):

    xlpath = handle_uploaded_file(f)

    data = get_student_dataset(xlpath)

    rows = data.dict

    for row in rows:
        if not(Student.objects.filter(s_id=row['s_id'])):
            #s_class = Class.objects.get(class_id=str(row['class_id']))
            s_class = get_object_or_404(Class, class_id=str(row['class_id']))
            s_user = User.objects.create_user(
                username=row['s_id'],
                password=row['s_id']
            )

            Student.objects.create(
                user=s_user,
                name=row['name'],
                sex=row['sex'],
                s_id=row['s_id'],
                s_class=s_class
            )
    delete_uploaded_file(xlpath)
