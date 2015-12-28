# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from ..models import Student


class StudentTests(APITestCase):

    def test_create_student(self):
        pass

