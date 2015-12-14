# -*- coding: utf-8 -*-
import datetime
from decimal import Decimal

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from ..utils.import_data import get_student_dataset, handle_uploaded_file, delete_uploaded_file
from django.shortcuts import get_object_or_404
from ..users.models import User


# Helper Functions
# ------------------------------------------------------------------------------
def validate_all_digits_in_string(string):
    if not string.isdigit():
        raise ValidationError('%s is not of all digits' % string)


# Model Classes
# ------------------------------------------------------------------------------
class UserProfile(models.Model):

    SEX_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name='username',
    )
    name = models.CharField(max_length=255, )
    sex = models.CharField(max_length=10, choices=SEX_CHOICES, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name

    def validate_not_empty_fields(self):
        """Make sure certain char or text fields are not empty"""
        # name field should not be empty
        if not self.name:
            raise ValidationError({'name': 'empty name'})

    def validate_user_uniqueness(self):
        """One user can only be bound to one role(Student, Instructor, etc"""
        role = get_role_of(self.user)
        if role and not role == self:
            raise ValidationError('user already used')

    def clean(self):
        self.validate_user_uniqueness()

    def save(self, *args, **kwargs):
        UserProfile.validate_not_empty_fields(self)
        self.validate_user_uniqueness()
        super(UserProfile, self).save(*args, **kwargs)


class ContactInfoType(models.Model):
    type_string = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.type_string

    def validate_type_string_uniqueness(self):
        """Check if type string is unique no matter the case."""
        if ContactInfoType.objects.filter(
            type_string__iexact=self.type_string
        ).exists():
            raise ValidationError({'type_string': 'Type already exists.'})

    def clean(self):
        self.validate_type_string_uniqueness()

    def save(self, *args, **kwargs):
        self.validate_type_string_uniqueness()
        # Validate type_string is not empty
        if self.type_string is '':
            raise ValidationError({'type_string': 'Type is empty.'})
        super(ContactInfoType, self).save(*args, **kwargs)


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

    def validate_not_empty_fields(self):
        """Make sure certain char or text fields are not empty"""
        if not self.content:
            raise ValidationError({'content': 'empty content'})

    def save(self, *args, **kwargs):
        self.validate_not_empty_fields()
        super(ContactInfo, self).save(*args, **kwargs)


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

    def validate_not_empty_fields(self):
        """Make sure certain char or text fields are not empty"""
        if not self.class_id:
            raise ValidationError({'class_id': 'empty class ID'})

    def save(self, *args, **kwargs):
        self.validate_not_empty_fields()
        super(Class, self).save(*args, **kwargs)


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

    def validate_not_empty_fields(self):
        """Make sure certain char or text fields are not empty"""
        if not self.title:
            raise ValidationError({'title': 'empty course title'})
        if not self.semester:
            raise ValidationError({'semester': 'empty course semester'})

    def validate_group_size(self):
        if self.min_group_size > self.max_group_size:
            raise ValidationError(
                {'min_group_size': 'Min size of groups must not be greater than max size.',
                 'max_group_size': 'Min size of groups must not be greater than max size.'}
            )

    def clean(self):
        self.validate_group_size()

    def save(self, *args, **kwargs):
        self.validate_not_empty_fields()
        self.validate_group_size()
        super(Course, self).save(*args, **kwargs)

    def get_used_group_numbers(self):
        """Return a list of used group number"""
        return self.group_set.values_list('number', flat=True)

    def get_next_group_number(self):
        """Return the next available group number"""
        return min(set(self.NUMBERS_LIST) - set(self.get_used_group_numbers()))

    def get_all_students(self):
        return self.student_set.all()

    def get_all_groups(self):
        return self.group_set.all()

    def get_all_assignments(self):
        return self.assignments.all()

    def add_group(self, members=(), *args, **kwargs):
        group = self.group_set.create(*args, **kwargs)
        group.members.add(*members)

    def add_assignment(self, *args, **kwargs):
        self.assignments.create(*args, **kwargs)

    def get_group(self, group_id):
        try:
            return self.group_set.get(number=group_id)
        except Group.DoesNotExist:
            return None


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
        through='Takes',
        through_fields=('student', 'course')
    )

    def __str__(self):
        return '{name}-{id}'.format(name=self.name, id=self.s_id)

    def validate_not_empty_fields(self):
        """Make sure certain char or text fields are not empty"""
        super(Student, self).validate_not_empty_fields()
        if not self.s_id:
            raise ValidationError({'s_id': 'empty student ID'})

    def save(self, *args, **kwargs):
        self.validate_not_empty_fields()
        super(Student, self).save(*args, **kwargs)

    def get_all_courses(self):
        return self.courses.all()
        
    def get_course(self, pk):
        try:
            return self.courses.get(pk=pk)
        except Course.DoesNotExist:
            return None

    def get_group(self, course_pk):
        """
        Get a group this student belongs to

        Raise ValidationError if student does not take the course.
        """
        course = self.get_course(course_pk)
        if not course:
            raise ValidationError('This student does not take the course.')
        qs = self.member_of.filter(course=course)
        if not qs.exists():
            qs = self.leader_of.filter(course=course)
            if not qs.exists():
                return None
        return qs[0]    # only return the first group, there should be only one


class StudentContactInfo(ContactInfo):
    student = models.ForeignKey(Student, related_name='contact_infos')


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

    def validate_not_empty_fields(self):
        """Make sure certain char or text fields are not empty"""
        super(Instructor, self).validate_not_empty_fields()
        if not self.inst_id:
            raise ValidationError({'inst_id': 'empty instructor ID'})

    def save(self, *args, **kwargs):
        self.validate_not_empty_fields()
        super(Instructor, self).save(*args, **kwargs)

    def get_all_courses(self):
        return self.courses.all()

    def get_course(self, pk):
        try:
            return self.courses.get(pk=pk)
        except Course.DoesNotExist:
            return None

    def add_course(self, *args, **kwargs):
        """Add a course to instructor itself"""
        new_course = Course.objects.create(*args, **kwargs)
        Teaches.objects.create(instructor=self, course=new_course)

    def delete_course(self, pk):
        try:
            course = self.courses.get(pk=pk)
        except Course.DoesNotExist:
            pass
        else:
            course.delete()

    def import_student_takes(self, f, course_pk):
        """
        Import students taking the course from xls file f

        Skip students who do not exist.
        Skip students who already take this course
        If file is of invalid type, raise ValidationError
        :param f: a xls file, of request.FILES['file'] type
        :param course_pk: the course the students take
        :return: count of successful import
        """
        xlpath = handle_uploaded_file(f)
        try:
            data = get_student_dataset(xlpath)
        except TypeError:
            raise ValidationError('Invalid file type.')
        course = self.get_course(course_pk)
        if not course:
            return 0

        rows = data.dict
        count = 0
        for row in rows:
            try:
                stu = Student.objects.get(s_id=row['s_id'])
            except Student.DoesNotExist:
                continue
            if not (stu.courses.filter(pk=course_pk).exists()):
                Takes.objects.create(student=stu, course=course)
                count += 1

        delete_uploaded_file(xlpath)
        return count


class InstructorContactInfo(ContactInfo):
    instructor = models.ForeignKey(Instructor, related_name='contact_infos')


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
        """Return group full name: YEAR-SEMESTER-NUM[-NAME]"""
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
                self.number in self.course.get_used_group_numbers()):
            raise ValidationError({'number': 'Number already used.'})
        if self.number not in self.course.NUMBERS_LIST:
            raise ValidationError({'number': 'Number should be in the list.'})

    def clean(self):
        # check if number is valid
        self.validate_group_number()

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
    group = models.ForeignKey(Group, related_name='contact_infos')


class CourseAssignment(models.Model):

    course = models.ForeignKey(Course, related_name='assignments')
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

    def __str__(self):
        return '{course}-#{no}-{title}'.format(
            no=self.no_in_course,
            title=self.title,
            course=self.course,
        )

    def validate_not_empty_fields(self):
        """Make sure certain char or text fields are not empty"""
        if not self.title:
            raise ValidationError({'title': 'empty title'})

    def validate_grade_ratio(self):
        """Make sure ratio is (0, 1]"""
        if not (Decimal(0) < self.grade_ratio <= Decimal(1.0)):
            raise ValidationError({'grade_ratio': 'Grade ratio should be in (0, 1].'})

    def clean(self):
        self.validate_grade_ratio()

    def save(self, *args, **kwargs):
        self.validate_not_empty_fields()
        self.validate_grade_ratio()

        super(CourseAssignment, self).save(*args, **kwargs)

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

    class Meta:
        verbose_name_plural = "teaches"

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
        verbose_name_plural = 'takes'

    def validate_grade(self):
        """Check grade is in [0, 100]"""
        if self.grade and not (0 <= self.grade <= 100):
            raise ValidationError({'grade': 'Grade should be in [0, 100]'})

    def clean(self):
        self.validate_grade()

    def save(self, *args, **kwargs):
        self.validate_grade()
        super(Takes, self).save(*args, **kwargs)

    def __str__(self):
        return '{stu}-{course}'.format(
            stu=self.student.__str__(),
            course=self.course.__str__(),
        )


# Global Functions
# ------------------------------------------------------------------------------
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


def import_student(f):
    """
    Import students, for those who do not exist, create
    account for them

    Skip those who already exist
    If the file is of invalid type, raise ValidatioError
    Skip if class does not exist
    :param f: a xls file, of request.FILES['file'] type
    :return: count of successful import
    """
    xlpath = handle_uploaded_file(f)
    try:
        data = get_student_dataset(xlpath)
    except TypeError:
        raise ValidationError('Invalid file type.')
    rows = data.dict

    count = 0
    for row in rows:
        if not(Student.objects.filter(s_id=row['s_id'])):
            try:
                s_class = Class.objects.get(class_id=row['class_id'])
            except Class.DoesNotExist:
                continue
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
            count += 1

    delete_uploaded_file(xlpath)

    return count
