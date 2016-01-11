# -*- coding: utf-8 -*-
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from rest_framework.test import APIRequestFactory

from .factories import (
    StudentFactory, ClassFactory, UserFactory, CourseFactory,
)
from ..serializers import (
    StudentSerializer, StudentCoursesSerializer, WriteStudentCoursesSerializer,
)
from ..models import (
    Student,
)
from . import factories


def get_course_url(course):
    return reverse('api:course-detail', kwargs={'pk': course.pk})


def get_student_url(student):
    return reverse('api:student-detail', kwargs={'pk': student.pk})


class StudentTests(APITestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.request = self.factory.get('/')

        self.user_1 = UserFactory()
        self.cls_1 = ClassFactory()
        self.course_1 = CourseFactory()
        self.course_2 = CourseFactory()
        self.stu_data_1 = {
            'user': reverse('api:user-detail', args=[self.user_1.id], request=self.request),
            's_id': '2012211000',
            's_class': reverse('api:class-detail', args=[self.cls_1.id], request=self.request),
            'name': 'Merton Shanahan III',
        }

    def test_create_student(self):
        pass


class StudentCoursesTests(APITestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.request = self.factory.get('/')

    def test_save_without_grade(self):
        stu1 = factories.StudentFactory()
        course1 = factories.CourseFactory()

        serializer = StudentCoursesSerializer(data=dict(
            student=get_student_url(stu1),
            course=get_course_url(course1),
        ))
        self.assertTrue(serializer.is_valid())
        takes1 = serializer.save()
        self.assertEqual(takes1.grade, None)

    def test_save_with_grade(self):
        stu1 = factories.StudentFactory()
        course1 = factories.CourseFactory()

        serializer = StudentCoursesSerializer(data=dict(
            student=get_student_url(stu1),
            course=get_course_url(course1),
            grade='90',
        ))
        self.assertTrue(serializer.is_valid())
        takes1 = serializer.save()
        self.assertEqual(takes1.grade, 90)

