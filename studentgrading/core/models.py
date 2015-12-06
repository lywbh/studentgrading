# -*- coding: utf-8 -*-
import datetime
from decimal import Decimal


from django.db import models
from django.db.utils import IntegrityError
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

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
        verbose_name='username',
    )
    name = models.CharField(max_length=255)
    sex = models.CharField(max_length=10, choices=SEX_CHOICES, blank=True,)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Check uniqueness of user"""
        # If self.user is already related to a role, raise error
        role = get_role_of(self.user)
        if role and not role == self:
            raise IntegrityError('user already used')

        super(UserProfile, self).save(*args, **kwargs)


def get_role_of(user):
    """
    Return an instance of one of the roles:['Student', 'Instructor', 'Assistant',
    etc] according to a User instance

    If no instance exists, return None
    """
    # Get a list of model instance names(lowercase) whose model inherits UserProfile
    instance_names = [
        f.get_accessor_name()
        for f in User._meta.get_all_related_objects()
        if not f.field.rel.multiple
    ]
    # Find the name this user has
    instance_related_name = None
    for name in instance_names:
        if hasattr(user, name):
            instance_related_name = name
            break

    if not instance_related_name:
        return None
    return getattr(user, instance_related_name)


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

    NUMBERS_LIST = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')

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

    def get_used_group_number(self):
        """Return a list of used group number"""
        return self.group_set.values_list('number', flat=True)

    def get_next_group_number(self):
        """Return the next available group number"""
        return min(set(self.NUMBERS_LIST) - set(self.get_used_group_number()))

    def get_students(self):
            return self.student_set.all()

    def get_groups(self):
            return self.group_set.all()

    def get_assignments(self):
            return self.assignments.all()

    def add_group(self, members=(), *args, **kwargs):
        group = self.group_set.create(*args, **kwargs)
        group.members.add(*members)

    def add_assignment(self, *args, **kwargs):
        self.assignments.create(*args, **kwargs)


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

    def __str__(self):
        return '{name}-{id}'.format(name=self.name, id=self.inst_id)

    def get_courses(self):
        return self.courses.all()

    def add_course(self, *args, **kwargs):
        new_course = Course.objects.create(*args, **kwargs)
        Teaches.objects.create(instructor=self, course=new_course)

    def delete_course(self, d_course):
        d_course.delete()


class InstructorContactInfo(ContactInfo):
    instructor = models.ForeignKey(Instructor)


class Group(models.Model):

    number = models.CharField(
        verbose_name=_('group number'),
        max_length=10,
        default='',
        blank=True,
    )
    name = models.CharField(
        verbose_name=_('group name'),
        max_length=255,
        default='',
        blank=True,
    )
    course = models.ForeignKey(Course)
    leader = models.ForeignKey(Student, related_name='leader_of', blank=True, null=True)
    members = models.ManyToManyField(Student, related_name='member_of')

    def __str__(self):
        """Return class full name: YEAR-SEMESTER-NUM[-NAME]"""
        return (
            '{year}-{semester}-{number}'.format(
                year=self.course.year,
                semester=self.course.semester,
                number=self.number,
            ) + ('-{}'.format(self.name) if self.name else '')
        )

    def validate_group_number(self):
        """
        Check if number is not used and is in the number list of its course,
        or raise ValidationError
        """
        if (not self.course.group_set.filter(pk=self.pk).exists() and
                self.number in self.course.get_used_group_number()):
            raise ValidationError({'number': 'Number already used.'})
        if self.number not in self.course.NUMBERS_LIST:
            raise ValidationError({'number': 'Number should be in the list.'})

    def clean(self):
        # check if number is valid
        self.validate_group_number()
        pass

    def save(self, *args, **kwargs):
        # check if number is valid
        try:
            self.validate_group_number()
        except ValidationError:
            if self.number:
                raise
            # if number is empty, fill in default number
            self.number = self.course.get_next_group_number()

        super(Group, self).save(*args, **kwargs)


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
