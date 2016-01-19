import json

from django.core.urlresolvers import reverse

from rest_framework.test import APITestCase
from rest_framework import status

from . import factories
from ..models import User


def get_formatted_json(data):
    return json.dumps(data, indent=2)


class APITestUtilsMixin(object):

    def force_authenticate_user(self, user):
        self.client.force_authenticate(user=user)


class UserAPITests(APITestUtilsMixin, APITestCase):

    def get_user_list(self):
        return self.client.get(reverse('api:user-list'))

    def get_user_detail(self, user):
        return self.client.get(reverse('api:user-detail', kwargs=dict(pk=user.pk)))

    def put_user_detail(self, user, user_dict):
        return self.client.put(reverse('api:user-detail', kwargs=dict(pk=user.pk)), user_dict)

    def delete_user(self, user):
        return self.client.delete(reverse('api:user-detail', kwargs=dict(pk=user.pk)))

    def is_read_fields(self, data_dict):
        return (set(data_dict.keys()) ==
                {'url', 'id', 'username', 'date_joined', })

    def test_get_user(self):
        user1 = factories.UserFactory()
        user2 = factories.UserFactory()

        self.force_authenticate_user(user1)

        response = self.get_user_list()
        self.assertEqual(len(response.data), 1)

        response = self.get_user_detail(user1)
        self.assertTrue(self.is_read_fields(response.data))

        response = self.get_user_detail(user2)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_change_user(self):
        user1 = factories.UserFactory()

        self.force_authenticate_user(user1)
        response = self.put_user_detail(user1, dict(username='foobar'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(User.objects.get(pk=user1.pk).username, 'foobar')

        user2 = factories.UserFactory()
        self.force_authenticate_user(user2)

        response = self.put_user_detail(user1, dict(username='foobar'))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.put_user_detail(user2, dict(username='foobar'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete(self):
        user1 = factories.UserFactory()

        self.force_authenticate_user(user1)
        response = self.delete_user(user1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
