# -*- coding: utf-8 -*-
from test_plus.test import TestCase
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.test.client import RequestFactory

import environ
from . import factories
from studentgrading.core.models import (
    get_role_of, ContactInfoType, import_student,
)
from ..models import (
    Course, Student,
)


class UserTests(TestCase):

    def test_save(self):
        user1 = factories.UserFactory()
        # user uniqueness
        factories.StudentFactory(user=user1)
        with self.assertRaises(ValidationError):
            factories.InstructorFactory(user=user1)

        # name not empty
        with self.assertRaises(ValidationError):
            factories.StudentFactory(name='')

    def test_clean(self):
        from studentgrading.core.models import Student, Instructor
        user1 = factories.UserFactory()
        # name not empty
        stu1 = Student(user=user1, s_id='2012211165', s_class=factories.ClassFactory())
        with self.assertRaises(ValidationError):
            stu1.full_clean()

        # user uniqueness
        inst1 = Instructor(user=user1, inst_id='1043678')
        with self.assertRaises(ValidationError):
            inst1.full_clean()


class ContactInfoTypeTests(TestCase):

    def test_save(self):
        # type str not empty
        with self.assertRaises(ValidationError):
            factories.ContactInfoTypeFactory(type_string='')

        # type str uniqueness
        factories.ContactInfoTypeFactory(type_string='QQ')
        with self.assertRaises(ValidationError):
            factories.ContactInfoTypeFactory(type_string='qq')

    def test_clean(self):
        # type str uniqueness
        from studentgrading.core.models import ContactInfoType
        factories.ContactInfoTypeFactory(type_string='QQ')
        cont1 = ContactInfoType(type_string='qq')
        with self.assertRaises(ValidationError):
            cont1.full_clean()

        # type str not empty
        cont1.type_string = ''
        with self.assertRaises(ValidationError):
            cont1.full_clean()


class ContactInfoTests(TestCase):

    def test_save(self):
        with self.assertRaises(ValidationError):
            factories.StudentContactInfoFactory(content='')


class ClassTests(TestCase):

    def test_save(self):
        with self.assertRaises(ValidationError):
            factories.ClassFactory(class_id='')


class StudentMethodTests(TestCase):

    def test_save(self):
        with self.assertRaises(ValidationError) as cm:
            factories.StudentFactory(s_id='')
        self.assertTrue(cm.exception.message_dict.get('s_id'))

    def test_get_course(self):
        stu1 = factories.StudentFactory()
        cs1 = factories.CourseFactory()
        cs2 = factories.CourseFactory()

        factories.TakesFactory(student=stu1, course=cs1)
        factories.TakesFactory(student=stu1, course=cs2)

        self.assertEqual(stu1.get_course(cs1.pk), cs1)
        self.assertEqual(stu1.get_course(cs1.pk + 5), None)

    def test_get_group(self):
        stu1 = factories.StudentFactory()
        cs1 = factories.CourseFactory()
        factories.TakesFactory(student=stu1, course=cs1)
        grp1 = factories.GroupFactory(course=cs1, leader=stu1)

        self.assertEqual(stu1.get_group(cs1.pk), grp1)

        stu2 = factories.StudentFactory()
        factories.TakesFactory(student=stu2, course=cs1)
        grp1.members.add(stu2)

        self.assertEqual(stu2.get_group(cs1.pk), grp1)

        with self.assertRaises(ValidationError):
            self.assertEqual(factories.StudentFactory().get_group(cs1.pk), None)

        with self.assertRaises(ValidationError):
            stu1.get_group(factories.CourseFactory().pk)


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
        with self.assertRaises(ValidationError) as cm:
            factories.GroupFactory(course=course, number=grp1.number)
        self.assertTrue(cm.exception.message_dict.get('number'))
        self.assertEqual(course.get_next_group_number(), course.NUMBERS_LIST[2])

        with self.assertRaises(ValidationError) as cm:
            factories.GroupFactory(course=course, number='1')
        self.assertTrue(cm.exception.message_dict.get('number'))

        # delete and add
        grp1.delete()
        grp3 = factories.GroupFactory(course=course)
        self.assertEqual(grp3.number, course.NUMBERS_LIST[0])

    def test_clean(self):
        # check number
        from studentgrading.core.models import Group
        grp1 = Group(name='hello_world', course=factories.CourseFactory())
        grp1.number = '1'
        with self.assertRaises(ValidationError) as cm:
            grp1.full_clean()
        self.assertTrue(cm.exception.message_dict.get('number'))

        grp1.number = 'B'
        grp1.save()
        grp2 = Group(name='hello_china', course=grp1.course)
        grp2.number = 'B'
        with self.assertRaises(ValidationError) as cm:
            grp2.full_clean()
        self.assertTrue(cm.exception.message_dict.get('number'))


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

    def test_import_student(self):
        factories.ClassFactory(class_id='301')
        rf = RequestFactory()
        with open(str((environ.Path(__file__) - 1).path('stu.xls')), 'rb') as f:
            count = import_student(rf.post('anything', {'file': f}).FILES['file'])
        self.assertEqual(count, 10)

        with open(str((environ.Path(__file__) - 1).path('stu.xls')), 'rb') as f:
            count = import_student(rf.post('anything', {'file': f}).FILES['file'])
        self.assertEqual(count, 0)


class CourseMethodTests(TestCase):

    def test_save(self):
        # not empty fields
        with self.assertRaises(ValidationError) as cm:
            factories.CourseFactory(title='')
        self.assertTrue(cm.exception.message_dict.get('title'))
        with self.assertRaises(ValidationError) as cm:
            factories.CourseFactory(semester='')
        self.assertTrue(cm.exception.message_dict.get('semester'))

        # check group size
        with self.assertRaises(ValidationError) as cm:
            factories.CourseFactory(min_group_size=2, max_group_size=1)
        self.assertTrue(cm.exception.message_dict.get('min_group_size'))
        self.assertTrue(cm.exception.message_dict.get('max_group_size'))

        try:
            factories.CourseFactory(min_group_size=2, max_group_size=2)
        except Exception as e:
            self.fail(str(e))

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

        course.add_assignment(title="ass1", grade_ratio=0.1)

        self.assertEqual(course.assignments.count(),1)

    def test_get_students_not_in_group(self):
        cs1 = factories.CourseFactory()

        stu1 = factories.StudentTakesCourseFactory(courses__course=cs1)
        stu2 = factories.StudentTakesCourseFactory(courses__course=cs1)
        stu3 = factories.StudentTakesCourseFactory(courses__course=cs1)

        factories.GroupFactory(course=cs1, members=(stu1, stu2))

        self.assertQuerysetEqual(
            cs1.get_students_not_in_any_group(),
            [repr(stu3)]
        )


class CourseAssignmentTests(TestCase):

    def test_clean(self):
        from studentgrading.core.models import CourseAssignment
        crs1 = CourseAssignment(
            course=factories.CourseFactory(),
            title='',
            grade_ratio=0.1,
        )
        with self.assertRaises(ValidationError) as cm:
            crs1.full_clean()
        self.assertIn('title', cm.exception.message_dict)

    def test_save(self):
        # empty title
        with self.assertRaises(ValidationError) as cm:
            factories.CourseAssignmentFactory(title='')
        self.assertIn('title', cm.exception.message_dict)

        # invalid grade ratio
        with self.assertRaises(ValidationError) as cm:
            factories.CourseAssignmentFactory(grade_ratio=0)
        self.assertIn('grade_ratio', cm.exception.message_dict)

        with self.assertRaises(ValidationError) as cm:
            factories.CourseAssignmentFactory(grade_ratio=-0.1)
        self.assertIn('grade_ratio', cm.exception.message_dict)

        with self.assertRaises(ValidationError) as cm:
            factories.CourseAssignmentFactory(grade_ratio=1.1)
        self.assertIn('grade_ratio', cm.exception.message_dict)


class InstructorMethodTests(TestCase):

    def test_add_course(self):
        instructor = factories.InstructorFactory()
        self.assertEqual(instructor.courses.count(), 0)

    def test_save(self):
        with self.assertRaises(ValidationError) as cm:
            factories.InstructorFactory(inst_id='')
        self.assertTrue(cm.exception.message_dict.get('inst_id'))

    def test_import_student_takes(self):
        inst1 = factories.InstructorFactory()
        cs1 = factories.CourseFactory()
        factories.TeachesFactory(instructor=inst1, course=cs1)

        rf = RequestFactory()
        factories.ClassFactory(class_id='301')
        f = open(str((environ.Path(__file__) - 1).path('stu.xls')), 'rb')
        count = inst1.import_student_takes(rf.post('anything', {'file': f}).FILES['file'], cs1.pk)
        self.assertEqual(count, 0)

        f.seek(0)
        import_student(rf.post('anything', {'file': f}).FILES['file'])

        factories.TakesFactory(student=Student.objects.all()[0], course=cs1)
        factories.TakesFactory(student=Student.objects.all()[1], course=cs1)
        f.seek(0)
        count = inst1.import_student_takes(rf.post('anything', {'file': f}).FILES['file'], cs1.pk)
        self.assertEqual(count, 8)
        self.assertEqual(cs1.takes.count(), 10)


class TakesTests(TestCase):

    def test_save(self):
        # invalid grade
        with self.assertRaises(ValidationError) as cm:
            factories.TakesFactory(grade=-1)
        self.assertIn('grade', cm.exception.message_dict)

        with self.assertRaises(ValidationError) as cm:
            factories.TakesFactory(grade=101)
        self.assertIn('grade', cm.exception.message_dict)
