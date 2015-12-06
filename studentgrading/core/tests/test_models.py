# -*- coding: utf-8 -*-
import unittest

from test_plus.test import TestCase
from django.db.utils import IntegrityError

from . import factories
from studentgrading.core.models import (
    Group,
    get_role_of,
)


class UserTests(TestCase):

    def test_save(self):
        user1 = factories.UserFactory()
        stu1 = factories.StudentFactory(user=user1)
        with self.assertRaises(IntegrityError):
            factories.InstructorFactory(user=user1)


class StudentMethodTests(TestCase):

    def test_students(self):
        pass


class CourseMethodTests(TestCase):

    def test_get_next_group_number(self):
        course = factories.CourseFactory()
        self.assertEqual(course.get_next_group_number(), course.NUMBERS_LIST[0])
        factories.GroupFactory(course=course)
        self.assertEqual(course.get_next_group_number(), course.NUMBERS_LIST[1])


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

    @unittest.skipIf(True, 'test')
    def test_get_list_of_available_numbers(self):
        course = factories.CourseFactory()
        grp1 = factories.GroupFactory(course=course)
        grp2 = factories.GroupFactory(course=course)
        grp3 = factories.GroupFactory(course=course)
        self.assertEqual(grp1.number, Group.NUMBERS_LIST[0])
        self.assertEqual(grp2.number, Group.NUMBERS_LIST[1])
        self.assertEqual(grp3.number, Group.NUMBERS_LIST[2])

        grp4 = factories.GroupFactory()
        self.assertEqual(grp4.number, Group.NUMBERS_LIST[0])

        grp5 = factories.GroupFactory()
        self.assertEqual(grp5.number, Group.NUMBERS_LIST[0])

    def test_save(self):
        course = factories.CourseFactory()
        grp1 = factories.GroupFactory(course=course)
        self.assertEqual(grp1.number, course.NUMBERS_LIST[0])


class ModelTests(TestCase):

    @unittest.skipIf(True, 'no need')
    def test_user_related_model(self):
        user = factories.UserFactory(username='2012211165')
        student = factories.StudentFactory(user=user)
        instructor = factories.InstructorFactory(user=user)
        self.assertEqual(user.student, student)
        self.assertEqual(user.instructor, instructor)
        with self.assertRaises(IntegrityError):
            factories.InstructorFactory(user=user)

    def test_get_role_of(self):
        user = factories.UserFactory()
        self.assertEqual(get_role_of(user), None)

        instructor = factories.InstructorFactory(user=user)
        self.assertEqual(get_role_of(user), instructor)