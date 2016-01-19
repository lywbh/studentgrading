# -*- coding: utf-8 -*-
import unittest
import json
import decimal
from datetime import timedelta

from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from . import factories
from ..models import (
    Student, Instructor, Course, Takes, Group,
)

User = get_user_model()

print_api_response = True
print_api_response_reason = "Print response to write docs."


def get_formatted_json(data):
    return json.dumps(data, indent=2)


def patch_params_to_url(url, params):
    if params:
        if url[-1] != '/':
            url += '/'
        url += '?'
    else:
        return url

    field = list(params.items())[0][0]
    value = params.pop(field)
    url += '{0}={1}'.format(field, value)
    for field, value in params.items():
        url += '&{0}={1}'.format(field, value)

    return url


def get_course_url(course):
    return reverse('api:course-detail', kwargs={'pk': course.pk})


def get_student_url(student):
    return reverse('api:student-detail', kwargs={'pk': student.pk})


def get_instructor_url(instructor):
    return reverse('api:instructor-detail', kwargs={'pk': instructor.pk})


class APITestUtilsMixin(object):

    def force_authenticate_user(self, user):
        self.client.force_authenticate(user=user)


class MyselfAPITests(APITestUtilsMixin, APITestCase):

    def get_myself(self):
        return self.client.get(reverse('api:myself'))

    def get(self):
        stu1 = factories.StudentFactory()
        self.force_authenticate_user(stu1.user)
        response = self.get_myself()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['url'], reverse('api:student-detail', kwargs=dict(pk=stu1.pk)))

        inst1 = factories.InstructorFactory()
        self.force_authenticate_user(inst1.user)
        response = self.get_myself()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['url'], reverse('api:instructor-detail', kwargs=dict(pk=inst1.pk)))

        admin = User.objects.create_superuser(username='foobar', password='foobar')
        self.force_authenticate_user(admin)
        response = self.get_myself()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class StudentAPITests(APITestUtilsMixin, APITestCase):

    def get_student_list(self):
        return self.client.get(reverse('api:student-list'))

    def filter_student_list(self, params):
        url = patch_params_to_url(reverse('api:student-list'),
                                  params)
        return self.client.get(url)

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
                {'url', 'id', 'name', 'sex', 's_id', 's_class', 'takes'})

    def is_itself_fields(self, data_dict):
        return (set(data_dict.keys()) ==
                {'url', 'id', 'name', 'sex', 's_id', 's_class', 'takes', 'user'})

    def test_filter_get(self):
        course1 = factories.CourseFactory()
        for i in range(4):
            factories.StudentTakesCourseFactory(courses__course=course1)
            factories.StudentFactory()

        inst1 = factories.InstructorTeachesCourseFactory(courses__course=course1)

        # against course
        self.force_authenticate_user(inst1.user)
        response = self.filter_student_list(dict(course=course1.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)

        # against course and group status
        stu1 = factories.StudentTakesCourseFactory(courses__course=course1)
        group1 = factories.GroupFactory(course=course1, leader=stu1)
        for i in range(2):
            factories.GroupMembershipFactory(group=group1,
                                             student=factories.StudentTakesCourseFactory(courses__course=course1))
        response = self.filter_student_list(dict(course=course1.pk, grouped=True))
        self.assertEqual(len(response.data), 3)

        response = self.filter_student_list(dict(course=course1.pk, grouped=False))
        self.assertEqual(len(response.data), 4)

        # other conditions
        course2 = factories.CourseFactory()
        factories.TakesFactory(student=stu1, course=course2)

        response = self.filter_student_list(dict(course=course2.pk, grouped=False))
        self.assertEqual(len(response.data), 1)

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

    @unittest.skipIf(print_api_response, print_api_response_reason)
    def test_print_get_student(self):
        course1 = factories.CourseFactory()
        cls1 = factories.ClassFactory()
        stu1 = factories.StudentTakesCourseFactory(s_class=cls1, courses__course=course1)
        stu2 = factories.StudentFactory(s_class=cls1)
        stu3 = factories.StudentTakesCourseFactory(courses__course=course1)

        self.force_authenticate_user(stu1.user)
        print(get_formatted_json(self.get_student_list().data))

        inst1 = factories.InstructorFactory()
        self.force_authenticate_user(inst1.user)
        print(get_formatted_json(self.get_student_list().data))


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
                {'url', 'id', 'name', 'sex', 'inst_id', 'user', 'teaches'})

    def is_other_inst_fields(self, inst_dict):
        return (set(inst_dict.keys()) ==
                {'url', 'id', 'name', 'sex', 'inst_id', 'teaches'})

    def is_course_stu_fields(self, inst_dict):
        return (set(inst_dict.keys()) ==
                {'url', 'id', 'name', 'sex', 'teaches'})

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

        # can GET course students'
        response = self.get_student_course_detail(stu2, takes2_1)
        self.assertTrue(self.is_course_stu_fields(response.data))
        # cannot POST, PUT, PATCH, DELETE others
        response = self.put_student_course(stu2, takes2_1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.patch_student_course(stu2, takes2_1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.delete_student_course(stu2, takes2_1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

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
                course=get_course_url(course1), grade='85.5',
            ))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(Takes.objects.get(pk=takes.pk).grade, decimal.Decimal('85.5'))

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

    @unittest.skipIf(print_api_response, print_api_response_reason)
    def test_print_takes(self):
        course1 = factories.CourseFactory()
        course2 = factories.CourseFactory()
        stu1 = factories.StudentFactory()
        stu2 = factories.StudentFactory()
        takes1_1 = factories.TakesFactory(course=course1, student=stu1)
        takes1_2 = factories.TakesFactory(course=course2, student=stu1)

        self.force_authenticate_user(stu1.user)
        print(get_formatted_json(self.get_student_course_list(stu1).data))


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
                 'max_group_size', 'instructors', 'groups'})

    def is_normal_inst_fields(self, course_dict):
        return (set(course_dict.keys()) ==
                {'url', 'id', 'title', 'year', 'semester', 'description', 'instructors'})

    def is_course_stu_fields(self, course_dict):
        return self.is_course_inst_fields(course_dict)

    def is_normal_stu_fields(self, course_dict):
        return (set(course_dict.keys()) ==
                {'url', 'id', 'title', 'year', 'semester', 'description', })

    def post_group(self, course, group_dict):
        return self.client.post(reverse('api:course-detail', kwargs={'pk': course.pk}) + 'add_group/', group_dict)

    def get_group_list(self, course):
        return self.client.get(reverse('api:course-group-list', kwargs={'parent_lookup_course': course.pk}))

    def get_group_detail(self, course, group):
        return self.client.get(reverse('api:course-group-detail', kwargs={'parent_lookup_course': course.pk,
                                                                          'pk': group.pk}))

    def is_group_fields(self, group_dict):
        return (set(group_dict.keys()) ==
                {'url', 'id', 'course', 'number', 'name', 'leader', 'members', })

    def get_giving_courses(self):
        return self.client.get(reverse('api:course-list') + 'giving/')

    def get_taking_courses(self):
        return self.client.get(reverse('api:course-list') + 'taking/')

    @unittest.skipIf(print_api_response, print_api_response_reason)
    def test_print_get(self):
        course1 = factories.CourseFactory()
        course2 = factories.CourseFactory()
        stu1 = factories.StudentTakesCourseFactory(courses__course=course1)
        inst1 = factories.InstructorTeachesCourseFactory(courses__course=course1)

        factories.InstructorTeachesCourseFactory(courses__course=course1)
        factories.GroupFactory(course=course1)
        factories.GroupFactory(course=course1)

        # GET a list of courses, including taking/giving or not course
        self.force_authenticate_user(stu1.user)
        response = self.get_course_list()
        print(get_formatted_json(response.data))

        # GET taking/giving course
        self.force_authenticate_user(stu1.user)
        response = self.get_course_detail(course2)
        print(get_formatted_json(response.data))

        # GET not taking/giving course
        self.force_authenticate_user(inst1.user)
        response = self.get_course_detail(course1)
        print(get_formatted_json(response.data))

    @unittest.skipIf(print_api_response, print_api_response_reason)
    def test_print_post(self):
        inst1 = factories.InstructorFactory()
        stu1 = factories.StudentFactory()

        print(get_formatted_json(dict(
            title='Software Engineering', yaer='2015',
            semester='AUT', description='Given by dxiao.',
            instructors=[get_instructor_url(inst1)]
        )))

        print(get_formatted_json(dict(
            student=get_course_url(stu1)
        )))

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

    def test_lazy_object(self):
        stu1 = factories.StudentFactory()
        inst1 = factories.InstructorFactory()
        course1 = factories.CourseFactory()

        self.force_authenticate_user(inst1.user)
        self.get_course_detail(course1)
        # instructor can POST
        response = self.post_course(dict(
            title='foobar', year='2005', semester='SPG', description='',
            instructors=[get_instructor_url(inst1)],
        ))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(inst1.courses.count(), 1)

    def test_post(self):
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

    def test_post_with_instructors(self):
        inst1 = factories.InstructorFactory()

        self.force_authenticate_user(inst1.user)
        response = self.post_course(dict(
            title='foobar', year='2007', semester='AUT', description='',
        ))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Course.objects.filter(instructors=inst1).exists())

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
            description="foobar", min_group_size=1, max_group_size=4,
        ))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        course1 = Course.objects.get(pk=course1.pk)
        self.assertEqual(course1.description, "foobar")
        self.assertEqual(course1.min_group_size, 1)
        self.assertEqual(course1.max_group_size, 4)

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

    def test_post_group(self):
        stu1 = factories.StudentFactory()
        inst1 = factories.InstructorFactory()
        course1 = factories.CourseFactory()

        # stu not in course cannot
        self.force_authenticate_user(stu1.user)
        response = self.post_group(course1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # inst not in course cannnot
        self.force_authenticate_user(inst1.user)
        response = self.post_group(course1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # stu already in a group cannot
        group1 = factories.GroupFactory(course=course1)
        factories.TakesFactory(student=stu1, course=course1)
        factories.GroupMembershipFactory(student=stu1, group=group1)
        self.force_authenticate_user(stu1.user)
        response = self.post_group(course1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # course inst can
        factories.TeachesFactory(instructor=inst1, course=course1)
        stu2 = factories.StudentTakesCourseFactory(courses__course=course1)
        self.force_authenticate_user(inst1.user)
        response = self.post_group(course1, dict(
            name='success', leader=get_student_url(stu2),
        ))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # student not in a group can
        stu3 = factories.StudentTakesCourseFactory(courses__course=course1)
        self.force_authenticate_user(stu3.user)
        response = self.post_group(course1, dict(
            name='success', leader=get_student_url(stu3), members=[],
        ))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # test add members
        stu4 = factories.StudentTakesCourseFactory(courses__course=course1)
        stu5 = factories.StudentTakesCourseFactory(courses__course=course1)
        stu6 = factories.StudentTakesCourseFactory(courses__course=course1)
        self.force_authenticate_user(stu4.user)
        response = self.post_group(course1, dict(
            name='success', leader=get_student_url(stu4),
            members=[get_student_url(stu5), get_student_url(stu6)]
        ))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        group2 = course1.groups.get(leader=stu4)
        self.assertEqual(group2.members.count(), 2)

    def test_stu_get_group(self):
        course1 = factories.CourseFactory()
        group1 = factories.GroupFactory(course=course1)
        stu1 = factories.StudentFactory()

        for i in range(5):
            factories.GroupFactory()

        # normal student cannot get
        self.force_authenticate_user(stu1.user)
        response = self.get_group_list(course1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        response = self.get_group_detail(course1, group1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # course stu can get
        factories.TakesFactory(student=stu1, course=course1)
        response = self.get_group_list(course1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        response = self.get_group_detail(course1, group1)
        self.assertTrue(self.is_group_fields(response.data))

    def test_inst_get_group(self):
        course1 = factories.CourseFactory()
        group1 = factories.GroupFactory(course=course1)
        inst1 = factories.InstructorFactory()

        for i in range(5):
            factories.GroupFactory()

        # normal inst cannot
        self.force_authenticate_user(inst1.user)
        response = self.get_group_list(course1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        response = self.get_group_detail(course1, group1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # course inst can
        factories.TeachesFactory(instructor=inst1, course=course1)

        response = self.get_group_list(course1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        response = self.get_group_detail(course1, group1)
        self.assertTrue(self.is_group_fields(response.data))

    def test_get_giving(self):
        inst1 = factories.InstructorFactory()
        for i in range(3):
            factories.TeachesFactory(instructor=inst1, course=factories.CourseFactory())
            factories.CourseFactory()

        self.force_authenticate_user(inst1.user)
        response = self.get_giving_courses()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

        self.force_authenticate_user(factories.StudentFactory().user)
        response = self.get_giving_courses()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_taking(self):
        stu1 = factories.StudentFactory()
        for i in range(3):
            factories.TakesFactory(student=stu1, course=factories.CourseFactory())
            factories.CourseFactory()

        self.force_authenticate_user(stu1.user)
        response = self.get_taking_courses()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

        self.force_authenticate_user(factories.InstructorFactory().user)
        response = self.get_taking_courses()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @unittest.skipIf(print_api_response, print_api_response_reason)
    def test_print_post_group(self):
        course1 = factories.CourseFactory()
        inst1 = factories.InstructorTeachesCourseFactory(courses__course=course1)
        stu1 = factories.StudentFactory()
        stu2 = factories.StudentFactory()
        stu3 = factories.StudentFactory()

        self.force_authenticate_user(inst1.user)
        print(get_formatted_json(dict(name='success', leader=get_student_url(stu1),
              members=[get_student_url(stu2), get_student_url(stu3)])))

    @unittest.skipIf(print_api_response, print_api_response_reason)
    def test_print_get_group(self):
        course1 = factories.CourseFactory()
        group1 = factories.GroupFactory(course=course1)
        group2 = factories.GroupFactory(course=course1)
        stu1 = factories.StudentTakesCourseFactory(courses__course=course1)

        for i in range(2):
            member1 = factories.StudentTakesCourseFactory(courses__course=course1)
            factories.GroupMembershipFactory(student=member1, group=group1)
            member2 = factories.StudentTakesCourseFactory(courses__course=course1)
            factories.GroupMembershipFactory(student=member2, group=group2)

        # get list
        self.force_authenticate_user(stu1.user)
        print(get_formatted_json(self.get_group_list(course1).data))

        # get group
        print(get_formatted_json(self.get_group_detail(course1, group1).data))


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

    def test_test(self):
        stu1 = factories.StudentFactory()
        course1 = factories.CourseFactory()

        self.force_authenticate_user(stu1.user)
        self.get_course_instructor_list(course1)


class CourseTakesAPITests(APITestUtilsMixin, APITestCase):

    def get_course_student_list(self, course):
        return self.client.get(reverse('api:course-takes-list', kwargs={'parent_lookup_course': course.pk}))

    def get_course_student_detail(self, course, takes):
        return self.client.get(reverse('api:course-takes-detail',
                                       kwargs={'parent_lookup_course': course.pk, 'pk': takes.pk}))

    def post_course_student(self, course, takes_dict):
        return self.client.post(reverse('api:course-takes-list', kwargs={'parent_lookup_course': course.pk}),
                                takes_dict)

    def put_course_student(self, course, takes, takes_dict):
        return self.client.put(
            reverse('api:course-takes-detail',
                    kwargs={'parent_lookup_course': course.pk, 'pk': takes.pk}),
            takes_dict
        )

    def patch_course_student(self, course, takes, takes_dict):
        return self.client.patch(
            reverse('api:course-takes-detail',
                    kwargs={'parent_lookup_course': course.pk, 'pk': takes.pk}),
            takes_dict
        )

    def delete_course_student(self, course, takes):
        return self.client.delete(reverse('api:course-takes-detail',
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
            student=get_student_url(stu1), grade=80,
        ))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(course1.students.count(), 1)
        self.assertEqual(stu1.takes.all()[0].grade, decimal.Decimal('80'))

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

    @unittest.skipIf(print_api_response, print_api_response_reason)
    def test_print_get(self):
        course1 = factories.CourseFactory()
        inst1 = factories.InstructorTeachesCourseFactory(courses__course=course1)
        stu1 = factories.StudentTakesCourseFactory(courses__course=course1)
        stu2 = factories.StudentTakesCourseFactory(courses__course=course1)

        self.force_authenticate_user(stu1.user)
        print(get_formatted_json(self.get_course_student_list(course1).data))

        self.force_authenticate_user(inst1.user)
        print(get_formatted_json(self.get_course_student_list(course1).data))


class GroupAPITests(APITestUtilsMixin, APITestCase):

    def setUp(self):
        self.admin = User.objects.create_superuser(username='foobar', password='foobar')

    def get_group_list(self):
        return self.client.get(reverse('api:group-list'))

    def filter_group_list(self, params):
        url = patch_params_to_url(reverse('api:group-list'),
                                  params)
        return self.client.get(url)

    def get_group_detail(self, group):
        return self.client.get(reverse('api:group-detail', kwargs={'pk': group.pk}))

    def patch_group(self, group, data_dict):
        return self.client.patch(reverse('api:group-detail', kwargs={'pk': group.pk}), data_dict)

    def delete_group(self, group):
        return self.client.delete(reverse('api:group-detail', kwargs={'pk': group.pk}))

    def is_group_fields(self, group_dict):
            return (set(group_dict.keys()) ==
                    {'url', 'id', 'course', 'number', 'name', 'leader', 'members', })

    def test_filter_get(self):
        course1 = factories.CourseFactory()
        stu1 = factories.StudentTakesCourseFactory(courses__course=course1)
        stu2 = factories.StudentTakesCourseFactory(courses__course=course1)
        inst1 = factories.InstructorTeachesCourseFactory(courses__course=course1)

        for i in range(2):
            factories.GroupFactory(course=course1)

        group1 = factories.GroupFactory(course=course1, leader=stu1)
        factories.GroupMembershipFactory(group=group1, student=stu2)

        course2 = factories.CourseFactory()
        factories.TakesFactory(course=course2, student=stu2)
        factories.TakesFactory(course=course2, student=stu1)
        stu4 = factories.StudentTakesCourseFactory(courses__course=course1)

        group2 = factories.GroupFactory(course=course2, leader=stu1)
        factories.GroupMembershipFactory(group=group2, student=stu2)

        # login as admin
        self.force_authenticate_user(self.admin)

        response = self.filter_group_list(dict(course=course1.pk))
        self.assertEqual(len(response.data), 3)

        response = self.filter_group_list(dict(leader=stu1.pk))
        self.assertEqual(len(response.data), 2)

        response = self.filter_group_list(dict(has_member=stu2.pk))
        self.assertEqual(len(response.data), 2)

        response = self.filter_group_list(dict(has_student=stu2.pk))
        self.assertEqual(len(response.data), 2)
        response = self.filter_group_list(dict(has_student=stu1.pk))
        self.assertEqual(len(response.data), 2)

        # has_student
        stu3 = factories.StudentTakesCourseFactory(courses__course=course2)
        factories.TakesFactory(course=course1, student=stu3)
        group3 = factories.GroupFactory(course=course2, leader=stu3)
        factories.GroupMembershipFactory(group=group1, student=stu3)

        response = self.filter_group_list(dict(has_student=stu2.pk))
        self.assertEqual(len(response.data), 2)

    def test_stu_get_group(self):
        course1 = factories.CourseFactory()
        group1 = factories.GroupFactory(course=course1)
        stu1 = factories.StudentFactory()

        for i in range(5):
            factories.GroupFactory()

        # normal student cannot get
        self.force_authenticate_user(stu1.user)
        response = self.get_group_list()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        response = self.get_group_detail(group1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # course stu can get
        factories.TakesFactory(student=stu1, course=course1)
        response = self.get_group_list()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        response = self.get_group_detail(group1)
        self.assertTrue(self.is_group_fields(response.data))

    def test_inst_get_group(self):
        course1 = factories.CourseFactory()
        group1 = factories.GroupFactory(course=course1)
        inst1 = factories.InstructorFactory()

        for i in range(5):
            factories.GroupFactory()

        # normal inst cannot
        self.force_authenticate_user(inst1.user)
        response = self.get_group_list()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        response = self.get_group_detail(group1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # course inst can
        factories.TeachesFactory(instructor=inst1, course=course1)

        response = self.get_group_list()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        response = self.get_group_detail(group1)
        self.assertTrue(self.is_group_fields(response.data))

    def test_stu_change_group(self):
        course1 = factories.CourseFactory()
        group1 = factories.GroupFactory(course=course1)
        stu1 = factories.StudentFactory()

        # normal student cannot
        self.force_authenticate_user(stu1.user)
        response = self.patch_group(group1, {})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # course student cannot
        factories.TakesFactory(student=stu1, course=course1)
        response = self.patch_group(group1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # group members cannot
        factories.GroupMembershipFactory(student=stu1, group=group1)
        response = self.patch_group(group1, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # group leader can
        grp1_leader = group1.leader
        self.force_authenticate_user(grp1_leader.user)
        response = self.patch_group(group1, dict(
            name='foobar',
        ))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        group1 = Group.objects.get(pk=group1.pk)
        self.assertEqual(group1.name, 'foobar')

    def test_change_leader(self):
        course1 = factories.CourseFactory()
        stu1 = factories.StudentTakesCourseFactory(courses__course=course1)
        stu2 = factories.StudentTakesCourseFactory(courses__course=course1)
        group1 = factories.GroupFactory(course=course1, leader=stu1)
        factories.GroupMembershipFactory(student=stu2, group=group1)

        # member cannot change
        self.force_authenticate_user(stu2.user)
        response = self.patch_group(group1, dict(
            leader=get_student_url(stu2),
        ))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # leader can change
        self.force_authenticate_user(stu1.user)
        response = self.patch_group(group1, dict(
            leader=get_student_url(stu2),
        ))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        group1 = Group.objects.get(pk=group1.pk)
        self.assertEqual(group1.leader, stu2)
        self.assertIn(stu1, group1.members.all())
        self.assertNotIn(stu2, group1.members.all())

        # course inst can change
        inst1 = factories.InstructorTeachesCourseFactory(courses__course=course1)
        self.force_authenticate_user(inst1.user)
        response = self.patch_group(group1, dict(
            leader=get_student_url(stu1),
        ))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        group1 = Group.objects.get(pk=group1.pk)
        self.assertEqual(group1.leader, stu1)
        self.assertIn(stu2, group1.members.all())
        self.assertNotIn(stu1, group1.members.all())

        # stay unchanged
        response = self.patch_group(group1, dict(
            leader=get_student_url(stu1),
        ))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        group1 = Group.objects.get(pk=group1.pk)
        self.assertEqual(group1.leader, stu1)

    def test_delete_group(self):
        course1 = factories.CourseFactory()
        stu1 = factories.StudentTakesCourseFactory(courses__course=course1)
        inst1 = factories.InstructorTeachesCourseFactory(courses__course=course1)
        group1 = factories.GroupFactory(leader=stu1, course=course1)

        # leader cannot delete
        self.force_authenticate_user(stu1.user)
        response = self.delete_group(group1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        inst2 = factories.InstructorFactory()
        # non-course inst cannot
        self.force_authenticate_user(inst2.user)
        response = self.delete_group(group1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # course inst can delete
        self.force_authenticate_user(inst1.user)
        response = self.delete_group(group1)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @unittest.skipIf(print_api_response, print_api_response_reason)
    def test_print_get_group(self):
        course1 = factories.CourseFactory()
        group1 = factories.GroupFactory(course=course1)
        group2 = factories.GroupFactory(course=course1)
        stu1 = factories.StudentTakesCourseFactory(courses__course=course1)

        for i in range(2):
            member1 = factories.StudentTakesCourseFactory(courses__course=course1)
            factories.GroupMembershipFactory(student=member1, group=group1)
            member2 = factories.StudentTakesCourseFactory(courses__course=course1)
            factories.GroupMembershipFactory(student=member2, group=group2)

        # get list
        self.force_authenticate_user(stu1.user)
        print(get_formatted_json(self.get_group_list().data))

        # get group
        print(get_formatted_json(self.get_group_detail(group1).data))


class AssignmentAPITests(APITestUtilsMixin, APITestCase):

    def get_assignment_list(self):
        return self.client.get(reverse('api:assignment-list'))

    def filter_assignment_list(self, params):
        url = patch_params_to_url(reverse('api:assignment-list'),
                                  params)
        return self.client.get(url)

    def get_assignment_detail(self, assignment):
        return self.client.get(reverse('api:assignment-detail', kwargs={'pk': assignment.pk}))

    def post_assignment(self, assignment_dict):
        return self.client.post(reverse('api:assignment-list'), assignment_dict)

    def put_assignment(self, assignment, assignment_dict):
        return self.client.put(reverse('api:assignment-detail', kwargs={'pk': assignment.pk}), assignment_dict)

    def patch_assignment(self, assignment, assignment_dict):
        return self.client.patch(reverse('api:assignment-detail', kwargs={'pk': assignment.pk}), assignment_dict)

    def delete_assignment(self, assignment):
        return self.client.delete(reverse('api:assignment-detail', kwargs={'pk': assignment.pk}))

    def is_read_field(self, data_dict):
        return (set(data_dict.keys()) ==
                {'url', 'id', 'course', 'title', 'description', 'deadline',
                 'assigned_time', 'grade_ratio', 'number'})

    def test_get_assignment(self):
        course1 = factories.CourseFactory()
        a1 = factories.AssignmentFactory(course=course1)
        a2 = factories.AssignmentFactory(course=course1)

        inst1 = factories.InstructorFactory()
        self.force_authenticate_user(inst1.user)

        response = self.get_assignment_list()
        self.assertEqual(len(response.data), 2)

        response = self.get_assignment_detail(a1)
        self.assertTrue(self.is_read_field(response.data))

    def test_filter_get(self):
        course1 = factories.CourseFactory()
        course2 = factories.CourseFactory()
        a1 = factories.AssignmentFactory(course=course1)
        a2 = factories.AssignmentFactory(course=course2)
        a3 = factories.AssignmentFactory(course=course2)

        inst1 = factories.InstructorFactory()
        self.force_authenticate_user(inst1.user)

        response = self.filter_assignment_list(dict(course=course1.pk))
        self.assertEqual(len(response.data), 1)

        response = self.filter_assignment_list(dict(course=course2.pk))
        self.assertEqual(len(response.data), 2)

    def test_post_assignment(self):
        course1 = factories.CourseFactory()
        inst1 = factories.InstructorTeachesCourseFactory(courses__course=course1)

        self.force_authenticate_user(inst1.user)
        response = self.post_assignment(dict(
            course=get_course_url(course1), title='Assignment1', grade_ratio='0.1',
        ))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(course1.assignments.count(), 1)

        # test create will all fields
        response = self.post_assignment(dict(
            course=get_course_url(course1), title='Assignment2', grade_ratio='0.1',
            description='Blablaba', deadline=(timezone.now() + timedelta(days=3)),
        ))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(course1.assignments.count(), 2)

        # other insts post
        inst2 = factories.InstructorFactory()

        self.force_authenticate_user(inst2.user)
        response = self.post_assignment(dict(
            course=get_course_url(course1), title='Assignment1', grade_ratio='0.1',
        ))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_assignment(self):
        course1 = factories.CourseFactory()
        inst1 = factories.InstructorTeachesCourseFactory(courses__course=course1)
        a1 = factories.AssignmentFactory(course=course1)

        self.force_authenticate_user(inst1.user)
        response = self.put_assignment(a1, dict(
            title='Assignment2', grade_ratio='0.1',
            description='Blablaba', deadline=(timezone.now() + timedelta(days=3)),
        ))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.patch_assignment(a1, dict(
            title='Assignment5', grade_ratio='0.2',
        ))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_assignment(self):
        course1 = factories.CourseFactory()
        inst1 = factories.InstructorTeachesCourseFactory(courses__course=course1)
        a1 = factories.AssignmentFactory(course=course1)

        self.force_authenticate_user(inst1.user)
        response = self.delete_assignment(a1)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)