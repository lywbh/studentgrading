# -*- coding: utf-8 -*-
import json
import random
from decimal import Decimal

import factory
from faker.providers import BaseProvider

from studentgrading.users.models import User
from studentgrading.core.models import (
    CourseAssignment, Course, UserProfile, Student, Instructor,
    Class, Takes, Teaches, Group, ContactInfoType, ContactInfo,
    StudentContactInfo, InstructorContactInfo, GroupContactInfo,
    GroupMembership,
)


# Fake providers
# ------------------------------------------------------------------------------
class CourseProvider(BaseProvider):
    def __init__(self, *args, **kwargs):
        super(CourseProvider, self).__init__(*args, **kwargs)
        import os
        with open(os.path.dirname(os.path.abspath(__file__)) + '/courses.json') as f:
            self.courses = json.load(f)

    def course_title(self):
        return self.courses[random.randint(0, len(self.courses) - 1)]['title']

    def course_year(self):
        return self.courses[random.randint(0, len(self.courses) - 1)]['year']

factory.Faker.add_provider(CourseProvider)


# Factories
# ------------------------------------------------------------------------------
class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: 'user#{0}'.format(n))
    password = '211165'

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        manager = cls._get_manager(model_class)
        return manager.create_user(*args, **kwargs)


class UserProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserProfile
        abstract = True

    user = factory.SubFactory(UserFactory)
    name = factory.Faker('name')
    sex = factory.Iterator(
        [UserProfile.SEX_CHOICES[0][0], UserProfile.SEX_CHOICES[1][0]]
    )


class ContactInfoTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ContactInfoType

    type_string = factory.Iterator(['QQ', 'Email', 'Phone'])


class ContactInfoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ContactInfo
        abstract = True

    info_type = factory.SubFactory(ContactInfoTypeFactory)

    @factory.lazy_attribute_sequence
    def content(self, n):
        type_str = self.info_type.type_string
        if type_str.lower() == 'qq':
            return '{0}'.format(random.randint(100000, 999999999))
        elif type_str.lower() == 'email':
            from faker import Factory
            return Factory.create().free_email()
        elif type_str.lower() == 'phone':
            from faker import Factory
            return Factory.create(locale='zh_CN').phone_number()
        else:
            return 'contact#{0}'.format(n)


class ClassFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Class

    class_id = factory.Sequence(lambda n: '20122113{0:0>2}'.format(n))


class CourseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Course

    title = factory.Faker('course_title')
    year = factory.Faker('course_year')
    semester = factory.Iterator(
        [Course.SEMESTER_CHOICES[0][0], Course.SEMESTER_CHOICES[1][0]]
    )

    @factory.post_generation
    def assignments(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for assignmt in extracted:
                self.assignments.add(assignmt)


class StudentFactory(UserProfileFactory):
    class Meta:
        model = Student

    s_id = factory.Sequence(lambda n: '2012211{0:0>3}'.format(n))
    s_class = factory.SubFactory(ClassFactory)


class StudentContactInfoFactory(ContactInfoFactory):
    class Meta:
        model = StudentContactInfo

    student = factory.SubFactory(StudentFactory)


class TakesFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Takes

    student = factory.SubFactory(StudentFactory)
    course = factory.SubFactory(CourseFactory)


class StudentTakesCourseFactory(StudentFactory):
    courses = factory.RelatedFactory(TakesFactory, 'student')


class InstructorFactory(UserProfileFactory):
    class Meta:
        model = Instructor

    inst_id = factory.Sequence(lambda n: '1120{0:0>3}'.format(n))


class TeachesFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Teaches

    instructor = factory.SubFactory(InstructorFactory)
    course = factory.SubFactory(CourseFactory)


class InstructorTeachesCourseFactory(InstructorFactory):
    courses = factory.RelatedFactory(TeachesFactory, 'instructor')


class CourseAssignmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CourseAssignment

    course = factory.SubFactory(CourseFactory)
    title = factory.LazyAttributeSequence(
        lambda o, n: '{0}#{1}'.format(o.course.title, n)
    )
    grade_ratio = Decimal('0.{0:0>2}'.format(random.randint(10, 29)))


class GroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Group

    name = factory.Faker('word')
    course = factory.SubFactory(CourseFactory)
    leader = factory.SubFactory(StudentTakesCourseFactory,
                                courses__course=factory.SelfAttribute('..course'))

    @factory.post_generation
    def members(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for member in extracted:
                GroupMembership.objects.create(group=self, student=member)


class GroupMembershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GroupMembership

    student = factory.SubFactory(StudentFactory)
    group = factory.SubFactory(GroupFactory)