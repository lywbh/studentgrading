# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.test import APIClient
from guardian.shortcuts import assign_perm, remove_perm, get_objects_for_user

from . import factories
from ..models import (
    Student, Instructor,
    has_four_level_perm,
)


class StudentAPITests(APITestCase):

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

    def force_authenticate_user(self, user):
        self.client.force_authenticate(user=user)

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

    def test_api(self):
        cls1 = factories.ClassFactory()
        cls2 = factories.ClassFactory()
        course1 = factories.CourseFactory()
        course2 = factories.CourseFactory()
        stu_cls1_cs1_list = []
        stu_cls1_cs2_list = []
        stu_cls2_cs2_list = []
        stu_cls2_cs12_list = []
        for i in range(10):
            stu_cls1_cs1_list.append(factories.StudentTakesCourseFactory(s_class=cls1, courses__course=course1))
            stu_cls2_cs2_list.append(factories.StudentTakesCourseFactory(s_class=cls2, courses__course=course2))
            stu_cls1_cs2_list.append(factories.StudentTakesCourseFactory(s_class=cls1, courses__course=course2))
            stu = factories.StudentTakesCourseFactory(s_class=cls2, courses__course=course2)
            factories.TakesFactory(student=stu, course=course1)
            stu_cls2_cs12_list.append(stu)
        inst1 = factories.InstructorTeachesCourseFactory(courses__course=course1)
        inst2 = factories.InstructorTeachesCourseFactory(courses__course=course2)
        inst3 = factories.InstructorTeachesCourseFactory(courses__course=course1)
        factories.TeachesFactory(instructor=inst3, course=course2)

        # test cls1 cs1 stu
        for stu in stu_cls1_cs1_list:
            self.force_authenticate_user(stu.user)
            response = self.get_student_list()
            self.assertEqual(len(response.data), 20 + 10)
            self.force_authenticate_user(None)

        # test cls1 cs2 stu
        for stu in stu_cls1_cs2_list:
            self.force_authenticate_user(stu.user)
            response = self.get_student_list()
            self.assertEqual(len(response.data), 20 + 20)
            self.force_authenticate_user(None)

        # test cls2 cs2 stu
        for stu in stu_cls2_cs2_list:
            self.force_authenticate_user(stu.user)
            response = self.get_student_list()
            self.assertEqual(len(response.data), 20 + 10)
            self.force_authenticate_user(None)

        # test cls2 cs2 stu
        for stu in stu_cls2_cs12_list:
            self.force_authenticate_user(stu.user)
            response = self.get_student_list()
            self.assertEqual(len(response.data), 20 + 20)
            self.force_authenticate_user(None)


class InstructorAPITests(APITestCase):

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
                {'url', 'id', 'name', 'sex', 'inst_id', 'user', })

    def is_other_inst_fields(self, inst_dict):
        return (set(inst_dict.keys()) ==
                {'url', 'id', 'name', 'sex', 'inst_id', })

    def is_course_stu_fields(self, inst_dict):
        return (set(inst_dict.keys()) ==
                {'url', 'id', 'name', 'sex', })

    def force_authenticate_user(self, user):
        self.client.force_authenticate(user=user)

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


