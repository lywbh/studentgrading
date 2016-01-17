# -*- coding: utf-8 -*-
from django.test import TestCase
from django.test.client import RequestFactory
from django.core.urlresolvers import reverse

from rest_framework.permissions import BasePermission
from rest_framework.views import APIView

from ..permissions import (CreateGroupPermission, )


class TestView(APIView):

    def test_permission(self, request):
        from rest_framework.request import Request

        request = Request(request)

        self.request = request

        for permission in self.get_permissions():
            if not permission.has_permission(request, self):
                return False

        return True


class PermissionsTestCase(TestCase):

    def setUp(self):
        self.requests = RequestFactory()

    def assertViewPermission(self, request, view_class, granted=True):
        view = view_class()
        result = view.test_permission(request)
        if granted:
            self.assertTrue(result)
        else:
            self.assertFalse(result)

    def test_create_group_permissions(self):

        class View1(TestView):
            permission_classes = (CreateGroupPermission, )

        request = self.requests.get(reverse('api:course-detail', kwargs={'pk': 1}))
        self.assertViewPermission(request, View1, True)
