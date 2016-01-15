# -*- coding: utf-8 -*-
import unittest

from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.test import APIClient

from . import factories
from ..models import (
    Student, Instructor, Course, Takes,
    has_four_level_perm,
)

User = get_user_model()

skip_seperate_tests = True
skip_seperate_tests_reason = "This test can only pass when tested separately."


def get_course_url(course):
    return reverse('api:course-detail', kwargs={'pk': course.pk})


def get_student_url(student):
    return reverse('api:student-detail', kwargs={'pk': student.pk})


def get_instructor_url(instructor):
    return reverse('api:instructor-detail', kwargs={'pk': instructor.pk})


class APITestUtilsMixin(object):
    def force_authenticate_user(self, user):
        self.client.force_authenticate(user=user)


class StudentAPITests(APITestUtilsMixin, APITestCase):

    def get_student_list(self):
        return self.client.get(reverse('api:student-list'))

    def get_student_detail(self, stu):
        return self.client.get(reverse('api:student-detail', kwargs={'pk': stu.pk}))

    def post_student(self, stu_dict):
        return self.client.post(reverse('api:student-list'), stu_dict)

    def put_student(self, stu, new_stu):
        return self.client.put(reverse('api:student-detail', kwargs={'pk': stu.pk}), new_stu)

    def patch_student(self, stu, data_dict):
        return self.client.patch(reverse('api:student-detail', kwargs={'pk': stu.pk}), data_dict)

    def delete_student(self, stu):
        return self.client.delete(reverse('api:student-detail', kwargs={'pk': stu.pk}))

    def is_classmate_fields(self, data_dict):
        return (set(data_dict.keys()) ==
                {'url', 'id', 'name', 'sex', 's_id', 's_class'})

    def is_student_course_stu_fields(self, data_dict):
        return (set(data_dict.keys()) ==
                {'url', 'id', 'name', 'sex'})

    def is_instructor_fields(self, data_dict):
        return (set(data_dict.keys()) ==
                {'url', 'id', 'name', 'sex', 's_id', 's_class', 'courses'})

    def is_itself_fields(self, data_dict):
        return (set(data_dict.keys()) ==
                {'url', 'id', 'name', 'sex', 's_id', 's_class', 'courses', 'user'})

    def test_test(self):
        pass

    def test_access_normal_student(self):
        stu1 = factories.StudentFactory()
        for i in range(10):
            factories.StudentFactory()

        self.force_authenticate_user(stu1.user)
        # student GET
        response = self.get_student_list()
        self.assertEqual(len(response.data), 1)

        response = self.get_student_detail(stu1)       # itself
        self.assertTrue(self.is_itself_fields(response.data))

        for stu in Student.objects.exclude(pk=stu1.pk):     # others
            response = self.get_student_detail(stu)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # student POST
        response = self.post_student({})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # student PUT, PATCH
        for stu in Student.objects.all():
            response = self.put_student(stu, {})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            response = self.patch_student(stu, {})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # student DELETE
        for stu in Student.objects.all():
            response = self.delete_student(stu)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # instructor GET
        self.force_authenticate_user(None)
        inst1 = factories.InstructorFactory()
        self.force_authenticate_user(inst1.user)

        response = self.get_student_list()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), Student.objects.count())

        for stu in Student.objects.all():
            response = self.get_student_detail(stu)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(self.is_instructor_fields(response.data))

        # instructor POST
        response = self.post_student({})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # instructor PUT, PATCH
        for stu in Student.objects.all():
            response = self.put_student(stu, {})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            response = self.patch_student(stu, {})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # instructor DELETE
        for stu in Student.objects.all():
            response = self.delete_student(stu)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_access_classmate(self):
        stu1 = factories.StudentFactory()
        cls1 = stu1.s_class
        for i in range(10):
            factories.StudentFactory(s_class=cls1)
            factories.StudentFactory()
        self.force_authenticate_user(stu1.user)

        # GET
        response = self.get_student_list()
        self.assertEqual(len(response.data), cls1.students.count())
        for stu in cls1.students.exclude(pk=stu1.pk):
            response = self.get_student_detail(stu)
            self.assertTrue(self.is_classmate_fields(response.data))

        # PUT, PATCH, DELETE
        for stu in cls1.students.exclude(pk=stu1.pk):
            response = self.put_student(stu, {})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            response = self.patch_student(stu, {})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            response = self.delete_student(stu)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_access_course_stu(self):
        course1 = factories.CourseFactory()
        stu1 = factories.StudentTakesCourseFactory(courses__course=course1)
        for i in range(10):
            factories.StudentTakesCourseFactory(courses__course=course1)
            factories.StudentFactory()
        course_stus = Student.objects.takes_courses([course1])
        self.force_authenticate_user(stu1.user)

        # GET
        response = self.get_student_list()
        self.assertEqual(len(response.data), course_stus.count())

        for stu in course_stus.exclude(pk=stu1.pk):
            response = self.get_student_detail(stu)
            self.assertTrue(self.is_student_course_stu_fields(response.data))

        # PUT, PATCH, DELETE
        for stu in course_stus:
            response = self.put_student(stu, {})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            response = self.patch_student(stu, {})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            response = self.delete_student(stu)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class InstructorAPITests(APITestUtilsMixin, APITestCase):

    def get_instructor_list(self):
        return self.client.get(reverse('api:instructor-list'))

    def get_instructor_detail(self, inst):
        return self.client.get(reverse('api:instructor-detail', kwargs={'pk': inst.pk}))

    def post_instructor(self, inst_dict):
        return self.client.post(reverse('api:instructor-list'), inst_dict)

    def put_instructor(self, inst, inst_dict):
        return self.client.put(reverse('api:instructor-detail', kwargs={'pk': inst.pk}), inst_dict)

    def patch_instructor(self, inst, inst_dict):
        return self.client.patch(reverse('api:instructor-detail', kwargs={'pk': inst.pk}), inst_dict)

    def delete_instructor(self, inst):
        return self.client.delete(reverse('api:instructor-detail', kwargs={'pk': inst.pk}))

    def is_itself_fields(self, inst_dict):
        return (set(inst_dict.keys()) ==
                {'url', 'id', 'name', 'sex', 'inst_id', 'user', 'courses'})

    def is_other_inst_fields(self, inst_dict):
        return (set(inst_dict.keys()) ==
                {'url', 'id', 'name', 'sex', 'inst_id', 'courses'})

    def is_course_stu_fields(self, inst_dict):
        return (set(inst_dict.keys()) ==
                {'url', 'id', 'name', 'sex', 'courses'})

    def test_access_normal_instructor(self):
        inst1 = factories.InstructorFactory()
        for i in range(10):
            factories.InstructorFactory()

        self.force_authenticate_user(inst1.user)

        # instructor GET
        response = self.get_instructor_list()
        self.assertEqual(len(response.data), Instructor.objects.count())

        response = self.get_instructor_detail(inst1)
        self.assertTrue(self.is_itself_fields(response.data))

        for inst in Instructor.objects.exclude(pk=inst1.pk):
            response = self.get_instructor_detail(inst)
            self.assertTrue(self.is_other_inst_fields(response.data))

        # instructor POST, PUT, PATCH, DELETE
        response = self.post_instructor({})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        for inst in Instructor.objects.all():
            response = self.put_instructor(inst, {})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            response = self.patch_instructor(inst, {})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            response = self.delete_instructor(inst)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # student GET, POST, PUT, PATCH, DELETE
        stu1 = factories.StudentFactory()
        self.force_authenticate_user(stu1.user)
        response = self.get_instructor_list()
        self.assertEqual(len(response.data), 0)
        for inst in Instructor.objects.all():
            response = self.get_instructor_detail(inst)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            response = self.post_instructor({})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            response = self.put_instructor(inst, {})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            response = self.patch_instructor(inst, {})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            response = self.delete_instructor(inst)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_inst_access_course_inst(self):
        course1 = factories.CourseFactory()
        inst1 = factories.InstructorTeachesCourseFactory(courses__course=course1)
        for i in range(3):
            factories.InstructorTeachesCourseFactory(courses__course=course1)
            factories.InstructorFactory()
        course_insts = Instructor.objects.gives_courses([course1])
        self.force_authenticate_user(inst1.user)

        # GET
        response = self.get_instructor_list()
        self.assertEqual(len(response.data), Instructor.objects.count())
        for inst in course_insts.exclude(pk=inst1.pk):
            response = self.get_instructor_detail(inst)
            self.assertTrue(self.is_other_inst_fields(response.data))
            # PUT, PATCH, DELETE
            response = self.put_instructor(inst, {})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            response = self.patch_instructor(inst, {})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            response = self.delete_instructor(inst)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class StudentCoursesAPITests(APITestUtilsMixin, APITestCase):

    def setUp(self):
        self.admin = User.objects.create_superuser(username='admin', password='sep2015')

    def get_student_course_list(self, stu):
        return self.client.get(reverse('api:student-course-list', kwargs={'parent_lookup_student': stu.pk}))

    def get_student_course_detail(self, stu, takes):
        return self.client.get(reverse('api:student-course-detail',
                                       kwargs={'parent_lookup_student': stu.pk, 'pk': takes.pk}))

    def post_student_course(self, stu, takes_dict):
        return self.client.post(reverse('api:student-course-list', kwargs={'parent_lookup_student': stu.pk}),
                                takes_dict)

    def put_student_course(self, stu, takes, takes_dict):
        return self.client.put(
            reverse('api:student-course-detail',
                    kwargs={'parent_lookup_student': stu.pk, 'pk': takes.pk}),
            takes_dict
        )

    def patch_student_course(self, stu, takes, takes_dict):
        return self.client.patch(
            reverse('api:student-course-detail',
                    kwargs={'parent_lookup_student': stu.pk, 'pk': takes.pk}),
            takes_dict
        )

    def delete_student_course(self, stu, takes):
        return self.client.delete(reverse('api:student-course-detail',
                                          kwargs={'parent_lookup_student': stu.pk, 'pk': takes.pk}))

    def is_view_all_fields(self, takes_dict):
        return (set(takes_dict.keys()) ==
                {'url', 'id', 'student', 'course', 'grade'})

    def is_itself_fields(self, takes_dict):
        return self.is_view_all_fields(takes_dict)

    def is_course_inst_fields(self, takes_dict):
        return self.is_view_all_fields(takes_dict)

    def is_course_stu_fields(self, takes_dict):
        return (set(takes_dict.keys()) ==
                {'url', 'id', 'student', 'course', })

    def test_student_access_stu_course(self):
        course1 = factories.CourseFactory()
        course2 = factories.CourseFactory()
        stu1 = factories.StudentFactory()
        stu2 = factories.StudentFactory()
        takes1_1 = factories.TakesFactory(course=course1, student=stu1)
        takes2_1 = factories.TakesFactory(course=course1, student=stu2)

        self.force_authenticate_user(stu1.user)
        response = self.get_student_course_list(stu1)
        self.assertEqual(len(response.data), stu1.courses.count())
        # can GET itself
        response = self.get_student_course_detail(stu1, takes1_1)
        self.assertTrue(self.is_itself_fields(response.data))
        # cannot PUT, PATCH, DELETE itself
        response = self.put_student_course(stu1, takes1_1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.patch_student_course(stu1, takes1_1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.delete_student_course(stu1, takes1_1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # can GET others
        response = self.get_student_course_detail(stu2, takes2_1)
        self.assertTrue(self.is_course_stu_fields(response.data))
        # cannot POST, PUT, PATCH, DELETE others
        response = self.put_student_course(stu2, takes2_1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.patch_student_course(stu2, takes2_1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.delete_student_course(stu2, takes2_1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @unittest.skipIf(skip_seperate_tests, skip_seperate_tests_reason)
    def test_inst_access_student_course(self):
        course1 = factories.CourseFactory()
        course2 = factories.CourseFactory()
        stu1 = factories.StudentFactory()

        for i in range(10):
            factories.TakesFactory(course=course1, student=factories.StudentFactory())
            factories.TakesFactory(course=course2, student=factories.StudentFactory())

        inst1 = factories.InstructorTeachesCourseFactory(courses__course=course1)
        self.force_authenticate_user(inst1.user)

        # can POST to its courses
        self.assertNotIn(stu1, course1.students.all())
        self.assertIn(inst1, course1.instructors.all())
        response = self.post_student_course(stu1, dict(
            course=get_course_url(course1),
        ))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn(stu1, course1.students.all())

        # can GET, PATCH, PUT, DELETE its course's takes
        for takes in Takes.objects.filter(course=course1):
            response = self.put_student_course(takes.student, takes, dict(
                course=get_course_url(course1), grade=80,
            ))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(Takes.objects.get(pk=takes.pk).grade, 80)

            response = self.patch_student_course(takes.student, takes, dict(
                grade=70,
            ))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(Takes.objects.get(pk=takes.pk).grade, 70)

        for takes in Takes.objects.filter(course=course1):
            response = self.get_student_course_detail(takes.student, takes)
            self.assertTrue(self.is_course_inst_fields(response.data))
            response = self.delete_student_course(takes.student, takes)
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # cannot GET, PUT, PATCH, DELETE other course's takes
        for takes in Takes.objects.filter(course=course2):
            response = self.put_student_course(takes.student, takes, {})
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            response = self.patch_student_course(takes.student, takes, {})
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        for takes in Takes.objects.filter(course=course2):
            response = self.get_student_course_detail(takes.student, takes)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            response = self.delete_student_course(takes.student, takes)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_inst_add_stu_to_other_courses(self):
        """
        Test when an instructor adds a student to a course not given by itself.
        """
        course1 = factories.CourseFactory()
        course2 = factories.CourseFactory()
        inst1 = factories.InstructorTeachesCourseFactory(courses__course=course1)
        stu1 = factories.StudentFactory()

        self.force_authenticate_user(inst1.user)
        response = self.post_student_course(stu1, dict(
            course=get_course_url(course2),
        ))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class InstructorCoursesAPITests(APITestUtilsMixin, APITestCase):

    def get_instructor_course_list(self, inst):
        return self.client.get(reverse('api:instructor-course-list', kwargs={'parent_lookup_instructor': inst.pk}))

    def get_instructor_course_detail(self, inst, teaches):
        return self.client.get(reverse('api:instructor-course-detail',
                                       kwargs={'parent_lookup_instructor': inst.pk, 'pk': teaches.pk}))

    def post_instructor_course(self, inst, teaches_dict):
        return self.client.post(reverse('api:instructor-course-list', kwargs={'parent_lookup_instructor': inst.pk}),
                                teaches_dict)

    def put_instructor_course(self, inst, teaches, teaches_dict):
        return self.client.put(
            reverse('api:instructor-course-detail',
                    kwargs={'parent_lookup_instructor': inst.pk, 'pk': teaches.pk}),
            teaches_dict
        )

    def patch_instructor_course(self, inst, teaches, teaches_dict):
        return self.client.patch(
            reverse('api:instructor-course-detail',
                    kwargs={'parent_lookup_instructor': inst.pk, 'pk': teaches.pk}),
            teaches_dict
        )

    def delete_instructor_course(self, inst, teaches):
        return self.client.delete(reverse('api:instructor-course-detail',
                                          kwargs={'parent_lookup_instructor': inst.pk, 'pk': teaches.pk}))

    def is_view_all_fields(self, teaches_dict):
        return (set(teaches_dict.keys()) ==
                {'url', 'id', 'instructor', 'course'})

    def is_itself_fields(self, teaches_dict):
        return self.is_view_all_fields(teaches_dict)

    def is_course_stu_fields(self, teaches_dict):
        return self.is_view_all_fields(teaches_dict)

    def is_other_inst_fields(self, teaches_dict):
        return self.is_view_all_fields(teaches_dict)

    def test_student_access_inst_course(self):
        stu1 = factories.StudentFactory()
        course1 = factories.CourseFactory()
        inst1 = factories.InstructorFactory()
        teaches1 = factories.TeachesFactory(course=course1, instructor=inst1)
        inst2 = factories.InstructorFactory()
        teaches2 = factories.TeachesFactory(course=course1, instructor=inst2)

        self.force_authenticate_user(stu1.user)
        # cannot GET, POST, PUT, PATCH, DELETE before taking course
        response = self.get_instructor_course_list(inst1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        response = self.post_instructor_course(inst1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.put_instructor_course(inst1, teaches1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.patch_instructor_course(inst1, teaches1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.delete_instructor_course(inst1, teaches1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        takes = factories.TakesFactory(student=stu1, course=course1)

        # can GET after
        response = self.get_instructor_course_list(inst1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        response = self.get_instructor_course_detail(inst1, teaches1)
        self.assertTrue(self.is_course_stu_fields(response.data))
        # cannot POST, PUT, PATCH, DELETE after
        response = self.post_instructor_course(inst1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.put_instructor_course(inst1, teaches1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.patch_instructor_course(inst1, teaches1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.delete_instructor_course(inst1, teaches1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_inst_access_inst_course(self):
        course1 = factories.CourseFactory()
        inst1 = factories.InstructorFactory()
        inst2 = factories.InstructorFactory()
        teaches1 = factories.TeachesFactory(course=course1, instructor=inst1)

        self.force_authenticate_user(inst2.user)
        # cannot GET, POST, PUT, PATCH, DELETE other inst's teaches
        response = self.get_instructor_course_list(inst1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
        response = self.get_instructor_course_detail(inst1, teaches1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # can GET, POST, PATCH, DELETE after taking same course
        factories.TeachesFactory(course=course1, instructor=inst2)
        response = self.get_instructor_course_list(inst1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        response = self.get_instructor_course_detail(inst1, teaches1)
        self.assertTrue(self.is_other_inst_fields(response.data))

    @unittest.skipIf(skip_seperate_tests, skip_seperate_tests_reason)
    def test_add_course_to_other_inst(self):
        course1 = factories.CourseFactory()
        course2 = factories.CourseFactory()
        inst1 = factories.InstructorFactory()
        inst2 = factories.InstructorFactory()
        factories.TeachesFactory(course=course1, instructor=inst1)

        self.force_authenticate_user(inst1.user)

        # can add course given by itself
        response = self.post_instructor_course(inst2, dict(
            course=get_course_url(course1),
        ))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # cannot add course not given by itself
        response = self.post_instructor_course(inst2, dict(
            course=get_course_url(course2),
        ))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @unittest.skipIf(skip_seperate_tests, skip_seperate_tests_reason)
    def test_add_course_to_inst_itself(self):
        course1 = factories.CourseFactory()
        inst1 = factories.InstructorFactory()

        self.force_authenticate_user(inst1.user)

        # can add course to itself
        response = self.post_instructor_course(inst1, dict(
            course=get_course_url(course1),
        ))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # again, error
        response = self.post_instructor_course(inst1, dict(
            course=get_course_url(course1),
        ))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CourseAITests(APITestUtilsMixin, APITestCase):

    def get_course_list(self):
        return self.client.get(reverse('api:course-list'))

    def get_course_detail(self, course):
        return self.client.get(reverse('api:course-detail', kwargs={'pk': course.pk}))

    def post_course(self, course_dict):
        return self.client.post(reverse('api:course-list'), course_dict)

    def put_course(self, course, course_dict):
        return self.client.put(reverse('api:course-detail', kwargs={'pk': course.pk}), course_dict)

    def patch_course(self, course, course_dict):
        return self.client.patch(reverse('api:course-detail', kwargs={'pk': course.pk}), course_dict)

    def delete_course(self, course):
        return self.client.delete(reverse('api:course-detail', kwargs={'pk': course.pk}))

    def is_course_inst_fields(self, course_dict):
        return (set(course_dict.keys()) ==
                {'url', 'id', 'title', 'year', 'semester', 'description', 'min_group_size',
                 'max_group_size', 'instructors'})

    def is_normal_inst_fields(self, course_dict):
        return (set(course_dict.keys()) ==
                {'url', 'id', 'title', 'year', 'semester', 'description', 'instructors'})

    def is_course_stu_fields(self, course_dict):
        return self.is_course_inst_fields(course_dict)

    def is_normal_stu_fields(self, course_dict):
        return (set(course_dict.keys()) ==
                {'url', 'id', 'title', 'year', 'semester', 'description', })

    def test_get(self):
        stu1 = factories.StudentFactory()
        inst1 = factories.InstructorFactory()
        course1 = factories.CourseFactory()

        # base view
        self.force_authenticate_user(stu1.user)
        response = self.get_course_list()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        response = self.get_course_detail(course1)
        self.assertTrue(self.is_normal_stu_fields(response.data))

        self.force_authenticate_user(inst1.user)
        response = self.get_course_list()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        response = self.get_course_detail(course1)
        self.assertTrue(self.is_normal_inst_fields(response.data))

        # advanced view
        takes1 = factories.TakesFactory(student=stu1, course=course1)
        teaches1 = factories.TeachesFactory(instructor=inst1, course=course1)

        self.force_authenticate_user(stu1.user)
        response = self.get_course_list()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        response = self.get_course_detail(course1)
        self.assertTrue(self.is_course_stu_fields(response.data))

        self.force_authenticate_user(inst1.user)
        response = self.get_course_list()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        response = self.get_course_detail(course1)
        self.assertTrue(self.is_course_inst_fields(response.data))

        # restore to base view
        takes1.delete()
        teaches1.delete()
        self.force_authenticate_user(stu1.user)
        response = self.get_course_list()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        response = self.get_course_detail(course1)
        self.assertTrue(self.is_normal_stu_fields(response.data))

        self.force_authenticate_user(inst1.user)
        response = self.get_course_list()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        response = self.get_course_detail(course1)
        self.assertTrue(self.is_normal_inst_fields(response.data))

    @unittest.skipIf(skip_seperate_tests, skip_seperate_tests_reason)
    def test_post(self):
        self.client = APIClient()
        stu1 = factories.StudentFactory()
        inst1 = factories.InstructorFactory()

        # instructor can POST
        self.force_authenticate_user(inst1.user)
        response = self.post_course(dict(
            title='foobar', year='2005', semester='SPG', description='',
            instructors=[get_instructor_url(inst1)],
        ))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(inst1.courses.count(), 1)

        # POST without instructors
        response = self.post_course(dict(
            title='foobar', year='2006', semester='SPG', description='',
        ))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Course.objects.count(), 2)
        self.assertEqual(inst1.courses.count(), 1)

        # test required field
        response = self.post_course(dict(
            title='foobar',
        ))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.post_course(dict(
            title='foobar', year='2007'
        ))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.post_course(dict(
            title='foobar', year='2007', semester='SPG',
        ))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # test semester
        response = self.post_course(dict(
            title='foobar', year='2007', semester='Spring', description='',
        ))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.post_course(dict(
            title='foobar', year='2007', semester='AUT', description='',
        ))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # student cannot POST
        self.force_authenticate_user(stu1.user)
        response = self.post_course({})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_change(self):
        stu1 = factories.StudentFactory()
        inst1 = factories.InstructorFactory()
        course1 = factories.CourseFactory()

        # student cannot PUT, PATCH
        self.force_authenticate_user(stu1.user)
        response = self.put_course(course1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.patch_course(course1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # inst not giving the course cannot either
        self.force_authenticate_user(inst1.user)
        response = self.put_course(course1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.patch_course(course1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # inst can change after taking the course
        factories.TeachesFactory(instructor=inst1, course=course1)
        response = self.put_course(course1, dict(
            title='foobar', year='2007', semester='Spring',
        ))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.patch_course(course1, dict(
            title='barfoo',
        ))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete(self):
        stu1 = factories.StudentFactory()
        inst1 = factories.InstructorFactory()
        course1 = factories.CourseFactory()

        # student cannot DELETE
        self.force_authenticate_user(stu1.user)
        response = self.delete_course(course1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # inst not giving cannot DELETE
        self.force_authenticate_user(inst1.user)
        response = self.delete_course(course1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # inst can DELETE after taking the course
        factories.TeachesFactory(instructor=inst1, course=course1)
        response = self.delete_course(course1)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class CourseInstructorsAPITests(APITestUtilsMixin, APITestCase):

    def get_course_instructor_list(self, course):
        return self.client.get(reverse('api:course-instructor-list', kwargs={'parent_lookup_course': course.pk}))

    def get_course_instructor_detail(self, course, teaches):
        return self.client.get(reverse('api:course-instructor-detail',
                                       kwargs={'parent_lookup_course': course.pk, 'pk': teaches.pk}))

    def post_course_instructor(self, course, teaches_dict):
        return self.client.post(reverse('api:course-instructor-list', kwargs={'parent_lookup_course': course.pk}),
                                teaches_dict)

    def put_course_instructor(self, course, teaches, teaches_dict):
        return self.client.put(
            reverse('api:course-instructor-detail',
                    kwargs={'parent_lookup_course': course.pk, 'pk': teaches.pk}),
            teaches_dict
        )

    def patch_course_instructor(self, course, teaches, teaches_dict):
        return self.client.patch(
            reverse('api:course-instructor-detail',
                    kwargs={'parent_lookup_course': course.pk, 'pk': teaches.pk}),
            teaches_dict
        )

    def delete_course_instructor(self, course, teaches):
        return self.client.delete(reverse('api:course-instructor-detail',
                                          kwargs={'parent_lookup_course': course.pk, 'pk': teaches.pk}))

    def is_view_all_fields(self, teaches_dict):
        return (set(teaches_dict.keys()) ==
                {'url', 'id', 'instructor', 'course'})

    def is_course_inst_fields(self, teaches_dict):
        return self.is_view_all_fields(teaches_dict)

    def is_course_stu_fields(self, teaches_dict):
        return self.is_view_all_fields(teaches_dict)

    def test_get(self):
        stu1 = factories.StudentFactory()
        inst1 = factories.InstructorFactory()
        inst2 = factories.InstructorFactory()
        course1 = factories.CourseFactory()
        teaches1 = factories.TeachesFactory(instructor=inst1, course=course1)

        # student not taking the course cannot GET teaches
        self.force_authenticate_user(stu1.user)
        response = self.get_course_instructor_list(course1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        response = self.get_course_instructor_detail(course1, teaches1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # student can GET after taking
        takes1 = factories.TakesFactory(student=stu1, course=course1)
        response = self.get_course_instructor_detail(course1, teaches1)
        self.assertTrue(self.is_course_stu_fields(response.data))

        # instructor can GET its own course teaches
        response = self.get_course_instructor_list(course1)
        self.assertEqual(len(response.data), 1)

        response = self.get_course_instructor_detail(course1, teaches1)
        self.assertTrue(self.is_course_inst_fields(response.data))

        # course instructor can GET other course inst's teaches
        teaches2 = factories.TeachesFactory(instructor=inst2, course=course1)
        response = self.get_course_instructor_list(course1)
        self.assertEqual(len(response.data), 2)

        response = self.get_course_instructor_detail(course1, teaches2)
        self.assertTrue(self.is_course_inst_fields(response.data))

    @unittest.skipIf(skip_seperate_tests, skip_seperate_tests_reason)
    def test_post(self):
        stu1 = factories.StudentFactory()
        inst1 = factories.InstructorFactory()
        inst2 = factories.InstructorFactory()
        course1 = factories.CourseFactory()

        # instructor can POST to its own course
        factories.TeachesFactory(instructor=inst1, course=course1)
        self.force_authenticate_user(inst1.user)
        response = self.post_course_instructor(course1, dict(
            instructor=get_instructor_url(inst2),
        ))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(course1.is_given_by(inst2))

        # can POST itself to other course
        course2 = factories.CourseFactory()
        self.post_course_instructor(course2, dict(
            instructor=get_instructor_url(inst1)
        ))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(course2.is_given_by(inst1))

        # cannot POST other inst to other course
        self.force_authenticate_user(inst1.user)
        course3 = factories.CourseFactory()
        response = self.post_course_instructor(course3, dict(
            instructor=get_instructor_url(inst2)
        ))
        self.assertFalse(course3.is_given_by(inst2))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # student cannot POST
        self.force_authenticate_user(stu1.user)
        response = self.post_course_instructor(course1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_change(self):
        stu1 = factories.StudentFactory()
        inst1 = factories.InstructorFactory()
        inst2 = factories.InstructorFactory()
        course1 = factories.CourseFactory()
        teaches1 = factories.TeachesFactory(instructor=inst1, course=course1)

        # student cannot PUT or PATCH
        self.force_authenticate_user(stu1.user)
        response = self.put_course_instructor(course1, teaches1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.patch_course_instructor(course1, teaches1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # course instructor cannot PUT or PATCH
        self.force_authenticate_user(inst1.user)
        response = self.put_course_instructor(course1, teaches1, dict(
            instructor=get_instructor_url(inst2)
        ))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.patch_course_instructor(course1, teaches1, dict(
            instructor=get_instructor_url(inst2)
        ))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # normal instructor cannot
        self.force_authenticate_user(inst2.user)
        response = self.put_course_instructor(course1, teaches1, dict(
            instructor=get_instructor_url(inst2)
        ))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.patch_course_instructor(course1, teaches1, dict(
            instructor=get_instructor_url(inst2)
        ))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete(self):
        stu1 = factories.StudentFactory()
        inst1 = factories.InstructorFactory()
        inst2 = factories.InstructorFactory()
        course1 = factories.CourseFactory()
        teaches1 = factories.TeachesFactory(instructor=inst1, course=course1)

        # student cannot
        self.force_authenticate_user(stu1.user)
        response = self.delete_course_instructor(course1, teaches1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # normal inst cannot
        self.force_authenticate_user(inst2.user)
        response = self.delete_course_instructor(course1, teaches1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # course inst can DELETE itself
        self.force_authenticate_user(inst1.user)
        response = self.delete_course_instructor(course1, teaches1)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class CourseStudentsAPITests(APITestUtilsMixin, APITestCase):

    def get_course_student_list(self, course):
        return self.client.get(reverse('api:course-student-list', kwargs={'parent_lookup_course': course.pk}))

    def get_course_student_detail(self, course, takes):
        return self.client.get(reverse('api:course-student-detail',
                                       kwargs={'parent_lookup_course': course.pk, 'pk': takes.pk}))

    def post_course_student(self, course, takes_dict):
        return self.client.post(reverse('api:course-student-list', kwargs={'parent_lookup_course': course.pk}),
                                takes_dict)

    def put_course_student(self, course, takes, takes_dict):
        return self.client.put(
            reverse('api:course-student-detail',
                    kwargs={'parent_lookup_course': course.pk, 'pk': takes.pk}),
            takes_dict
        )

    def patch_course_student(self, course, takes, takes_dict):
        return self.client.patch(
            reverse('api:course-student-detail',
                    kwargs={'parent_lookup_course': course.pk, 'pk': takes.pk}),
            takes_dict
        )

    def delete_course_student(self, course, takes):
        return self.client.delete(reverse('api:course-student-detail',
                                          kwargs={'parent_lookup_course': course.pk, 'pk': takes.pk}))

    def is_view_all_fields(self, takes_dict):
        return (set(takes_dict.keys()) ==
                {'url', 'id', 'student', 'course', 'grade'})

    def is_course_inst_fields(self, takes_dict):
        return self.is_view_all_fields(takes_dict)

    def is_course_stu_fields(self, takes_dict):
        return self.is_view_all_fields(takes_dict)

    def is_other_course_stu_fields(self, takes_dict):
        return (set(takes_dict.keys()) ==
                {'url', 'id', 'student', 'course', })

    def test_get(self):
        stu1 = factories.StudentFactory()
        stu2 = factories.StudentFactory()
        course1 = factories.CourseFactory()
        takes2_1 = factories.TakesFactory(student=stu2, course=course1)

        # normal student cannot GET takes
        self.force_authenticate_user(stu1.user)
        response = self.get_course_student_list(course1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        response = self.get_course_student_detail(course1, takes2_1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # course student can GET
        self.force_authenticate_user(stu2.user)
        response = self.get_course_student_list(course1)
        self.assertEqual(len(response.data), 1)

        response = self.get_course_student_detail(course1, takes2_1)
        self.assertTrue(self.is_course_stu_fields(response.data))

        # course student can GET other course student
        takes1_1 = factories.TakesFactory(student=stu1, course=course1)
        response = self.get_course_student_detail(course1, takes1_1)
        self.assertTrue(self.is_other_course_stu_fields(response.data))

    @unittest.skipIf(skip_seperate_tests, skip_seperate_tests_reason)
    def test_post(self):
        stu1 = factories.StudentFactory()
        inst1 = factories.InstructorFactory()
        course1 = factories.CourseFactory()

        # student cannot POST
        self.force_authenticate_user(stu1.user)
        response = self.post_course_student(course1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # normal inst cannot POST
        self.force_authenticate_user(inst1.user)
        response = self.post_course_student(course1, dict(
            student=get_student_url(stu1),
        ))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # course inst can POST
        factories.TeachesFactory(instructor=inst1, course=course1)
        response = self.post_course_student(course1, dict(
            student=get_student_url(stu1),
        ))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(course1.students.count(), 1)

    def test_change(self):
        stu1 = factories.StudentFactory()
        inst1 = factories.InstructorFactory()
        course1 = factories.CourseFactory()
        takes1_1 = factories.TakesFactory(student=stu1, course=course1)

        # student cannot change
        self.force_authenticate_user(stu1.user)
        response = self.put_course_student(course1, takes1_1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.patch_course_student(course1, takes1_1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # normal inst cannot change
        self.force_authenticate_user(inst1.user)
        response = self.put_course_student(course1, takes1_1, {})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.patch_course_student(course1, takes1_1, {})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # course inst can change
        factories.TeachesFactory(instructor=inst1, course=course1)
        response = self.put_course_student(course1, takes1_1, dict(
            grade=70,
        ))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Takes.objects.get(pk=takes1_1.pk).grade, 70)

    def test_delete(self):
        stu1 = factories.StudentFactory()
        stu2 = factories.StudentFactory()
        inst1 = factories.InstructorFactory()
        course1 = factories.CourseFactory()
        takes1_1 = factories.TakesFactory(student=stu1, course=course1)

        # student cannot DELETE
        self.force_authenticate_user(stu1.user)
        response = self.delete_course_student(course1, takes1_1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.force_authenticate_user(stu2.user)
        response = self.delete_course_student(course1, takes1_1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # normal inst cannot DELETE
        self.force_authenticate_user(inst1.user)
        response = self.delete_course_student(course1, takes1_1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # course inst can DELETE
        factories.TeachesFactory(instructor=inst1, course=course1)
        response = self.delete_course_student(course1, takes1_1)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

