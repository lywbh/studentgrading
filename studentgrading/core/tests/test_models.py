# -*- coding: utf-8 -*-
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.core.urlresolvers import reverse
from django.test.client import RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from django.contrib.auth import get_user_model, authenticate
from django.db.models.signals import post_save

from django.test import TestCase
from guardian.shortcuts import remove_perm, assign_perm
import environ
from . import factories
from ..models import (
    Course, Student, Instructor, ContactInfoType, import_student, get_role_of,
    assign_four_level_perm, has_four_level_perm
)

User = get_user_model()


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

        with self.assertRaises(ValueError):
            factories.StudentFactory(s_class=None)

        cls = factories.ClassFactory()
        stu = factories.StudentFactory()
        self.assertEqual(cls.students.count(), 0)
        cls.students.add(stu)
        self.assertEqual(stu.s_class, cls)
        cls.students = [factories.StudentFactory()]
        self.assertEqual(cls.students.count(), 2)

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
        factories.GroupMembershipFactory(group=grp1, student=stu2)

        self.assertEqual(stu2.get_group(cs1.pk), grp1)

        with self.assertRaises(ValidationError):
            self.assertEqual(factories.StudentFactory().get_group(cs1.pk), None)

        with self.assertRaises(ValidationError):
            stu1.get_group(factories.CourseFactory().pk)

    def test_is_classmate_of(self):
        stu1 = factories.StudentFactory()
        stu2 = factories.StudentFactory(s_class=stu1.s_class)
        stu3 = factories.StudentFactory()

        self.assertFalse(stu1.is_classmate_of(stu1))
        self.assertFalse(stu3.is_classmate_of(stu1))
        self.assertFalse(stu1.is_classmate_of(stu3))
        self.assertTrue(stu1.is_classmate_of(stu2))
        self.assertTrue(stu2.is_classmate_of(stu1))

    def test_is_taking_same_course(self):
        course = factories.CourseFactory()
        stu1 = factories.StudentTakesCourseFactory(courses__course=course)
        stu2 = factories.StudentTakesCourseFactory(courses__course=course)
        stu3 = factories.StudentFactory()

        self.assertFalse(stu1.is_taking_same_course_with(stu1))
        self.assertFalse(stu3.is_taking_same_course_with(stu1))
        self.assertFalse(stu1.is_taking_same_course_with(stu3))
        self.assertTrue(stu2.is_taking_same_course_with(stu1))
        self.assertTrue(stu1.is_taking_same_course_with(stu2))


class StudentManagerTests(TestCase):

    def setUp(self):
        self.mang = Student.objects

    def test_takes_courses(self):
        course1 = factories.CourseFactory()
        course2 = factories.CourseFactory()
        course3 = factories.CourseFactory()
        for i in range(10):
            factories.StudentTakesCourseFactory(courses__course=course1)
            factories.StudentTakesCourseFactory(courses__course=course2)
            factories.StudentTakesCourseFactory(courses__course=course3)

        self.assertEqual(self.mang.takes_courses([course1]).count(), 10)
        self.assertEqual(self.mang.takes_courses([course1, course2]).count(), 20)
        self.assertEqual(self.mang.takes_courses([course1, course2, course3]).count(),
                         30)
        self.assertEqual(self.mang.takes_courses([course1]).takes_courses([course2]).count(),
                         0)

    def test_in_group_of(self):
        course1 = factories.CourseFactory()
        for i in range(3):
            factories.StudentTakesCourseFactory(courses__course=course1)

        stu1 = factories.StudentTakesCourseFactory(courses__course=course1)
        stu2 = factories.StudentTakesCourseFactory(courses__course=course1)
        group1 = factories.GroupFactory(course=course1, leader=stu1)
        factories.GroupMembershipFactory(student=stu2, group=group1)

        self.assertEqual(Student.objects.in_any_group_of(course1).count(), 2)

    def test_not_in_group_of(self):
        course1 = factories.CourseFactory()
        for i in range(3):
            factories.StudentTakesCourseFactory(courses__course=course1)

        stu1 = factories.StudentTakesCourseFactory(courses__course=course1)
        stu2 = factories.StudentTakesCourseFactory(courses__course=course1)
        group1 = factories.GroupFactory(course=course1, leader=stu1)
        factories.GroupMembershipFactory(student=stu2, group=group1)

        self.assertEqual(Student.objects.not_in_any_group_of(course1).count(), 3)


class StudentPermsTests(TestCase):
    def test_has_perms_for_course_stu(self):
        stu1 = factories.StudentFactory()
        stu2 = factories.StudentFactory()
        assign_perm('core.view_student_base', stu2.user, stu1)
        self.assertTrue(stu1.has_perms_for_course_stu(stu2.user))

    def test_assign_perms_for_course_stu(self):
        stu1 = factories.StudentFactory()
        stu2 = factories.StudentFactory()
        stu1.assign_perms_for_course_stu(stu2.user)
        self.assertTrue(stu1.has_perms_for_course_stu(stu2.user))

    def test_remove_perms_for_course_stu(self):
        stu1 = factories.StudentFactory()
        stu2 = factories.StudentFactory()
        stu1.assign_perms_for_course_stu(stu2.user)
        stu1.remove_perms_for_course_stu(stu2.user)
        self.assertFalse(stu1.has_perms_for_course_stu(stu2.user))

        assign_perm('core.view_student_normal', stu2.user, stu1)
        stu1.remove_perms_for_course_stu(stu2.user)
        self.assertTrue(stu1.has_perms_for_course_stu(stu2.user))

        remove_perm('core.view_student_normal', stu2.user, stu1)
        assign_perm('core.view_student_advanced', stu2.user, stu1)
        stu1.remove_perms_for_course_stu(stu2.user)
        self.assertTrue(stu1.has_perms_for_course_stu(stu2.user))

        remove_perm('core.view_student_advanced', stu2.user, stu1)
        assign_perm('core.view_student', stu2.user, stu1)
        stu1.remove_perms_for_course_stu(stu2.user)
        self.assertTrue(stu1.has_perms_for_course_stu(stu2.user))

    def test_has_perms_for_classmate(self):
        stu1 = factories.StudentFactory()
        stu2 = factories.StudentFactory()
        assign_perm('core.view_student_normal', stu2.user, stu1)
        self.assertTrue(stu1.has_perms_for_classmate(stu2.user))

    def test_assign_perms_for_classmate(self):
        stu1 = factories.StudentFactory()
        stu2 = factories.StudentFactory()
        stu1.assign_perms_for_classmate(stu2.user)
        self.assertTrue(stu1.has_perms_for_classmate(stu2.user))

    def test_remove_perms_for_classmate(self):
        stu1 = factories.StudentFactory()
        stu2 = factories.StudentFactory()
        stu1.assign_perms_for_classmate(stu2.user)
        stu1.remove_perms_for_classmate(stu2.user)
        self.assertFalse(stu1.has_perms_for_classmate(stu2.user))

        assign_perm('core.view_student_advanced', stu2.user, stu1)
        stu1.remove_perms_for_classmate(stu2.user)
        self.assertTrue(stu1.has_perms_for_classmate(stu2.user))

        remove_perm('core.view_student_advanced', stu2.user, stu1)
        assign_perm('core.view_student', stu2.user, stu1)
        stu1.remove_perms_for_classmate(stu2.user)
        self.assertTrue(stu1.has_perms_for_classmate(stu2.user))

    def test_has_base_perms_for_instructor(self):
        stu1 = factories.StudentFactory()
        inst1 = factories.InstructorFactory()
        assign_perm('core.view_student_advanced', inst1.user, stu1)
        self.assertTrue(stu1.has_base_perms_for_instructor(inst1.user))

    def test_assign_base_perms_for_instructor(self):
        stu1 = factories.StudentFactory()
        inst1 = factories.InstructorFactory()
        stu1.assign_base_perms_for_instructor(inst1.user)
        self.assertTrue(stu1.has_base_perms_for_instructor(inst1.user))

    def test_remove_base_perms_for_instructor(self):
        stu1 = factories.StudentFactory()
        inst1 = factories.InstructorFactory()
        stu1.assign_base_perms_for_instructor(inst1.user)
        stu1.remove_base_perms_for_instructor(inst1.user)
        self.assertFalse(stu1.has_base_perms_for_instructor(inst1.user))

    def test_has_perms_for_course_inst(self):
        stu1 = factories.StudentFactory()
        inst1 = factories.InstructorFactory()
        assign_perm('core.view_student_advanced', inst1.user, stu1)
        self.assertTrue(stu1.has_perms_for_course_inst(inst1.user))

    def test_assign_perms_for_course_inst(self):
        stu1 = factories.StudentFactory()
        inst1 = factories.InstructorFactory()
        stu1.assign_perms_for_course_inst(inst1.user)
        self.assertTrue(stu1.has_perms_for_course_inst(inst1.user))

    def test_remove_perms_for_course_inst(self):
        stu1 = factories.StudentFactory()
        inst1 = factories.InstructorFactory()
        stu1.assign_perms_for_course_inst(inst1.user)
        stu1.remove_perms_for_course_inst(inst1.user)
        self.assertTrue(stu1.has_perms_for_course_inst(inst1.user))

        assign_perm('core.view_student_advanced', inst1.user, stu1)
        stu1.remove_perms_for_course_inst(inst1.user)
        self.assertTrue(stu1.has_perms_for_course_inst(inst1.user))

    def test_perms(self):
        stu = factories.StudentFactory()
        for i in range(10):
            factories.StudentFactory(s_class=stu.s_class)
            factories.InstructorFactory()
        # test model perms
        self.assertTrue(stu.user.has_perm('core.view_student'))
        self.assertTrue(stu.user.has_perm('core.view_takes'))
        self.assertTrue(stu.user.has_perm('core.view_course'))
        self.assertTrue(stu.user.has_perm('core.view_instructor'))
        self.assertTrue(stu.user.has_perm('core.view_teaches'))
        # test obj perms
        self.assertTrue(stu.user.has_perm('core.view_student', stu))

        for inst in Instructor.objects.all():
            self.assertTrue(stu.has_base_perms_for_instructor(inst.user))

        stu.delete()
        user = User.objects.get(pk=stu.user.pk)     # remove the cache
        # test perms after deletion
        self.assertFalse(user.has_perm('core.view_student'))
        self.assertFalse(user.has_perm('core.view_takes'))
        self.assertFalse(user.has_perm('core.view_course'))
        self.assertFalse(user.has_perm('core.view_instructor'))
        self.assertFalse(user.has_perm('core.view_teaches'))

        self.assertFalse(user.has_perm('core.view_student', stu))

        for inst in Instructor.objects.all():
            self.assertFalse(stu.has_base_perms_for_instructor(inst.user))

    def test_class_perms(self):
        cls1 = factories.ClassFactory()
        stu1 = factories.StudentFactory(s_class=cls1)
        stu2 = factories.StudentFactory(s_class=cls1)
        stu3 = factories.StudentFactory(s_class=cls1)

        # check classmates perm
        self.assertTrue(stu1.has_perms_for_classmate(stu2.user))
        self.assertTrue(stu1.has_perms_for_classmate(stu3.user))
        self.assertTrue(stu2.has_perms_for_classmate(stu1.user))
        self.assertTrue(stu2.has_perms_for_classmate(stu3.user))
        self.assertTrue(stu3.has_perms_for_classmate(stu1.user))
        self.assertTrue(stu3.has_perms_for_classmate(stu2.user))

        cls2 = factories.ClassFactory()
        stu4 = factories.StudentFactory(s_class=cls2)
        stu1.s_class = cls2
        stu1.save()
        # check perms after change class
        self.assertTrue(stu1.has_perms_for_classmate(stu4.user))
        self.assertTrue(stu4.has_perms_for_classmate(stu1.user))
        self.assertFalse(stu1.has_perms_for_classmate(stu2.user))
        self.assertFalse(stu1.has_perms_for_classmate(stu3.user))
        self.assertFalse(stu2.has_perms_for_classmate(stu1.user))
        self.assertFalse(stu3.has_perms_for_classmate(stu1.user))

        # check perms after deleting
        stu1.delete()
        self.assertFalse(stu1.has_perms_for_classmate(stu1.user))
        self.assertFalse(stu1.has_perms_for_classmate(stu4.user))
        self.assertFalse(stu1.has_perms_for_classmate(stu1.user))

    def test_classmate_perms(self):
        cls1 = factories.ClassFactory()
        stu_cls1_list = []
        for i in range(10):
            stu_cls1_list.append(factories.StudentFactory(s_class=cls1))
            factories.StudentFactory()

        for stu in stu_cls1_list:
            for clsmt in cls1.students.exclude(pk=stu.pk):
                self.assertTrue(stu.has_perms_for_classmate(clsmt.user))
                self.assertTrue(clsmt.has_perms_for_classmate(stu.user))


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
        # use default number
        grp = factories.GroupFactory(number='')
        self.assertEqual(grp.number, grp.course.NUMBERS_LIST[0])

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

    def test_number(self):
        # check number
        course1 = factories.CourseFactory()
        grp1 = factories.GroupFactory(course=course1)
        grp1.number = '1'
        with self.assertRaises(ValidationError) as cm:
            grp1.full_clean()
        self.assertTrue(cm.exception.message_dict.get('number'))

        grp1.number = 'B'
        grp1.save()
        grp2 = factories.GroupFactory(course=course1)
        grp2.number = 'B'
        with self.assertRaises(ValidationError) as cm:
            grp2.full_clean()
        self.assertTrue(cm.exception.message_dict.get('number'))

    def test_leader(self):
        stu1 = factories.StudentFactory()
        course1 = factories.CourseFactory()

        # student not taking the course can not join group
        with self.assertRaises(ValidationError) as cm:
            factories.GroupFactory(course=course1, leader=stu1)
        self.assertIn('leader', cm.exception.message_dict)

        # after taking, student can
        factories.TakesFactory(student=stu1, course=course1)
        group1 = factories.GroupFactory(course=course1, leader=stu1)
        self.assertTrue(course1.groups.filter(pk=group1.pk).exists())


class GroupMembershipMethodTests(TestCase):

    def test_save(self):
        course1 = factories.CourseFactory()
        group1 = factories.GroupFactory(course=course1)
        stu1 = factories.StudentFactory()
        stu2 = factories.StudentTakesCourseFactory(courses__course=course1)

        factories.GroupMembershipFactory(student=stu2, group=group1)

        with self.assertRaises(ValidationError) as cm:
            factories.GroupMembershipFactory(student=stu1, group=group1)
        self.assertIn('student', cm.exception.message_dict)

        with self.assertRaises(ValidationError) as cm:
            factories.GroupMembershipFactory(student=stu1, group=group1)
        self.assertIn('student', cm.exception.message_dict)

        group2 = factories.GroupFactory(course=course1)
        with self.assertRaises(ValidationError) as cm:
            factories.GroupMembershipFactory(student=stu1, group=group2)
        self.assertIn('student', cm.exception.message_dict)


class GroupPermsTests(TestCase):

    def test_student_perms(self):
        course1 = factories.CourseFactory()
        group1 = factories.GroupFactory(course=course1)
        stu1 = factories.StudentTakesCourseFactory(courses__course=course1)
        stu2 = factories.StudentFactory()

        # normal student has no perms
        self.assertFalse(group1.has_perms_for_course_stu(stu2.user))

        # course student has perms
        self.assertTrue(group1.has_perms_for_course_stu(stu1.user))

        # group leader has perms
        self.assertTrue(group1.has_perms_for_leader(group1.leader.user))

        # when no longer leader, has no leader perms
        grp1_leader = group1.leader
        group1.leader = stu1
        group1.save()
        self.assertFalse(group1.has_perms_for_leader(grp1_leader.user))
        self.assertTrue(group1.has_perms_for_course_stu(grp1_leader.user))

        # when no longer takes the course, no perms
        course1.students.clear()
        self.assertFalse(group1.has_perms_for_course_stu(stu1.user))
        self.assertFalse(group1.has_perms_for_course_stu(grp1_leader.user))

    def test_instructor_perms(self):
        course1 = factories.CourseFactory()
        group1 = factories.GroupFactory(course=course1)
        inst1 = factories.InstructorFactory()

        # normal inst has no perms
        self.assertFalse(group1.has_perms_for_course_inst(inst1.user))

        # course inst has perms
        factories.TeachesFactory(instructor=inst1, course=course1)
        self.assertTrue(group1.has_perms_for_course_inst(inst1.user))

        # when no longer course inst, no perms
        course1.instructors.clear()
        self.assertFalse(group1.has_perms_for_course_inst(inst1.user))


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

        with self.assertRaises(ValidationError) as cm:
            factories.CourseFactory(min_group_size=-1, max_group_size=-1)
        self.assertTrue(cm.exception.message_dict.get('min_group_size'))
        self.assertTrue(cm.exception.message_dict.get('max_group_size'))

        try:
            factories.CourseFactory(min_group_size=2, max_group_size=2)
        except Exception as e:
            self.fail(str(e))

        # check year
        with self.assertRaises(ValidationError) as cm:
            factories.CourseFactory(year=-1)
        self.assertIn('year', cm.exception.message_dict)

        with self.assertRaises(ValidationError) as cm:
            factories.CourseFactory(year=10000)
        self.assertIn('year', cm.exception.message_dict)

        # check semester
        with self.assertRaises(ValidationError) as cm:
            factories.CourseFactory(semester='SUM')
        self.assertIn('semester', cm.exception.message_dict)

    def test_clean(self):
        # check group size
        cs = Course(
            title='SEP',
            semester='AUT',
            min_group_size=-1,
        )
        with self.assertRaises(ValidationError) as cm:
            cs.full_clean()
        self.assertIn('min_group_size', cm.exception.message_dict)

        # check group size
        cs = Course(
            title='SEP',
            semester='AUT',
            max_group_size=-1,
        )
        with self.assertRaises(ValidationError) as cm:
            cs.full_clean()
        self.assertIn('max_group_size', cm.exception.message_dict)

        # check year
        cs = Course(
            title='SEP',
            year=-1,
            semester='AUT',
        )
        with self.assertRaises(ValidationError) as cm:
            cs.full_clean()
        self.assertIn('year', cm.exception.message_dict)

    def test_get_next_group_number(self):
        course = factories.CourseFactory()
        self.assertEqual(course.get_next_group_number(), course.NUMBERS_LIST[0])
        factories.GroupFactory(course=course)
        self.assertEqual(course.get_next_group_number(), course.NUMBERS_LIST[1])

    def test_add_group(self):
        course = factories.CourseFactory()
        stu = factories.StudentTakesCourseFactory(courses__course=course)
        self.assertEqual(course.groups.count(), 0)

        course.add_group(
            members=(stu,),
            name='Hello_world',
            leader=factories.StudentTakesCourseFactory(courses__course=course),
        )
        self.assertEqual(course.groups.count(), 1)

    def test_add_assignment(self):
        course = factories.CourseFactory()
        self.assertEqual(course.assignments.count(), 0)

        course.add_assignment(title="ass1", grade_ratio='0.1')

        self.assertEqual(course.assignments.count(), 1)

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

    def test_has_group_including(self):
        course1 = factories.CourseFactory()
        stu1 = factories.StudentTakesCourseFactory(courses__course=course1)
        stu2 = factories.StudentTakesCourseFactory(courses__course=course1)
        stu3 = factories.StudentTakesCourseFactory(courses__course=course1)

        factories.GroupFactory(leader=stu1, course=course1)
        group1 = factories.GroupFactory(course=course1)
        factories.GroupMembershipFactory(group=group1, student=stu2)

        self.assertTrue(course1.has_group_including(stu1))
        self.assertTrue(course1.has_group_including(stu2))
        self.assertFalse(course1.has_group_including(stu3))


class CoursePermsTests(TestCase):

    def test_base_perms(self):
        stu1 = factories.StudentFactory()
        inst1 = factories.InstructorFactory()
        course1 = factories.CourseFactory()

        # test base perms
        self.assertTrue(course1.has_base_perms_for_instructor(inst1.user))
        self.assertTrue(course1.has_base_perms_for_student(stu1.user))

        # test inst perms after perm restored
        takes1 = factories.TakesFactory(student=stu1, course=course1)
        self.assertTrue(course1.has_base_perms_for_student(stu1.user))
        self.assertTrue(course1.has_perms_for_course_stu(stu1.user))
        takes1.delete()
        self.assertTrue(course1.has_base_perms_for_student(stu1.user))
        self.assertFalse(course1.has_perms_for_course_stu(stu1.user))

        teaches1 = factories.TeachesFactory(instructor=inst1, course=course1)
        self.assertTrue(course1.has_base_perms_for_instructor(inst1.user))
        self.assertTrue(course1.has_perms_for_course_inst(inst1.user))
        teaches1.delete()
        self.assertTrue(course1.has_base_perms_for_instructor(inst1.user))
        self.assertFalse(course1.has_perms_for_course_inst(inst1.user))

        # test perms after deletion
        user_stu1 = stu1.user
        stu1.delete()
        self.assertFalse(course1.has_base_perms_for_student(user_stu1))

        user_inst1 = inst1.user
        inst1.delete()
        self.assertFalse(course1.has_base_perms_for_instructor(user_inst1))


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
        try:
            factories.CourseAssignmentFactory(grade_ratio='0')
        except ValidationError as e:
            self.fail(str(e))

        try:
            factories.CourseAssignmentFactory(grade_ratio='1')
        except ValidationError as e:
            self.fail(str(e))

        with self.assertRaises(ValidationError) as cm:
            factories.CourseAssignmentFactory(grade_ratio='-0.1')
        self.assertIn('grade_ratio', cm.exception.message_dict)

        with self.assertRaises(ValidationError) as cm:
            factories.CourseAssignmentFactory(grade_ratio='1.1')
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


class InstructorPermsTests(TestCase):
    def test_perms(self):
        inst = factories.InstructorFactory()
        user = inst.user
        for i in range(10):
            factories.StudentFactory()
            factories.InstructorFactory()

        self.assertTrue(user.has_perm('core.view_instructor'))
        self.assertTrue(user.has_perm('core.view_takes'))
        self.assertTrue(user.has_perm('core.change_takes'))
        self.assertTrue(user.has_perm('core.add_takes'))
        self.assertTrue(user.has_perm('core.delete_takes'))
        self.assertTrue(user.has_perm('core.view_student'))
        self.assertTrue(user.has_perm('core.view_course'))
        self.assertTrue(user.has_perm('core.add_course'))
        self.assertTrue(user.has_perm('core.change_course'))
        self.assertTrue(user.has_perm('core.delete_course'))
        self.assertTrue(user.has_perm('core.view_instructor', inst))
        for i in Instructor.objects.exclude(pk=inst.pk):
            self.assertTrue(i.has_base_perms_for_instructor(user))
            self.assertTrue(i.has_base_perms_for_instructor(inst.user))

        for stu in Student.objects.all():
            self.assertTrue(stu.has_base_perms_for_instructor(user))

        inst.delete()
        user = User.objects.get(pk=user.pk)
        self.assertFalse(user.has_perm('core.view_instructor'))
        self.assertFalse(user.has_perm('core.view_takes'))
        self.assertFalse(user.has_perm('core.change_takes'))
        self.assertFalse(user.has_perm('core.add_takes'))
        self.assertFalse(user.has_perm('core.delete_takes'))
        self.assertFalse(user.has_perm('core.view_student'))
        self.assertFalse(user.has_perm('core.view_course'))
        self.assertFalse(user.has_perm('core.add_course'))
        self.assertFalse(user.has_perm('core.change_course'))
        self.assertFalse(user.has_perm('core.delete_course'))
        self.assertFalse(user.has_perm('core.view_instructor', inst))
        for i in Instructor.objects.exclude(pk=inst.pk):
            self.assertFalse(i.has_base_perms_for_instructor(user))
            self.assertFalse(i.has_base_perms_for_instructor(inst.user))

        for stu in Student.objects.all():
            self.assertFalse(stu.has_base_perms_for_instructor(user))


class InstructorManagerTests(TestCase):

    def setUp(self):
        self.mang = Instructor.objects

    def test_gives_courses(self):
        course1 = factories.CourseFactory()
        course2 = factories.CourseFactory()
        course3 = factories.CourseFactory()
        for i in range(3):
            factories.InstructorTeachesCourseFactory(courses__course=course1)
            factories.InstructorTeachesCourseFactory(courses__course=course2)
            factories.InstructorTeachesCourseFactory(courses__course=course3)

        self.assertEqual(self.mang.gives_courses([course1]).count(),
                         3)
        self.assertEqual(self.mang.gives_courses([course1, course2]).count(),
                         6)
        self.assertEqual(self.mang.gives_courses([course1, course2, course3]).count(),
                         9)


class TakesTests(TestCase):

    def test_save(self):
        # invalid grade
        with self.assertRaises(ValidationError) as cm:
            factories.TakesFactory(grade=-1)
        self.assertIn('grade', cm.exception.message_dict)

        with self.assertRaises(ValidationError) as cm:
            factories.TakesFactory(grade=101)
        self.assertIn('grade', cm.exception.message_dict)

        takes = factories.TakesFactory()
        with self.assertRaises(ValidationError):
            factories.TakesFactory(student=takes.student, course=takes.course)

    def test_perms(self):
        teaches = factories.TeachesFactory()
        inst = teaches.instructor
        course = teaches.course
        stu = factories.StudentFactory()

        # test perms after created
        self.assertFalse(course.has_perms_for_course_stu(stu.user))
        self.assertFalse(teaches.has_perms_for_course_stu(stu.user))

        takes = factories.TakesFactory(student=stu, course=course)

        self.assertTrue(takes.has_perms_for_course_stu(stu.user))
        self.assertTrue(takes.has_perms_for_course_inst(inst.user))
        self.assertTrue(course.has_perms_for_course_stu(stu.user))
        self.assertTrue(teaches.has_perms_for_course_stu(stu.user))
        self.assertTrue(stu.has_perms_for_course_inst(inst.user))
        self.assertTrue(inst.has_perms_for_course_stu(stu.user))

        # test perms after deletion
        takes.delete()
        self.assertFalse(takes.has_perms_for_course_stu(stu.user))
        self.assertFalse(takes.has_perms_for_course_inst(inst.user))
        self.assertFalse(course.has_perms_for_course_stu(stu.user))
        self.assertFalse(teaches.has_perms_for_course_stu(stu.user))

        # test perms after deletion but relationship still keeps
        teaches1 = factories.TeachesFactory(instructor=inst)
        course1 = teaches1.course
        takes = factories.TakesFactory(student=stu, course=course)
        factories.TakesFactory(student=stu, course=course1)

        takes.delete()
        self.assertFalse(takes.has_perms_for_course_stu(stu.user))
        self.assertFalse(takes.has_perms_for_course_inst(inst.user))
        self.assertFalse(course.has_perms_for_course_stu(stu.user))
        self.assertFalse(teaches.has_perms_for_course_stu(stu.user))
        self.assertTrue(teaches1.has_perms_for_course_stu(stu.user))
        self.assertTrue(stu.has_perms_for_course_inst(inst.user))
        self.assertTrue(inst.has_perms_for_course_stu(stu.user))

    def test_student_perms(self):
        teaches = factories.TeachesFactory()
        inst = teaches.instructor
        course = teaches.course
        stu = factories.StudentFactory()
        takes = factories.TakesFactory(student=stu, course=course)

        # test perms after student changed
        stu1 = factories.StudentFactory()
        takes.student = stu1
        takes.save()

        self.assertFalse(takes.has_perms_for_course_stu(stu.user))
        self.assertFalse(course.has_perms_for_course_stu(stu.user))
        self.assertFalse(teaches.has_perms_for_course_stu(stu.user))
        self.assertTrue(stu.has_base_perms_for_instructor(inst.user))

        self.assertTrue(takes.has_perms_for_course_stu(stu1.user))
        self.assertTrue(takes.has_perms_for_course_inst(inst.user))
        self.assertTrue(course.has_perms_for_course_stu(stu1.user))
        self.assertTrue(teaches.has_perms_for_course_stu(stu1.user))
        self.assertTrue(stu1.has_perms_for_course_inst(inst.user))
        self.assertTrue(inst.has_perms_for_course_stu(stu1.user))

        # test perms after student changed,
        # but it still takes inst's other course
        teaches1 = factories.TeachesFactory(instructor=inst)
        factories.TakesFactory(student=stu1, course=teaches1.course)
        takes.student = stu
        takes.save()

        self.assertTrue(stu1.has_perms_for_course_inst(inst.user))
        self.assertTrue(inst.has_perms_for_course_stu(stu1.user))

    def test_course_perms(self):
        teaches = factories.TeachesFactory()
        inst = teaches.instructor
        stu = factories.StudentFactory()
        takes = factories.TakesFactory(student=stu, course=teaches.course)

        # test perms after course changed
        teaches1 = factories.TeachesFactory()
        inst1 = teaches1.instructor
        takes.course = teaches1.course
        takes.save()

        self.assertTrue(takes.has_perms_for_course_stu(stu.user))
        self.assertFalse(teaches.course.has_perms_for_course_stu(stu.user))
        self.assertFalse(teaches.has_perms_for_course_stu(stu.user))
        self.assertTrue(teaches1.course.has_perms_for_course_stu(stu.user))
        self.assertTrue(teaches1.has_perms_for_course_stu(stu.user))
        self.assertTrue(inst1.has_perms_for_course_stu(stu.user))

        self.assertFalse(takes.has_perms_for_course_stu(inst.user))
        self.assertTrue(stu.has_base_perms_for_instructor(inst.user))
        self.assertTrue(takes.has_perms_for_course_stu(inst1.user))
        self.assertTrue(stu.has_perms_for_course_inst(inst1.user))

        # test perms after course changed,
        # but student still takes inst's another course
        teaches2 = factories.TeachesFactory(instructor=inst1)
        factories.TakesFactory(student=stu, course=teaches2.course)
        takes.course = teaches.course
        takes.save()

        self.assertTrue(inst1.has_perms_for_course_stu(stu.user))
        self.assertTrue(stu.has_perms_for_course_inst(inst1.user))
        self.assertFalse(teaches1.course.has_perms_for_course_stu(stu.user))
        self.assertFalse(teaches1.has_perms_for_course_stu(stu.user))
        self.assertTrue(takes.course.has_perms_for_course_stu(stu.user))

    def test_student_takes_perms(self):
        """
        Test perms between student taking same course
        """
        course1 = factories.CourseFactory()
        stu_cs1_list = []
        for i in range(10):
            stu_cs1_list.append(factories.StudentTakesCourseFactory(courses__course=course1))
            factories.StudentFactory()

        for stu in stu_cs1_list:
            for other in course1.students.exclude(pk=stu.pk):
                self.assertTrue(other.has_perms_for_course_stu(stu.user))
                self.assertTrue(stu.has_perms_for_course_stu(other.user))


class TeachesTests(TestCase):

    def test_save(self):
        teaches = factories.TeachesFactory()
        with self.assertRaises(IntegrityError):
            factories.TeachesFactory(instructor=teaches.instructor,
                                     course=teaches.course)


class TeachesPermsTests(TestCase):

    def test_perms(self):
        inst = factories.InstructorFactory()
        course = factories.CourseFactory()
        for i in range(5):
            factories.StudentTakesCourseFactory(courses__course=course)
        takes_list = course.takes.all()

        teaches = factories.TeachesFactory(instructor=inst, course=course)

        self.assertTrue(teaches.has_perms_for_course_inst(inst.user))
        self.assertTrue(course.has_perms_for_course_inst(inst.user))

        for takes in takes_list:
            stu = takes.student
            self.assertTrue(takes.has_perms_for_course_inst(inst.user))
            self.assertTrue(stu.has_perms_for_course_inst(inst.user))

            self.assertTrue(inst.has_perms_for_course_stu(stu.user))
            self.assertTrue(teaches.has_perms_for_course_stu(stu.user))

    def test_instructor_perms(self):
        inst1 = factories.InstructorFactory()
        inst2 = factories.InstructorFactory()
        course1 = factories.CourseFactory()
        course2 = factories.CourseFactory()
        for i in range(5):
            factories.StudentTakesCourseFactory(courses__course=course1)
        takes_list = course1.takes.all()

        teaches = factories.TeachesFactory(instructor=inst1, course=course1)

        # after change inst
        teaches.instructor = inst2
        teaches.save()

        self.assertFalse(teaches.has_perms_for_course_inst(inst1.user))
        self.assertFalse(course1.has_perms_for_course_inst(inst1.user))
        for takes in takes_list:
            stu = takes.student
            self.assertFalse(takes.has_perms_for_course_inst(inst1.user))
            self.assertTrue(stu.has_base_perms_for_instructor(inst1.user))

            self.assertFalse(inst1.has_perms_for_course_stu(stu.user))

        self.assertTrue(teaches.has_perms_for_course_inst(inst2.user))
        self.assertTrue(course1.has_perms_for_course_inst(inst2.user))
        for takes in takes_list:
            stu = takes.student
            self.assertTrue(takes.has_perms_for_course_inst(inst2.user))
            self.assertTrue(stu.has_perms_for_course_inst(inst2.user))

            self.assertTrue(inst2.has_perms_for_course_stu(stu.user))
            self.assertTrue(teaches.has_perms_for_course_stu(stu.user))

        # after change inst, but relationship keeps
        stu1 = factories.StudentTakesCourseFactory(courses__course=course1)
        factories.TakesFactory(student=stu1, course=course2)
        factories.TeachesFactory(instructor=inst2, course=course2)

        teaches.instructor = inst1
        teaches.save()
        self.assertTrue(inst2.has_perms_for_course_stu(stu1.user))
        self.assertTrue(stu1.has_perms_for_course_inst(inst2.user))

    def test_course_perms_plus(self):
        course = factories.CourseFactory()
        inst = factories.InstructorFactory()
        teaches = factories.TeachesFactory(course=course, instructor=inst)
        for i in range(10):
            factories.StudentTakesCourseFactory(courses__course=course)
        takes_list = course.takes.all()

        for takes in takes_list:
            stu = takes.student
            self.assertTrue(inst.has_perms_for_course_stu(stu.user))
            self.assertTrue(stu.has_perms_for_course_inst(inst.user))

        teaches.delete()

        for takes in takes_list:
            stu = takes.student
            self.assertFalse(inst.has_perms_for_course_stu(stu.user))
            self.assertTrue(stu.has_base_perms_for_instructor(inst.user))

    def test_course_perms(self):
        inst1 = factories.InstructorFactory()
        inst2 = factories.InstructorFactory()
        course1 = factories.CourseFactory()
        course2 = factories.CourseFactory()
        for i in range(5):
            factories.StudentTakesCourseFactory(courses__course=course1)
            factories.StudentTakesCourseFactory(courses__course=course2)
        takes_list1 = course1.takes.all()
        takes_list2 = course2.takes.all()

        factories.TeachesFactory(instructor=inst2, course=course1)
        factories.InstructorTeachesCourseFactory(courses__course=course2)
        teaches = factories.TeachesFactory(instructor=inst1, course=course1)

        # after course changed
        teaches.course = course2
        teaches.save()
        self.assertFalse(course1.has_perms_for_course_inst(inst1.user))

        for takes in takes_list1:
            stu = takes.student
            self.assertFalse(takes.has_perms_for_course_inst(inst1.user))
            self.assertTrue(stu.has_base_perms_for_instructor(inst1.user))

            self.assertFalse(teaches.has_perms_for_course_stu(stu.user))
            self.assertFalse(inst1.has_perms_for_course_stu(stu.user))

        self.assertTrue(course2.has_perms_for_course_inst(inst1.user))
        self.assertTrue(teaches.has_perms_for_course_inst(inst1.user))

        for takes in takes_list2:
            stu = takes.student
            self.assertTrue(takes.has_perms_for_course_inst(inst1.user))
            self.assertTrue(stu.has_perms_for_course_inst(inst1.user))

            self.assertTrue(teaches.has_perms_for_course_stu(stu.user))
            self.assertTrue(inst1.has_perms_for_course_stu(stu.user))

        # after course changed, but relationship keeps
        stu1 = factories.StudentTakesCourseFactory(courses__course=course1)
        factories.TakesFactory(student=stu1, course=course2)

        teaches.course = course1
        teaches.save()
        self.assertTrue(inst1.has_perms_for_course_stu(stu1.user))
        self.assertTrue(stu1.has_perms_for_course_inst(inst1.user))

    def test_teaches_perms(self):
        inst1 = factories.InstructorFactory()
        inst2 = factories.InstructorFactory()
        course1 = factories.CourseFactory()
        course2 = factories.CourseFactory()
        teaches1_1 = factories.TeachesFactory(instructor=inst1, course=course1)

        self.assertTrue(teaches1_1.has_perms_for_course_inst(inst1.user))
        self.assertFalse(teaches1_1.has_perms_for_course_inst(inst2.user))
        self.assertFalse(teaches1_1.has_perms_for_other_course_inst(inst2.user))

        teaches2_1 = factories.TeachesFactory(instructor=inst2, course=course1)
        self.assertTrue(teaches1_1.has_perms_for_other_course_inst(inst2.user))
        self.assertTrue(inst1.user.has_perm('core.view_teaches', teaches2_1))
        self.assertTrue(teaches2_1.has_perms_for_other_course_inst(inst1.user))


class ModelTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.user = factories.UserFactory()

    def test_get_role_of(self):
        # No roles bound to it
        self.assertEqual(get_role_of(self.user), None)

        # Anonymous user
        self.assertEqual(get_role_of(AnonymousUser()), None)

        # Instructor
        instructor = factories.InstructorFactory(user=self.user)
        self.assertEqual(get_role_of(self.user), instructor)
        instructor.delete()

        # Student
        student = factories.StudentFactory(user=self.user)
        self.assertEqual(get_role_of(self.user), student)

    def test_import_student(self):
        factories.ClassFactory(class_id='301')
        with open(str((environ.Path(__file__) - 1).path('stu.xls')), 'rb') as f:
            count = import_student(self.factory.post('anything', {'file': f}).FILES['file'])
        self.assertEqual(count, 10)

        with open(str((environ.Path(__file__) - 1).path('stu.xls')), 'rb') as f:
            count = import_student(self.factory.post('anything', {'file': f}).FILES['file'])
        self.assertEqual(count, 0)

    def test_assign_and_has_four_level_perm(self):
        user = User.objects.create_user(username='foo', password='foobar')
        stu = factories.StudentFactory()

        assign_four_level_perm('core.view_student_base', user, stu)
        self.assertTrue(user.has_perm('core.view_student_base', stu))
        assign_four_level_perm('core.view_student_normal', user, stu)
        self.assertTrue(user.has_perm('core.view_student_normal', stu))
        self.assertFalse(user.has_perm('core.view_student_base', stu))
        self.assertFalse(user.has_perm('core.view_student_advanced', stu))
        self.assertFalse(user.has_perm('core.view_student', stu))
        assign_four_level_perm('core.view_student_advanced', user, stu)
        self.assertTrue(user.has_perm('core.view_student_advanced', stu))
        self.assertFalse(user.has_perm('core.view_student_base', stu))
        self.assertFalse(user.has_perm('core.view_student_normal', stu))
        self.assertFalse(user.has_perm('core.view_student', stu))
        assign_four_level_perm('core.view_student', user, stu)
        self.assertTrue(user.has_perm('core.view_student', stu))
        self.assertFalse(user.has_perm('core.view_student_base', stu))
        self.assertFalse(user.has_perm('core.view_student_normal', stu))
        self.assertFalse(user.has_perm('core.view_student_advanced', stu))

        assign_four_level_perm('core.view_student_base', user, stu)
        self.assertTrue(user.has_perm('core.view_student', stu))
        assign_four_level_perm('core.view_student_normal', user, stu)
        self.assertTrue(user.has_perm('core.view_student', stu))
        assign_four_level_perm('core.view_student_advanced', user, stu)
        self.assertTrue(user.has_perm('core.view_student', stu))
        assign_four_level_perm('core.view_student', user, stu)
        self.assertTrue(user.has_perm('core.view_student', stu))

        remove_perm('core.view_student', user, stu)
        assign_four_level_perm('core.view_student_normal', user, stu)
        assign_four_level_perm('core.view_student_base', user, stu)
        self.assertTrue(user.has_perm('core.view_student_normal', stu))
        assign_four_level_perm('core.view_student_normal', user, stu)
        self.assertTrue(user.has_perm('core.view_student_normal', stu))
        assign_four_level_perm('core.view_student_advanced', user, stu)
        self.assertTrue(user.has_perm('core.view_student_advanced', stu))
        assign_four_level_perm('core.view_student', user, stu)
        self.assertTrue(user.has_perm('core.view_student', stu))

        remove_perm('core.view_student', user, stu)
        assign_four_level_perm('core.view_student_advanced', user, stu)
        assign_four_level_perm('core.view_student_base', user, stu)
        self.assertTrue(user.has_perm('core.view_student_advanced', stu))
        assign_four_level_perm('core.view_student_normal', user, stu)
        self.assertTrue(user.has_perm('core.view_student_advanced', stu))
        assign_four_level_perm('core.view_student_advanced', user, stu)
        self.assertTrue(user.has_perm('core.view_student_advanced', stu))
        assign_four_level_perm('core.view_student', user, stu)
        self.assertTrue(user.has_perm('core.view_student', stu))

        assign_four_level_perm('core.view_student_advanced', user, stu, override=True)
        self.assertTrue(user.has_perm('core.view_student_advanced', stu))
        assign_four_level_perm('core.view_student_normal', user, stu, override=True)
        self.assertTrue(user.has_perm('core.view_student_normal', stu))
        assign_four_level_perm('core.view_student_base', user, stu, override=True)
        self.assertTrue(user.has_perm('core.view_student_base', stu))
        assign_four_level_perm('core.view_student', user, stu, override=True)
        self.assertTrue(user.has_perm('core.view_student', stu))

    def test_has_four_level_perm(self):
        user = User.objects.create_user(username='foo', password='foobar')
        stu = factories.StudentFactory()

        assign_perm('core.view_student', user, stu)
        self.assertTrue(has_four_level_perm('core.view_student_base', user, stu))
        self.assertTrue(has_four_level_perm('core.view_student_normal', user, stu))
        self.assertTrue(has_four_level_perm('core.view_student_advanced', user, stu))
        self.assertTrue(has_four_level_perm('core.view_student', user, stu))
        self.assertFalse(has_four_level_perm('core.view_student_base', user, stu, exact=True))
        self.assertFalse(has_four_level_perm('core.view_student_normal', user, stu, exact=True))
        self.assertFalse(has_four_level_perm('core.view_student_advanced', user, stu, exact=True))
        self.assertTrue(has_four_level_perm('core.view_student', user, stu, exact=True))

        remove_perm('core.view_student', user, stu)
        assign_perm('core.view_student_base', user, stu)
        self.assertTrue(has_four_level_perm('core.view_student_base', user, stu))
        self.assertFalse(has_four_level_perm('core.view_student_normal', user, stu))
        self.assertFalse(has_four_level_perm('core.view_student_advanced', user, stu))
        self.assertFalse(has_four_level_perm('core.view_student', user, stu))
        self.assertTrue(has_four_level_perm('core.view_student_base', user, stu, exact=True))
        self.assertFalse(has_four_level_perm('core.view_student_normal', user, stu, exact=True))
        self.assertFalse(has_four_level_perm('core.view_student_advanced', user, stu, exact=True))
        self.assertFalse(has_four_level_perm('core.view_student', user, stu, exact=True))

        remove_perm('core.view_student_base', user, stu)
        assign_perm('core.view_student_normal', user, stu)
        self.assertTrue(has_four_level_perm('core.view_student_base', user, stu))
        self.assertTrue(has_four_level_perm('core.view_student_normal', user, stu))
        self.assertFalse(has_four_level_perm('core.view_student_advanced', user, stu))
        self.assertFalse(has_four_level_perm('core.view_student', user, stu))
        self.assertFalse(has_four_level_perm('core.view_student_base', user, stu, exact=True))
        self.assertTrue(has_four_level_perm('core.view_student_normal', user, stu, exact=True))
        self.assertFalse(has_four_level_perm('core.view_student_advanced', user, stu, exact=True))
        self.assertFalse(has_four_level_perm('core.view_student', user, stu, exact=True))

        remove_perm('core.view_student_normal', user, stu)
        assign_perm('core.view_student_advanced', user, stu)
        self.assertTrue(has_four_level_perm('core.view_student_base', user, stu))
        self.assertTrue(has_four_level_perm('core.view_student_normal', user, stu))
        self.assertTrue(has_four_level_perm('core.view_student_advanced', user, stu))
        self.assertFalse(has_four_level_perm('core.view_student', user, stu))
        self.assertFalse(has_four_level_perm('core.view_student_base', user, stu, exact=True))
        self.assertFalse(has_four_level_perm('core.view_student_normal', user, stu, exact=True))
        self.assertTrue(has_four_level_perm('core.view_student_advanced', user, stu, exact=True))
        self.assertFalse(has_four_level_perm('core.view_student', user, stu, exact=True))


class ModelDiffMixinTests(TestCase):

    def setUp(self):
        self.stu = factories.StudentFactory()
        self.cls = factories.ClassFactory()

    def test_before_create(self):
        stu = Student(user=factories.UserFactory(), name='LYYF',
                      s_id='2012211165', s_class=factories.ClassFactory())
        self.assertFalse(stu.changed_fields)
        self.assertFalse(stu.get_old_field('name'))
        self.assertFalse(stu.pk)
        self.assertTrue(stu.name)

    def test_fields_change(self):
        stu = factories.StudentFactory()
        self.assertEqual(stu.has_changed, False)
        self.assertFalse(stu.changed_fields)

        # char field
        stu.name = 'LYYF'
        self.assertEqual(stu.has_changed, True)
        self.assertEqual(stu.changed_fields, ['name'])
        stu.save()
        self.assertEqual(stu.has_changed, False)
        self.assertFalse(stu.changed_fields)

        # foreign key field
        stu.s_class = self.cls
        self.assertEqual(stu.has_changed, True)
        self.assertEqual(stu.changed_fields, ['s_class'])
        stu.save()
        self.assertEqual(stu.has_changed, False)
        self.assertFalse(stu.changed_fields)

    def test_m2m_field(self):
        cls1 = factories.ClassFactory()
        stu1 = factories.StudentFactory()

        cls1.students.add(stu1)