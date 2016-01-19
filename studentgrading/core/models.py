# -*- coding: utf-8 -*-
import datetime
from decimal import Decimal

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models import Q
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
from django.forms.models import model_to_dict

from guardian.shortcuts import assign_perm, remove_perm

from ..utils.import_data import get_student_dataset, handle_uploaded_file, delete_uploaded_file
from ..users.models import User


# ------------------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------------------
def validate_all_digits_in_string(string):
    if not string.isdigit():
        raise ValidationError('%s is not of all digits' % string)


class ModelDiffMixin(object):
    """
    A model mixin that tracks model fields' values and provide some useful api
    to know what fields have been changed.

    You should explicitly call save_all_field_diff() when you are done with diff
    """
    def __init__(self, *args, **kwargs):
        super(ModelDiffMixin, self).__init__(*args, **kwargs)
        self.__initial = self._dict

    @property
    def _dict(self):
        return model_to_dict(self, fields=[field.name for field in self._meta.fields])

    @property
    def diff(self):
        past = self.__initial
        now = self._dict
        diffs = [(k, (v, now[k])) for k, v in past.items() if v != now[k]]
        return dict(diffs)

    @property
    def has_changed(self):
        return bool(self.diff)

    @property
    def changed_fields(self):
        return list(self.diff.keys())

    def get_field_diff(self, field_name):
        """
        Returns a diff for field if it's changed and None otherwise
        """
        return self.diff.get(field_name, None)

    def get_old_field(self, field_name):
        diff = self.diff.get(field_name, None)
        return diff[0] if diff else None

    def save_all_field_diff(self):
        """
        Save differences
        """
        self.__initial = self._dict


def split_four_level_perm_string(perm):
    """
    Split a four-level permission string into level string and base string.

    e.g. `'core.view_student'` to `'all'`, `'core.view_student'`
    e.g. `'core.view_student_base'` to `'base'`, `'core.view_student'`
    :param perm: a four-level permission string
    :return: level string and base string pair
    """
    frags = perm.split('_')
    frags_len = len(frags)
    if frags_len == 2:
        # all permission
        level_name = 'all'
        base_perm = perm
    elif frags_len == 3:
        # one of the three level
        level_name = frags[-1]
        base_perm = frags[0] + '_' + frags[1]
    else:
        raise ValueError('Invalid permission string.')

    return level_name, base_perm


def assign_four_level_perm(perm, user, obj, override=False):
    """
    Assigns four-level view/change permission to user on obj

    One user can only have one of the four-level permissions of same action on obj.
    Higher-level permission will override lower one, otherwise not by default.
    If `override` is set to `True`, new permission will override old one.
    Model of obj should define four-level permissions, or DoesNotExist exception will be raised.
    Use `guardian.shortcuts.assign_perm`.
    :param perm: perm string, same as `assign_perm`
    :param user: instance of `User`, same `assign_perm`
    :param obj: model instance, same as `assign_perm`
    :param override: indicate if force overriding old perms
    """
    level_name, base_perm = split_four_level_perm_string(perm)

    all_perm = base_perm
    base_level_perm = base_perm + '_base'
    normal_level_perm = base_perm + '_normal'
    advanced_level_perm = base_perm + '_advanced'

    if override:
        remove_perm(base_level_perm, user, obj)
        remove_perm(normal_level_perm, user, obj)
        remove_perm(advanced_level_perm, user, obj)
        assign_perm(perm, user, obj)
        return

    if level_name == 'base':
        if (not user.has_perm(normal_level_perm, obj) and
           not user.has_perm(advanced_level_perm, obj) and
           not user.has_perm(all_perm, obj)):
            assign_perm(perm, user, obj)
    elif level_name == 'normal':
        if user.has_perm(base_level_perm, obj):
            remove_perm(base_level_perm, user, obj)
        if not user.has_perm(advanced_level_perm, obj):
            assign_perm(perm, user, obj)
    elif level_name == 'advanced':
        if user.has_perm(base_level_perm, obj):
            remove_perm(base_level_perm, user, obj)
        elif user.has_perm(normal_level_perm, obj):
            remove_perm(normal_level_perm, user, obj)
        if not user.has_perm(all_perm, obj):
            assign_perm(perm, user, obj)
    elif level_name == 'all':
        if user.has_perm(base_level_perm, obj):
            remove_perm(base_level_perm, user, obj)
        elif user.has_perm(normal_level_perm, obj):
            remove_perm(normal_level_perm, user, obj)
        elif user.has_perm(advanced_level_perm, obj):
            remove_perm(advanced_level_perm, user, obj)
        assign_perm(perm, user, obj)
    else:
        raise ValueError('Invalid level name.')


def has_four_level_perm(perm, user, obj, exact=False):
    """
    Checks four-level permissions.

    By default, if providing permission is lower-level than existing, return `True`.
    If `exact` is set to `True`, only return `True` on exact matching.
    :param perm: permission string
    :param user: instance of User
    :param obj: target model instance
    :param exact: exact matching or not
    """
    if user.has_perm(perm, obj):
        return True
    else:
        if exact: return False

    level_name, base_perm = split_four_level_perm_string(perm)

    if level_name == 'all':
        return False

    all_perm = base_perm
    normal_level_perm = base_perm + '_normal'
    advanced_level_perm = base_perm + '_advanced'

    if level_name == 'base':
        return (user.has_perm(normal_level_perm, obj) or
                user.has_perm(advanced_level_perm, obj) or
                user.has_perm(all_perm, obj))
    if level_name == 'normal':
        return (user.has_perm(advanced_level_perm, obj) or
                user.has_perm(all_perm, obj))
    if level_name == 'advanced':
        return user.has_perm(all_perm, obj)
    else:
        raise ValueError('Invalid level name.')


# ------------------------------------------------------------------------------
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

    def validate_user_uniqueness(self):
        """One user can only be bound to one role(Student, Instructor, etc"""
        role = get_role_of(self.user)
        if role and not role == self:
            raise ValidationError('user already used')

    def clean(self):
        self.validate_user_uniqueness()

    def save(self, *args, **kwargs):
        self.full_clean()
        self.validate_user_uniqueness()
        super(UserProfile, self).save(*args, **kwargs)


class ContactInfoType(models.Model):
    type_string = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.type_string

    def validate_type_string_uniqueness(self):
        """Check if type string is unique no matter the case."""
        try:
            type_string = ContactInfoType.objects.get(
                type_string__iexact=self.type_string
            )
        except ContactInfoType.DoesNotExist:
            return
        raise ValidationError({'type_string': 'Type {0} already exists.'.format(type_string)})

    def clean(self):
        self.validate_type_string_uniqueness()

    def save(self, *args, **kwargs):
        self.full_clean()
        self.validate_type_string_uniqueness()
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

    def save(self, *args, **kwargs):
        self.full_clean()
        super(ContactInfo, self).save(*args, **kwargs)


class Class(models.Model):
    class_id = models.CharField(
        verbose_name="Class's id",
        unique=True,
        max_length=255,
        validators=[validate_all_digits_in_string],
    )

    class Meta:
        verbose_name_plural = 'Classes'
        permissions = (
            ('view_class', 'Can view class'),
        )

    def __str__(self):
        return self.class_id

    def save(self, *args, **kwargs):
        self.full_clean()
        super(Class, self).save(*args, **kwargs)


class CourseQuerySet(models.QuerySet):
    def taken_by(self, student):
        return self.filter(students=student)

    def given_by(self, instructor):
        return self.filter(instructors=instructor)


class CourseManager(models.Manager):
    pass


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
        default=5,
    )

    objects = CourseManager.from_queryset(CourseQuerySet)()

    class Meta:
        unique_together = (('title', 'year', 'semester'), )
        permissions = (
            ('view_course', 'Can view course'),
            ('view_course_base', "Can view course, base level"),
            ('view_course_normal', "Can view course, normal level"),
            ('view_course_advanced', "Can view course, advanced level"),
            ('change_course_base', "Can change course, base level"),
            ('change_course_normal', "Can change course, normal level"),
            ('change_course_advanced', "Can change course, advanced level"),
        )

    def __str__(self):
        return '{title}-{year}-{semester}'.format(
            title=self.title, year=self.year, semester=self.semester,
        )

    def validate_group_size(self):
        if self.min_group_size > self.max_group_size:
            raise ValidationError({
                'min_group_size': 'Ensure this value is greater than the max one.',
                'max_group_size': 'Ensure this value is less or equal than the min one.',
            })

    def clean(self):
        self.validate_group_size()

    def save(self, *args, **kwargs):
        self.full_clean()
        self.validate_group_size()
        super(Course, self).save(*args, **kwargs)

    # Row-level methods
    # -------------------------------------------------------------------------
    def get_used_group_numbers(self):
        """Return a list of used group number"""
        return self.groups.values_list('number', flat=True)

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
        group = self.groups.create(*args, **kwargs)
        for member in members:
            GroupMembership.objects.create(group=group, student=member)

    def add_assignment(self, *args, **kwargs):
        self.assignments.create(*args, **kwargs)

    def get_group(self, group_id):
        try:
            return self.group_set.get(number=group_id)
        except Group.DoesNotExist:
            return None

    def get_students_not_in_any_group(self):
        q_stu_takes = Q(takes__course=self)
        q_stu_in_group = Q(leader_of__course=self) | Q(member_of__course=self)
        return Student.objects.filter(
            ~(q_stu_takes & q_stu_in_group) & q_stu_takes
        )

    def is_given_by(self, instructor):
        return self.instructors.filter(pk=instructor.pk).exists()

    def is_taken_by(self, student):
        return self.students.filter(pk=student.pk).exists()

    def has_group_including(self, student):
        query = Q(leader=student) | Q(members=student)
        return self.groups.filter(query).exists()

    # Object permission related methods
    # -------------------------------------------------------------------------
    # Object permission handler for users
    # Student
    def assign_base_perms_for_student(self, user):
        assign_four_level_perm('core.view_course_normal', user, self)

    def remove_base_perms_for_student(self, user):
        remove_perm('core.view_course_normal', user, self)

    def has_base_perms_for_student(self, user):
        return has_four_level_perm('core.view_course_normal', user, self)

    def assign_perms_for_course_stu(self, user):
        assign_perm('core.view_course', user, self)
        # plus perms on course groups
        for group in self.groups.all():
            group.assign_perms_for_course_stu(user)

    def remove_perms_for_course_stu(self, user):
        remove_perm('core.view_course', user, self)
        self.assign_base_perms_for_student(user)
        # remove perms on course groups
        for group in self.groups.all():
            group.remove_perms_for_course_stu(user)

    def has_perms_for_course_stu(self, user):
        return user.has_perm('core.view_course', self)

    # Instructor
    def assign_base_perms_for_instructor(self, user):
        assign_four_level_perm('core.view_course_advanced', user, self)

    def remove_base_perms_for_instructor(self, user):
        remove_perm('core.view_course_advanced', user, self)

    def has_base_perms_for_instructor(self, user):
        return has_four_level_perm('core.view_course_advanced', user, self)

    def assign_perms_for_course_inst(self, user):
        assign_perm('core.view_course', user, self)
        assign_four_level_perm('core.change_course_base', user, self)
        assign_perm('core.delete_course', user, self)
        # plus perms on course groups
        for group in self.groups.all():
            group.assign_perms_for_course_inst(user)

    def remove_perms_for_course_inst(self, user):
        remove_perm('core.view_course', user, self)
        remove_perm('core.change_course_base', user, self)
        remove_perm('core.delete_course', user, self)
        self.assign_base_perms_for_instructor(user)
        # remove perms on course groups
        for group in self.groups.all():
            group.remove_perms_for_course_inst(user)

    def has_perms_for_course_inst(self, user):
        return (user.has_perm('core.view_course', self) and
                user.has_perm('core.change_course_base', self) and
                user.has_perm('core.delete_course', self))


@receiver(post_save, sender=Course)
def course_assign_perms(sender, **kwargs):
    course, created = kwargs['instance'], kwargs['created']

    if created:
        # assign base perms for student
        for student in Student.objects.all():
            course.assign_base_perms_for_student(student.user)

        # assign base perms for instructor
        for instructor in Instructor.objects.all():
            course.assign_base_perms_for_instructor(instructor.user)


@receiver(post_delete, sender=Course)
def course_remove_perms(sender, **kwargs):
    course = kwargs['instance']

    # remove base perms for student
    for student in Student.objects.all():
        course.remove_base_perms_for_student(student.user)

    # remove base perms for instructor
    for instructor in Instructor.objects.all():
        course.remove_base_perms_for_instructor(instructor.user)


class StudentQuerySet(models.QuerySet):
    def takes_courses(self, courses):
        query = Q()
        for course in courses:
            query |= Q(courses=course)
        return self.filter(query)

    def in_any_group_of(self, course):
        query = Q(leader_of__course=course) | Q(member_of__course=course)
        return self.filter(query)

    def not_in_any_group_of(self, course):
        return self.filter(~(Q(leader_of__course=course) | Q(member_of__course=course)))

    def in_any_group(self, any=True):
        if any:
            query = Q(leader_of__isnull=False) | Q(member_of__isnull=False)
        else:
            query = Q(leader_of__isnull=True) & Q(member_of__isnull=True)

        return self.filter(query)


class StudentManager(models.Manager):
    def create_student_with_courses(self, courses, **kwargs):
        """
        Create a student object with a list of course objects and other args.

        Use default value for Takes.  Handle no exceptions.
        courses can bt empty
        """
        if not courses:
            courses = []

        stu = self.create(**kwargs)
        for course in courses:
            Takes.objects.create(student=stu, course=course)

        return stu


class Student(ModelDiffMixin, UserProfile):
    s_id = models.CharField(
        verbose_name="student ID",
        unique=True,
        max_length=255,
        validators=[validate_all_digits_in_string],
    )
    s_class = models.ForeignKey(Class, verbose_name="class",
                                related_name='students')
    courses = models.ManyToManyField(
        Course,
        through='Takes',
        through_fields=('student', 'course'),
        related_name='students',
    )

    objects = StudentManager.from_queryset(StudentQuerySet)()

    class Meta:
        permissions = (
            ('view_student', "Can view student"),
            ('view_student_base', "Can view student, base level"),
            ('view_student_normal', "Can view student, normal level"),
            ('view_student_advanced', "Can view student, advanced level"),
            ('change_student_base', "Can change student, base level"),
            ('change_student_normal', "Can change student, normal level"),
            ('change_student_advanced', "Can change student, advanced level"),
            ('student_non', "Redundant permission"),
        )

    def __str__(self):
        return '{name}-{id}'.format(name=self.name, id=self.s_id)

    def save(self, *args, **kwargs):
        self.full_clean()
        super(Student, self).save(*args, **kwargs)

    # Row-level methods
    # -------------------------------------------------------------------------
    def take_new_courses(self, courses):
        """
        Add new courses to the Takes of the student

        Ignore the course already taken
        Use default grade(None)
        """
        for course in courses:
            if self.takes.filter(course__pk=course.pk).exists():
                continue
            Takes.objects.create(student=self, course=course)

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

    def get_classmates(self):
        return self.s_class.students.exclude(pk=self.pk)

    def is_classmate_of(self, student):
        """
        Check if `student` is a classmate of student

        Return `False` if `student` is student itself.
        :param student: instance of Student
        :return: `True` if it is, or `False`
        """
        if self is student:
            return False

        return student in self.get_classmates()

    def is_taking_same_course_with(self, student):
        """
        Check if `student` is taking same course(s) with student.

        Return `False` if `student` is student itself.
        :param student: instance of Student
        :return: `True` if it is, or `False`
        """
        if self is student:
            return False

        return Course.objects.filter(students=self).filter(
            students=student).exists()

    def is_taking_course_given_by(self, instructor):
        """
        Checks if student is taking course given by `instructor`

        :param instructor: Instructor instance
        :return: `True` or `False`
        """
        return self.courses.filter(instructors=instructor).exists()

    def is_taking(self, course):
        return self.courses.filter(pk=course.pk).exists()

    # Object permission related methods
    # -------------------------------------------------------------------------
    # Object permission handlers for other users
    # ------------------------------------
    # For students
    def assign_perms_for_course_stu(self, user):
        """
        Assign permissions for a student taking same course as student

        Do not check if user is taking same course as student
        :param user: User instance of a student
        """
        assign_four_level_perm('core.view_student_base', user, self)

    def remove_perms_for_course_stu(self, user):
        """
        Remove permissions for a student taking same course as student

        Do not check if user is taking same course as student
        :param user: User instance of a student
        """
        remove_perm('core.view_student_base', user, self)

    def has_perms_for_course_stu(self, user):
        """
        Check if user has permissions for student taking same course(s) as student

        Do not check if user is taking same course as student
        :param user: User instance of student
        :return: `True` if has, or `False`
        """
        return has_four_level_perm('core.view_student_base', user, self)

    def assign_perms_for_classmate(self, user, override=False):
        """
        Assign permissions for student's classmate.

        Do not check if user is student's classmate.
        :param user: User instance of a student
        :param override: whether to clear view permissions first before assigning
        """
        assign_four_level_perm('core.view_student_normal', user, self, override)

    def remove_perms_for_classmate(self, user):
        """
        Remove permissions for student's classmate.

        Do not check if user is student's classmate.
        :param user: User instance of a student
        """
        if (user.has_perm('core.view_student_advanced', self) or
           user.has_perm('core.view_student', self)):
            return

        if self.is_taking_same_course_with(user.student):
            self.assign_perms_for_course_stu(user)

        remove_perm('core.view_student_normal', user, self)

    def has_perms_for_classmate(self, user):
        """
        Check if user has permissions for student's classmate

        :param user: User instance of student
        :return: `True` if has, or `False`
        """
        return has_four_level_perm('core.view_student_normal', user, self)

    # For instructors
    def assign_base_perms_for_instructor(self, user):
        """
        Assign permissions for each instructor

        Do not check if user is an instructor
        :param user: User instance of a instructor
        """
        # all instructors have advanced read permissions on all students
        assign_four_level_perm('core.view_student_advanced', user, self)

    def remove_base_perms_for_instructor(self, user):
        """
        Remove permissions for each instructor.

        Do not check if user is an instructor.
        :param user: User instance of an instructor
        """
        remove_perm('core.view_student_advanced', user, self)

    def has_base_perms_for_instructor(self, user):
        """
        Check if user has base permissions for instructor

        :param user: User instance of an instructor
        :return: `True` if has, or `False`
        """
        return has_four_level_perm('core.view_student_advanced', user, self)

    def assign_perms_for_course_inst(self, user):
        """
        Assign permissions for student's course instructor

        Do not check if user is student's course instructor
        :param user: User instance of an instructor
        """
        assign_four_level_perm('core.view_student_advanced', user, self)

    def remove_perms_for_course_inst(self, user):
        """
        Remove permissions for student's course instructor.

        Do not check if user is student's course instructor.
        :param user: User instance of an instructor
        """
        if not self.is_taking_course_given_by(user.instructor):
            remove_perm('core.view_student_advanced', user, self)
        # give instructor least perms
        self.assign_base_perms_for_instructor(user)

    def has_perms_for_course_inst(self, user):
        """
        Check if user has permissions for student taking same course(s) as student

        :param user: User instance of an instructor
        :return: `True` if has, or `False`
        """
        return has_four_level_perm('core.view_student_advanced', user, self)

    # Object permission handlers for relationship
    # ------------------------------------
    def assign_class_perms(self):
        """
        Assign permissions when student-class relationship sets up
        """
        classmates = Student.objects.filter(
            s_class=self.s_class).exclude(pk=self.pk).all()
        for stu in classmates:
            stu.assign_perms_for_classmate(self.user)
            self.assign_perms_for_classmate(stu.user)

    def remove_class_perms(self, s_class):
        """
        Remove permissions when student-class relationship sets up
        """
        classmates = Student.objects.filter(
            s_class=s_class).exclude(pk=self.pk).all()
        for stu in classmates:
            stu.remove_perms_for_classmate(self.user)
            self.remove_perms_for_classmate(stu.user)


@receiver(post_save, sender=Student)
def student_assign_perms(sender, **kwargs):
    """
    Assign permissions after saving student object(creation or update)
    """
    student, created = kwargs['instance'], kwargs['created']
    user = student.user
    if created:     # add permissions for new student
        # model perms
        # 1. student
        assign_perm('core.view_student', user)
        # 2. takes
        assign_perm('core.view_takes', user)
        # 3. course
        assign_perm('core.view_course', user)
        # 4. instructor
        assign_perm('core.view_instructor', user)
        # 5. teaches
        assign_perm('core.view_teaches', user)
        # 6. group
        assign_perm('core.view_group', user)
        assign_perm('core.change_group', user)
        assign_perm('core.add_group', user)

        # object perms
        # 1. student itself
        assign_perm('core.view_student', user, student)
        # 2. courses
        for course in Course.objects.all():
            course.assign_base_perms_for_student(student.user)

        # other students
        # None

        # other instructors
        for inst in Instructor.objects.all():
            student.assign_base_perms_for_instructor(inst.user)

        # foreign relationship perms
        # 1. classmates have view permission
        # and student has view perm to classmates too
        student.assign_class_perms()

    else:   # change permissions after updating student
        old_cls_pk = student.get_old_field('s_class')
        if old_cls_pk:    # if student has a new class now
            # remove all view perms from old classmates
            old_cls = Class.objects.get(pk=old_cls_pk)
            student.remove_class_perms(old_cls)
            # assign view perms to new classmates
            # and student has perm to new classmates too
            if student.s_class:
                student.assign_class_perms()

    student.save_all_field_diff()


@receiver(post_delete, sender=Student)
def student_remove_perms(sender, **kwargs):
    """
    Remove permissions after deleting student object
    """
    student = kwargs['instance']
    user = student.user
    # remove perms after student is deleted
    # remove model perms
    remove_perm('core.view_student', user)
    remove_perm('core.view_takes', user)
    remove_perm('core.view_course', user)
    remove_perm('core.view_instructor', user)
    remove_perm('core.view_teaches', user)

    remove_perm('core.view_group', user)
    remove_perm('core.change_group', user)
    remove_perm('core.add_group', user)

    remove_perm('core.view_student', user, student)

    for course in Course.objects.all():
        course.remove_base_perms_for_student(student.user)

    for inst in Instructor.objects.all():
        student.remove_base_perms_for_instructor(inst.user)

    # remove all view perms from classmates
    student.remove_class_perms(student.s_class)


class StudentContactInfo(ContactInfo):
    student = models.ForeignKey(Student, related_name='contact_infos')


class InstructorQuerySet(models.QuerySet):
    def gives_courses(self, courses):
        query = Q()
        for course in courses:
            query |= Q(courses=course)
        return self.filter(query)


class InstructorManager(models.Manager):
    pass


class Instructor(UserProfile):

    inst_id = models.CharField(
        verbose_name="instructor's ID",
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
    objects = InstructorManager.from_queryset(InstructorQuerySet)()

    class Meta:
        permissions = (
            ('view_instructor', 'Can view instructor'),
            ('view_instructor_base', "Can view instructor, base level"),
            ('view_instructor_normal', "Can view instructor, normal level"),
            ('view_instructor_advanced', "Can view instructor, advanced level"),
            ('change_instructor_base', "Can change instructor, base level"),
            ('change_instructor_normal', "Can change instructor, normal level"),
            ('change_instructor_advanced', "Can change instructor, advanced level"),
        )

    def __str__(self):
        return '{name}-{id}'.format(name=self.name, id=self.inst_id)

    def save(self, *args, **kwargs):
        self.full_clean()
        super(Instructor, self).save(*args, **kwargs)

    # Row-level methods
    # -------------------------------------------------------------------------
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
                stu = Student.objects.get(s_id=str(int(row['s_id'])))
            except Student.DoesNotExist:
                continue
            if not (stu.courses.filter(pk=course_pk).exists()):
                Takes.objects.create(student=stu, course=course)
                count += 1

        delete_uploaded_file(xlpath)
        return count

    def is_giving_course_to(self, student):
        """
        Checks if instructor is giving course to `student`.

        :param student: Student instance
        :return: `True` or `False`
        """
        return self.courses.filter(students=student).exists()

    def is_giving(self, course):
        return self.courses.filter(pk=course.pk).exists()

    # Object permission related methods
    # -------------------------------------------------------------------------
    # Object permission handlers for other users
    # ------------------------------------
    # For students
    def assign_perms_for_course_stu(self, user):
        """
        Assign permissions for student taking instructor's course

        Do not check if user is taking the course.
        :param user: User instance of a student
        """
        assign_four_level_perm('core.view_instructor_base', user, self)

    def remove_perms_for_course_stu(self, user):
        """
        Remove permissions for student taking instructor's course

        Do not check if user is taking the course.
        :param user: User instance of a student
        """
        if not self.is_giving_course_to(user.student):
            remove_perm('core.view_instructor_base', user, self)

    def has_perms_for_course_stu(self, user):
        """
        Check if user has permissions for student taking instructor's course.

        Do not check if user is taking the course.
        :param user: User instance of student
        :return: `True` if has, or `False`
        """
        return has_four_level_perm('core.view_instructor_base', user, self)

    # For instructors
    def assign_base_perms_for_instructor(self, user):
        """
        Assign permissions for instructor

        :param user: User instance of instructor
        """
        assign_four_level_perm('core.view_instructor_normal', user, self)

    def remove_base_perms_for_instructor(self, user):
        """
        Remove permissions for instructor

        :param user: User instance of an instructor
        """
        remove_perm('core.view_instructor_normal', user, self)

    def has_base_perms_for_instructor(self, user):
        """
        Check if `user` has permissions for instructor

        :param user: User instance of an instructor
        """
        return has_four_level_perm('core.view_instructor_normal', user, self)

    def assign_perms_for_course_inst(self, user):
        assign_four_level_perm('core.view_instructor_normal', user, self)

    def remove_perms_for_course_inst(self, user):
        remove_perm('core.view_instructor_normal', user, self)

    def has_perms_for_course_inst(self, user):
        return has_four_level_perm('core.view_instructor_normal', user, self)


@receiver(post_save, sender=Instructor)
def instructor_assign_perms(sender, **kwargs):
    """
    Assign some model perms to new instructor
    """
    instructor, created = kwargs['instance'], kwargs['created']

    user = instructor.user
    if created:
        # model perms
        # 1. instructor
        assign_perm('core.view_instructor', user)
        # 2. takes
        assign_perm('core.view_takes', user)
        assign_perm('core.change_takes', user)
        assign_perm('core.add_takes', user)
        assign_perm('core.delete_takes', user)
        # 3. course
        assign_perm('core.view_course', user)
        assign_perm('core.change_course', user)
        assign_perm('core.add_course', user)
        assign_perm('core.delete_course', user)
        # 4. student
        assign_perm('core.view_student', user)
        # 5. teaches
        assign_perm('core.view_teaches', user)
        assign_perm('core.add_teaches', user)
        assign_perm('core.delete_teaches', user)
        # 6. group
        assign_perm('core.view_group', user)
        assign_perm('core.change_group', user)
        assign_perm('core.add_group', user)
        assign_perm('core.delete_group', user)

        # object perms
        # 1. instructor itself
        assign_perm('core.view_instructor', user, instructor)
        # 2. courses
        for course in Course.objects.all():
            course.assign_base_perms_for_instructor(user)

        # other instructors
        for inst in Instructor.objects.exclude(pk=instructor.pk):
            inst.assign_base_perms_for_instructor(user)
            instructor.assign_base_perms_for_instructor(inst.user)

        # other students
        for stu in Student.objects.all():
            stu.assign_base_perms_for_instructor(user)


@receiver(post_delete, sender=Instructor)
def instructor_remove_perms(sender, **kwargs):
    instructor = kwargs['instance']
    user = instructor.user

    remove_perm('core.view_instructor', user)

    remove_perm('core.view_takes', user)
    remove_perm('core.change_takes', user)
    remove_perm('core.add_takes', user)
    remove_perm('core.delete_takes', user)

    remove_perm('core.view_course', user)
    remove_perm('core.change_course', user)
    remove_perm('core.add_course', user)
    remove_perm('core.delete_course', user)

    remove_perm('core.view_group', user)
    remove_perm('core.change_group', user)
    remove_perm('core.add_group', user)
    remove_perm('core.delete_group', user)

    remove_perm('core.view_student', user)

    remove_perm('core.view_instructor', user, instructor)

    for course in Course.objects.all():
        course.remove_base_perms_for_instructor(user)

    for inst in Instructor.objects.exclude(pk=instructor.pk):
        inst.remove_base_perms_for_instructor(user)
        instructor.remove_base_perms_for_instructor(inst.user)

    for stu in Student.objects.all():
        stu.remove_base_perms_for_instructor(user)


class InstructorContactInfo(ContactInfo):
    instructor = models.ForeignKey(Instructor, related_name='contact_infos')


class Teaches(ModelDiffMixin, models.Model):
    instructor = models.ForeignKey(Instructor, related_name='teaches')
    course = models.ForeignKey(Course, related_name='teaches')

    class Meta:
        verbose_name_plural = 'teaches'
        unique_together = (('instructor', 'course'), )
        permissions = (
            ('view_teaches', 'Can view teaches'),
            ('view_teaches_base', 'Can view teaches - base level'),
            ('view_teaches_normal', 'Can view teaches - normal level'),
            ('view_teaches_advanced', 'Can view teaches - advanced level'),
            ('change_teaches_base', 'Can change teaches - base level'),
            ('change_teaches_normal', 'Can change teaches - normal level'),
            ('change_teaches_advanced', 'Can change teaches - advanced level'),
        )

    def __str__(self):
        return '({inst})-({course})'.format(
            inst=str(self.instructor),
            course=str(self.course),
        )

    # Object permission related methods
    # -------------------------------------------------------------------------
    # Object permission handlers for users
    # ------------------------------------
    # Student
    def assign_perms_for_course_stu(self, user):
        assign_perm('core.view_teaches', user, self)

    def remove_perms_for_course_stu(self, user):
        remove_perm('core.view_teaches', user, self)

    def has_perms_for_course_stu(self, user):
        return user.has_perm('core.view_teaches', self)

    # Instructor
    def assign_perms_for_course_inst(self, user):
        assign_perm('core.view_teaches', user, self)
        assign_perm('core.delete_teaches', user, self)

    def remove_perms_for_course_inst(self, user):
        remove_perm('core.view_teaches', user, self)
        remove_perm('core.delete_teaches', user, self)

    def has_perms_for_course_inst(self, user):
        return (user.has_perm('core.view_teaches', self) and
                user.has_perm('core.delete_teaches', self))

    def assign_perms_for_other_course_inst(self, user):
        assign_perm('core.view_teaches', user, self)

    def remove_perms_for_other_course_inst(self, user):
        remove_perm('core.view_teaches', user, self)

    def has_perms_for_other_course_inst(self, user):
        return user.has_perm('core.view_teaches', self)

    # Object permission handlers for relationship
    # ------------------------------------
    # teaches-instructor relationship
    def assign_instructor_perms(self):
        inst = self.instructor
        course = self.course
        takes_list = course.takes.all()
        teaches_list = course.teaches.exclude(pk=self.pk)

        # instructor perms on teaches
        self.assign_perms_for_course_inst(inst.user)
        # instructor perms on course
        course.assign_perms_for_course_inst(inst.user)

        for takes in takes_list:
            student = takes.student
            # instructor perms on takes
            takes.assign_perms_for_course_inst(inst.user)
            # instructor perms on student, and vice versa
            student.assign_perms_for_course_inst(inst.user)
            inst.assign_perms_for_course_stu(student.user)

        # instructor perms on other course insts and their teaches,
        # and vice versa
        for teaches in teaches_list:
            course_inst = teaches.instructor

            teaches.assign_perms_for_other_course_inst(inst.user)
            self.assign_perms_for_other_course_inst(course_inst.user)

            course_inst.assign_perms_for_course_inst(inst.user)
            inst.assign_perms_for_course_inst(course_inst.user)

    def remove_instructor_perms(self, instructor):
        inst = instructor
        course = self.course
        takes_list = course.takes.all()
        teaches_list = course.teaches.exclude(pk=self.pk)

        # instructor perms on teaches
        self.remove_perms_for_course_inst(inst.user)
        # instructor perms on course
        course.remove_perms_for_course_inst(inst.user)

        for takes in takes_list:
            student = takes.student
            # instructor perms on takes
            takes.remove_perms_for_course_inst(inst.user)
            # instructor perms on student, and vice versa
            student.remove_perms_for_course_inst(inst.user)
            inst.remove_perms_for_course_stu(student.user)

        # instructor perms on other course insts and their teaches,
        # and vice versa
        for teaches in teaches_list:
            course_inst = teaches.instructor

            teaches.remove_perms_for_other_course_inst(inst.user)
            self.remove_perms_for_other_course_inst(course_inst.user)

            course_inst.remove_perms_for_course_inst(inst.user)
            inst.remove_perms_for_course_inst(course_inst.user)

    # teaches-course relationship
    def assign_course_perms(self):
        inst = self.instructor
        course = self.course
        takes_list = self.course.takes.all()

        # instructor perms on course
        course.assign_perms_for_course_inst(inst.user)

        for takes in takes_list:
            student = takes.student
            # instructor perms on takes
            takes.assign_perms_for_course_inst(inst.user)
            # student perms on teaches
            self.assign_perms_for_course_stu(student.user)
            # instructor perms on student and vice versa
            student.assign_perms_for_course_inst(inst.user)
            inst.assign_perms_for_course_stu(student.user)

    def remove_course_perms(self, course):
        inst = self.instructor
        takes_list = course.takes.all()

        # instructor perms on course
        course.remove_perms_for_course_inst(inst.user)

        for takes in takes_list:
            student = takes.student
            # instructor perms on takes
            takes.remove_perms_for_course_inst(inst.user)
            # student perms on teaches
            self.remove_perms_for_course_stu(student.user)
            # instructor perms on student and vice versa
            student.remove_perms_for_course_inst(inst.user)
            inst.remove_perms_for_course_stu(student.user)


@receiver(post_save, sender=Teaches)
def teaches_assign_perms(instance, created, **kwargs):
    teaches = instance
    if created:
        teaches.assign_course_perms()
        teaches.assign_instructor_perms()
    else:
        old_course_pk = teaches.get_old_field('course')
        old_instructor_pk = teaches.get_old_field('instructor')
        if old_course_pk:
            old_course = Course.objects.get(pk=old_course_pk)
            teaches.remove_course_perms(old_course)
            teaches.assign_course_perms()
        if old_instructor_pk:
            old_instructor = Instructor.objects.get(pk=old_instructor_pk)
            teaches.remove_instructor_perms(old_instructor)
            teaches.assign_instructor_perms()

    teaches.save_all_field_diff()


@receiver(post_delete, sender=Teaches)
def teaches_remove_perms(instance, **kwargs):
    teaches = instance
    teaches.remove_course_perms(teaches.course)
    teaches.remove_instructor_perms(teaches.instructor)


class GroupQuerySet(models.QuerySet):
    def has_student(self, student):
        return self.filter(Q(members=student) | Q(leader=student))


class GroupManager(models.Manager):
    pass


class Group(ModelDiffMixin, models.Model):

    number = models.CharField(
        verbose_name='group number',
        max_length=10,
        default='',
        blank=True,
    )
    name = models.CharField(
        verbose_name='group name',
        max_length=255,
        default='',
        blank=True,
    )
    course = models.ForeignKey(Course, related_name='groups')
    leader = models.ForeignKey(Student, related_name='leader_of')
    members = models.ManyToManyField(Student,
                                     related_name='member_of',
                                     through='GroupMembership',)

    objects = GroupManager.from_queryset(GroupQuerySet)()

    class Meta:
        permissions = (
            ('view_group', 'Can view group'),
            ('view_group_base', "Can view group, base level"),
            ('view_group_normal', "Can view group, normal level"),
            ('view_group_advanced', "Can view group, advanced level"),
            ('change_group_base', "Can change group, base level"),
            ('change_group_normal', "Can change group, normal level"),
            ('change_group_advanced', "Can change group, advanced level"),
        )

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
        if not self.number:
            return

        if not self.pk:  # created
            if self.number not in self.course.NUMBERS_LIST:
                raise ValidationError({'number': 'Number should be in the list.'})
            elif self.number in self.course.get_used_group_numbers():
                raise ValidationError({'number': 'Number already used.'})
        else:
            old_number = self.get_old_field('number')
            if not old_number:
                return
            if self.number not in self.course.NUMBERS_LIST:
                raise ValidationError({'number': 'Number should be in the list.'})
            elif self.number in self.course.get_used_group_numbers():
                raise ValidationError({'number': 'Number already used.'})

    def validate_leader(self):
        """
        Validate if `leader` takes `course`
        """
        if not self.leader.is_taking(self.course):
            raise ValidationError({'leader': 'Group leader does not take the course.'})

    def clean(self):
        self.validate_group_number()
        self.validate_leader()

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.number:
            # if number is empty, fill in default number
            self.number = self.course.get_next_group_number()

        super(Group, self).save(*args, **kwargs)

    # Object permission related methods
    # -------------------------------------------------------------------------
    # Object permission handler for users
    # Students
    def assign_perms_for_course_stu(self, user):
        assign_perm('core.view_group', user, self)

    def remove_perms_for_course_stu(self, user):
        remove_perm('core.view_group', user, self)

    def has_perms_for_course_stu(self, user):
        return user.has_perm('core.view_group', self)

    def assign_perms_for_leader(self, user):
        assign_four_level_perm('core.change_group_advanced', user, self)

    def remove_perms_for_leader(self, user):
        remove_perm('core.change_group_advanced', user, self)

    def has_perms_for_leader(self, user):
        return has_four_level_perm('core.change_group_advanced', user, self)

    # Instructors
    def assign_perms_for_course_inst(self, user):
        assign_perm('core.view_group', user, self)
        assign_four_level_perm('core.change_group_advanced', user, self)
        assign_perm('core.delete_group', user, self)

    def remove_perms_for_course_inst(self, user):
        remove_perm('core.view_group', user, self)
        remove_perm('core.change_group_advanced', user, self)
        remove_perm('core.delete_group', user, self)

    def has_perms_for_course_inst(self, user):
        return (user.has_perm('core.view_group', self) and
                has_four_level_perm('core.change_group_advanced', user, self) and
                user.has_perm('core.delete_group', self))

    # Object permission handlers for 12m relationship
    # ------------------------------------
    # Group leader relationship
    def assign_leader_perms(self):
        self.assign_perms_for_leader(self.leader.user)

    def remove_leader_perms(self):
        self.remove_perms_for_leader(self.leader.user)


@receiver(post_save, sender=Group)
def group_assign_perms(**kwargs):
    group, created = kwargs['instance'], kwargs['created']
    if created:
        # course student's perms on group
        for stu in group.course.students.all():
            group.assign_perms_for_course_stu(stu.user)

        # course inst's perms on group
        for inst in group.course.instructors.all():
            group.assign_perms_for_course_inst(inst.user)

        # group leader's perms on group
        group.assign_perms_for_leader(group.leader.user)

    else:
        old_leader_pk = group.get_old_field('leader')
        if old_leader_pk:
            old_leader = Student.objects.get(pk=old_leader_pk)
            group.remove_perms_for_leader(old_leader.user)

            group.assign_perms_for_leader(group.leader.user)

    group.save_all_field_diff()


@receiver(post_delete, sender=Group)
def group_remove_perms(**kwargs):
    group = kwargs['instance']

    # course student's perms on group
    for stu in group.course.students.all():
        group.remove_perms_for_course_stu(stu.user)

    # course inst's perms on group
    for inst in group.course.instructors.all():
        group.remove_perms_for_course_inst(inst.user)

    # group leader's perms on group
    group.remove_perms_for_leader(group.leader.user)


class GroupContactInfo(ContactInfo):
    group = models.ForeignKey(Group, related_name='contact_infos')


class GroupMembership(ModelDiffMixin, models.Model):
    group = models.ForeignKey(Group, related_name='group_memberships')
    student = models.ForeignKey(Student, related_name='group_memberships')

    class Meta:
        verbose_name_plural = 'group_membership'
        unique_together = (('group', 'student'), )
        permissions = (
            ('view_grp_membership', 'Can view grp_membership'),
            ('view_grp_membership_base', 'Can view grp_membership - base level'),
            ('view_grp_membership_normal', 'Can view grp_membership - normal level'),
            ('view_grp_membership_advanced', 'Can view grp_membership - advanced level'),
            ('change_grp_membership_base', 'Can change grp_membership - base level'),
            ('change_grp_membership_normal', 'Can change grp_membership - normal level'),
            ('change_grp_membership_advanced', 'Can change grp_membership - advanced level'),
        )

    def validate_student(self):
        """
        Student should take the group course and is not a member of any group.
        """
        if not self.group.course.is_taken_by(self.student):
            raise ValidationError({'student': "Student should take the group course."})
        if self.group.course.has_group_including(self.student):
            raise ValidationError({'student': "Student is already in a group."})

    def clean(self):
        self.validate_student()

    def save(self, *args, **kwargs):
        self.full_clean()
        super(GroupMembership, self).save(*args, **kwargs)


class CourseAssignment(models.Model):

    def get_default_deadline():
        return timezone.now() + datetime.timedelta(days=7)

    course = models.ForeignKey(Course, related_name='assignments')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    deadline_dtm = models.DateTimeField(
        default=get_default_deadline,
        verbose_name='deadline',
    )
    assigned_dtm = models.DateTimeField(
        default=timezone.now,
        verbose_name='assigned time',
    )
    grade_ratio = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal(0)),
            MaxValueValidator(Decimal(1.0)),
        ]
    )

    class Meta:
        verbose_name = "course assignment"
        verbose_name_plural = "course assignments"

    def __str__(self):
        return '{course}-#{no}-{title}'.format(
            no=self.no_in_course,
            title=self.title,
            course=self.course,
        )

    def save(self, *args, **kwargs):
        self.full_clean()
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


class Takes(ModelDiffMixin, models.Model):
    student = models.ForeignKey(Student, related_name='takes')
    course = models.ForeignKey(Course, related_name='takes')
    grade = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100), ]
    )

    class Meta:
        verbose_name_plural = 'takes'
        unique_together = (('student', 'course'), )
        permissions = (
            ('view_takes', 'Can view takes'),
            ('view_takes_base', 'Can view takes - base level'),
            ('view_takes_normal', 'Can view takes - normal level'),
            ('view_takes_advanced', 'Can view takes - advanced level'),
            ('change_takes_base', 'Can change takes - base level'),
            ('change_takes_normal', 'Can change takes - normal level'),
            ('change_takes_advanced', 'Can change takes - advanced level'),
        )

    def save(self, *args, **kwargs):
        self.full_clean()
        super(Takes, self).save(*args, **kwargs)

    def __str__(self):
        return '({stu})-({course})'.format(
            stu=str(self.student),
            course=str(self.course),
        )

    # Object permission related methods
    # -------------------------------------------------------------------------
    # Object permission handlers for users
    # ------------------------------------
    # Student
    def assign_perms_for_course_stu(self, user):
        assign_perm('core.view_takes', user, self)

    def remove_perms_for_course_stu(self, user):
        remove_perm('core.view_takes', user, self)

    def has_perms_for_course_stu(self, user):
        return user.has_perm('core.view_takes', self)

    def assign_perms_for_other_course_stu(self, user):
        assign_perm('core.view_takes_base', user, self)

    def remove_perms_for_other_course_stu(self, user):
        remove_perm('core.view_takes_base', user, self)

    def has_perms_for_other_course_stu(self, user):
        return has_four_level_perm('core.view_takes_base', user, self)

    # Instructor
    def assign_perms_for_course_inst(self, user):
        assign_perm('core.view_takes', user, self)
        assign_four_level_perm('core.change_takes_base', user, self)
        assign_perm('core.delete_takes', user, self)

    def remove_perms_for_course_inst(self, user):
        remove_perm('core.view_takes', user, self)
        remove_perm('core.change_takes_base', user, self)
        remove_perm('core.delete_takes', user, self)

    def has_perms_for_course_inst(self, user):
        return (user.has_perm('core.view_takes', self) and
                has_four_level_perm('core.change_takes_base', user, self) and
                user.has_perm('core.delete_takes', self))

    # Object permission handlers for relationship
    # ------------------------------------
    # takes-student relationship
    def assign_student_perms(self):
        """
        Assign permissions after a new student is bound to takes
        """
        student = self.student
        stu_user = self.student.user
        course = self.course
        teaches_list = self.course.teaches.all()
        takes_list = course.takes.exclude(pk=self.pk)

        # student perms on takes
        self.assign_perms_for_course_stu(stu_user)
        # student perms on course
        course.assign_perms_for_course_stu(stu_user)

        for teaches in teaches_list:
            inst = teaches.instructor
            # student perms on teaches
            teaches.assign_perms_for_course_stu(stu_user)
            # student perms on instructor
            student.assign_perms_for_course_inst(inst.user)
            # instructor perms on student
            inst.assign_perms_for_course_stu(stu_user)

        # student perms on other course students and their takes,
        # and vice versa
        for takes in takes_list:
            course_stu = takes.student

            self.assign_perms_for_other_course_stu(course_stu.user)
            takes.assign_perms_for_other_course_stu(stu_user)

            student.assign_perms_for_course_stu(course_stu.user)
            course_stu.assign_perms_for_course_stu(student.user)

    def remove_student_perms(self, student):
        """
        Remove permissions after takes is bound to new student

        :param student: old student
        """
        stu_user = student.user
        course = self.course
        teaches_list = course.teaches.all()
        takes_list = course.takes.exclude(pk=self.pk)

        # student perms on takes
        self.remove_perms_for_course_stu(stu_user)
        # student perms on course
        course.remove_perms_for_course_stu(stu_user)

        for teaches in teaches_list:
            # student view teaches
            teaches.remove_perms_for_course_stu(stu_user)
            # if student does not take any more instructor's course,
            # then remove
            inst = teaches.instructor
            student.remove_perms_for_course_inst(inst.user)
            inst.remove_perms_for_course_stu(stu_user)

        # student perms on other course students and their takes,
        # and vice versa
        for takes in takes_list:
            course_stu = takes.student

            self.remove_perms_for_other_course_stu(course_stu.user)
            takes.remove_perms_for_other_course_stu(stu_user)

            student.remove_perms_for_course_stu(course_stu.user)
            course_stu.remove_perms_for_course_stu(student.user)

    # takes-course relationship
    def assign_course_perms(self):
        """
        Assign permissions after a new course is bound to takes
        """
        student = self.student
        course = self.course
        teaches_list = self.course.teaches.all()

        # student perms on course
        course.assign_perms_for_course_stu(student.user)

        for teaches in teaches_list:
            inst = teaches.instructor
            # student view teaches
            teaches.assign_perms_for_course_stu(student.user)
            # instructor perms on takes
            self.assign_perms_for_course_inst(inst.user)
            # instructor perms on student, and vice versa
            student.assign_perms_for_course_inst(inst.user)
            inst.assign_perms_for_course_stu(student.user)

        # student perms on other students taking the course, and vice versa
        other_students_list = course.students.exclude(pk=student.pk)
        for stu in other_students_list:
            stu.assign_perms_for_course_stu(student.user)
            student.assign_perms_for_course_stu(stu.user)

    def remove_course_perms(self, course):
        """
        Remove permissions after takes is bound to new course.

        Assume student does not change.
        :param course: old course
        """
        student = self.student
        teaches_list = course.teaches.all()

        # student perms on course
        course.remove_perms_for_course_stu(student.user)

        for teaches in teaches_list:
            inst = teaches.instructor
            # student view teaches
            teaches.remove_perms_for_course_stu(student.user)
            # instructor perms on takes
            self.remove_perms_for_course_inst(inst.user)
            # instructor perms on student, and vice versa
            student.remove_perms_for_course_inst(inst.user)
            inst.remove_perms_for_course_stu(student.user)

        # student perms on other students taking the course, and vice versa
        other_students_list = course.students.exclude(pk=student.pk)
        for stu in other_students_list:
            stu.remove_perms_for_course_stu(student.user)
            student.remove_perms_for_course_stu(stu.user)


@receiver(post_save, sender=Takes)
def takes_assign_perms(sender, **kwargs):
    """
    Assign related perms after creation of takes object
    """
    takes, created = kwargs['instance'], kwargs['created']

    if created:
        # student perms
        takes.assign_student_perms()
        # instructor perms
        takes.assign_course_perms()
    else:
        old_course_pk = takes.get_old_field('course')
        old_stu_pk = takes.get_old_field('student')
        if old_course_pk:
            old_course = Course.objects.get(pk=old_course_pk)
            takes.remove_course_perms(old_course)
            takes.assign_course_perms()
        if old_stu_pk:
            old_stu = Student.objects.get(pk=old_stu_pk)
            takes.remove_student_perms(old_stu)
            takes.assign_student_perms()

    takes.save_all_field_diff()


@receiver(post_delete, sender=Takes)
def takes_remove_perms(sender, **kwargs):
    takes = kwargs['instance']
    takes.remove_course_perms(takes.course)
    takes.remove_student_perms(takes.student)


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
        for f in User._meta.get_fields()
        if f.one_to_one
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
    If the file is of invalid type, raise ValidationError
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
        if not(Student.objects.filter(s_id=str(int(row['s_id'])))):
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
