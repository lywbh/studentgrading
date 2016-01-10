# -*- coding: utf-8 -*-
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from rest_framework.test import APIRequestFactory

from .factories import (
    StudentFactory, ClassFactory, UserFactory, CourseFactory,
)
from ..serializers import (
    StudentSerializer,
)
from ..models import (
    Student,
)


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
    pass
