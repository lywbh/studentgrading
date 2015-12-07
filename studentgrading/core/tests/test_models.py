# -*- coding: utf-8 -*-
from test_plus.test import TestCase
from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse

from . import factories
from studentgrading.core.models import (
    get_role_of,
)


class UserTests(TestCase):

    def test_save(self):
        user1 = factories.UserFactory()
        factories.StudentFactory(user=user1)
        with self.assertRaises(IntegrityError):
            factories.InstructorFactory(user=user1)


class StudentMethodTests(TestCase):

    def test_students(self):
        pass


class CourseAssignmentMethodTests(TestCase):

    def test_get_no_in_course(self):
        course = factories.CourseFactory()
        ca1 = factories.CourseAssignmentFactory(course=course)
        ca2 = factories.CourseAssignmentFactory(course=course)
        ca3 = factories.CourseAssignmentFactory(course=course)
        self.assertEqual(ca1.get_no_in_course(), 1)
        self.assertEqual(ca2.get_no_in_course(), 2)
        self.assertEqual(ca3.get_no_in_course(), 3)


class GroupMethodTests(TestCase):

    def test_save(self):
        # normal add
        course = factories.CourseFactory()
        grp1 = factories.GroupFactory(course=course)
        self.assertEqual(grp1.number, course.NUMBERS_LIST[0])
        grp2 = factories.GroupFactory(course=course)
        self.assertEqual(grp2.number, course.NUMBERS_LIST[1])

        # provide custom number
        with self.assertRaises(ValidationError):
            factories.GroupFactory(course=course, number=grp1.number)
        self.assertEqual(course.get_next_group_number(), course.NUMBERS_LIST[2])
        with self.assertRaises(ValidationError):
            factories.GroupFactory(course=course, number='1')

        # delete and add
        grp1.delete()
        grp3 = factories.GroupFactory(course=course)
        self.assertEqual(grp3.number, course.NUMBERS_LIST[0])


class ModelTests(TestCase):

    def test_get_role_of(self):
        user = factories.UserFactory()
        self.assertEqual(get_role_of(user), None)

        instructor = factories.InstructorFactory(user=user)
        self.assertEqual(get_role_of(user), instructor)

        # test login and retrieve user
        user1 = factories.UserFactory(username='test1234', password='abcd1234')
        instructor1 = factories.InstructorFactory(user=user1)
        self.post(
            reverse('users:login'),
            data={'username': 'test1234', 'password': 'abcd1234'},
        )
        self.get(
            reverse('users:login'),
        )

        from django.contrib.auth import authenticate
        from studentgrading.users.models import User
        User.objects.create_superuser(username='admin', password='sep2015')
        user2 = authenticate(username='admin', password='sep2015')
        print(get_role_of(user2))


class CourseMethodTests(TestCase):

    def test_get_next_group_number(self):
        course = factories.CourseFactory()
        self.assertEqual(course.get_next_group_number(), course.NUMBERS_LIST[0])
        factories.GroupFactory(course=course)
        self.assertEqual(course.get_next_group_number(), course.NUMBERS_LIST[1])

    def test_add_group(self):
        course = factories.CourseFactory()
        stu = factories.StudentFactory()
        self.assertEqual(course.group_set.count(), 0)

        course.add_group(
            members=(stu,),
            name='Hello_world',
            leader=factories.StudentFactory(),
        )
        self.assertEqual(course.group_set.count(), 1)

    def test_add_assignemnt(self):
        course = factories.CourseFactory()
        self.assertEqual(course.assignments.count(),0)

        course.add_assignment(title="ass1",grade_ratio=0.1)

        self.assertEqual(course.assignments.count(),1)
    

class InstructorMethodTests(TestCase):

    def test_add_course(self):
        instructor = factories.InstructorFactory()
        self.assertEqual(instructor.courses.count(), 0)

        instructor.add_course(title="DS")

        self.assertEqual(instructor.courses.count(), 1)

