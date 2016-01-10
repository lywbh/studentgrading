# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model

from rest_framework import permissions

from .models import (
    get_role_of, Student, Instructor, Course, has_four_level_perm,
)

from django.http import Http404

SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')
User = get_user_model()


class BaseObjectPermissions(permissions.DjangoObjectPermissions):
    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': ['%(app_label)s.view_%(model_name)s'],
        'HEAD': ['%(app_label)s.view_%(model_name)s'],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }


class StudentObjectPermissions(BaseObjectPermissions):
    pass


class StudentCoursesObjectPermissions(BaseObjectPermissions):
    pass


class FourLevelObjectPermissions(permissions.BasePermission):
    """
    A variant based on DjangoModelPermissions and DjangoObjectPermissions

    It ensures that the user is authenticated, and has the appropriate
    `add`/`change`/`delete` permissions on the model, plus the appropriate
    `add`/`delete`/any of the four-level `view`/any of the four-level `change`
    permissions on object.
    """

    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s',
                '%(app_label)s.view_%(model_name)s_base'],
        'OPTIONS': ['%(app_label)s.view_%(model_name)s',
                    '%(app_label)s.view_%(model_name)s_base'],
        'HEAD': ['%(app_label)s.view_%(model_name)s',
                 '%(app_label)s.view_%(model_name)s_base'],
        'PUT': ['%(app_label)s.change_%(model_name)s',
                '%(app_label)s.change_%(model_name)s_base'],
        'PATCH': ['%(app_label)s.change_%(model_name)s',
                  '%(app_label)s.change_%(model_name)s_base'],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }

    authenticated_users_only = True

    def get_required_permissions(self, method, model_cls):
        """
        Given a model and an HTTP method, return the list of permission
        codes that the user is required to have.
        """
        kwargs = {
            'app_label': model_cls._meta.app_label,
            'model_name': model_cls._meta.model_name
        }
        return [perm % kwargs for perm in self.perms_map[method]]

    def has_permission(self, request, view):
        # Workaround to ensure DjangoModelPermissions are not applied
        # to the root view when using DefaultRouter.
        if getattr(view, '_ignore_model_permissions', False):
            return True

        if hasattr(view, 'get_queryset'):
            queryset = view.get_queryset()
        else:
            queryset = getattr(view, 'queryset', None)

        assert queryset is not None, (
            'Cannot apply FourLevelModelPermissions on a view that '
            'does not set `.queryset` or have a `.get_queryset()` method.'
        )

        perms = self.get_required_permissions(request.method, queryset.model)

        return (
            request.user and
            (request.user.is_authenticated() or not self.authenticated_users_only) and
            # Repopulate the permission cache
            User.objects.get(pk=request.user.pk).has_perm(perms[0])
        )

    def get_required_object_permissions(self, method, model_cls):
        kwargs = {
            'app_label': model_cls._meta.app_label,
            'model_name': model_cls._meta.model_name
        }
        return [perm % kwargs for perm in self.perms_map[method]]

    def has_object_permission(self, request, view, obj):
        if hasattr(view, 'get_queryset'):
            queryset = view.get_queryset()
        else:
            queryset = getattr(view, 'queryset', None)

        assert queryset is not None, (
            'Cannot apply FourLevelObjectPermissions on a view that '
            'does not set `.queryset` or have a `.get_queryset()` method.'
        )

        model_cls = queryset.model
        # Repopulate the permission cache
        user = User.objects.get(pk=request.user.pk)

        perms = self.get_required_object_permissions(request.method, model_cls)

        if request.method in SAFE_METHODS + ('PUT', 'PATCH'):
            has_perm = has_four_level_perm(perms[1], user, obj)
        else:
            has_perm = user.has_perm(perms[0], obj)

        if not has_perm:
            # If the user does not have permissions we need to determine if
            # they have read permissions to see 403, or not, and simply see
            # a 404 response.

            if request.method in SAFE_METHODS:
                # Read permissions already checked and failed, no need
                # to make another lookup.
                raise Http404

            read_perms = self.get_required_object_permissions('GET', model_cls)
            has_read_perm = has_four_level_perm(read_perms[1], user, obj)
            if not has_read_perm:
                raise Http404

            # Has read permissions.
            return False

        return True