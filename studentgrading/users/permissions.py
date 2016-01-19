# -*- coding: utf-8 -*-
from rest_framework import permissions


class IsUserItself(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.is_staff:
            return True

        if request.method == 'DELETE':
            # Cannot DELETE
            return False

        return user == obj
