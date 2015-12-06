# -*- coding: utf-8 -*-
from test_plus.test import TestCase

from . import factories


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

    def test_get_list_of_available_numbers(self):
        pass


class CourseMethodTests(TestCase):

    def test_delete_group(self):
        course = factories.CourseFactory()
        group = factories.GroupFactory(course=course)
        self.assertEqual(course.group_set.count(), 1)
        
        course.delete_group(group)
        
        self.assertEqual(course.group_set.count(), 0)


    def test_add_group(self):
        course = factories.CourseFactory()
        stu = factories.StudentFactory()
        self.assertEqual(course.group_set.count(),0)

        course.add_group(number="1234",members=(stu,))

        self.assertEqual(course.group_set.count(),1)

    def test_add_assignemnt(self):
        course = factories.CourseFactory()
        self.assertEqual(course.assignments.count(),0)

        course.add_assignment(title="ass1",grade_ratio=0.1)
        #course.assignments.create(course=course,title="ass1",grade_ratio=0.1)

        self.assertEqual(course.assignments.count(),1)
    
    def test_delete_assignment(self):
        course = factories.CourseFactory()
        assignmt = factories.CourseAssignmentFactory(course=course)
        teaches = factories.TeachesFactory(course=course, assignments=(assignmt,))
        self.assertEqual(teaches.assignments.count(), 1)
        self.assertEqual(course.assignments.count(), 1)
        
        course.delete_assignment(assignmt)
        
        self.assertEqual(teaches.assignments.count(), 0)
        self.assertEqual(course.assignments.count(), 0)





class InstructorMethodTests(TestCase):

    def test_delete_course(self):
        course = factories.CourseFactory()
        instructor = factories.InstructorFactory()
        teaches = factories.TeachesFactory(course=course,instructor=instructor)
        self.assertEqual(instructor.courses.count(),1)
        
        instructor.delete_course(course)
        
        self.assertEqual(instructor.courses.count(),0)

    def test_add_course(self):
        instructor = factories.InstructorFactory()
        self.assertEqual(instructor.courses.count(),0)

        instructor.add_course(title="DS")

        self.assertEqual(instructor.courses.count(),1)