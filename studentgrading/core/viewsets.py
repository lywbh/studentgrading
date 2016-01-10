# -*- coding: utf-8 -*-
from rest_framework import viewsets, filters, mixins, status, generics
from rest_framework.response import Response

from rest_framework_extensions.mixins import NestedViewSetMixin
from guardian.shortcuts import get_objects_for_user

from .serializers import (
    StudentSerializer, ReadStudentSerializer,
    InstructorSerializer, ReadInstructorSerializer,
    ClassSerializer, CourseSerializer,
    AdminStudentCoursesSerializer, NormalStudentCoursesSerializer,
)
from .models import (
    has_four_level_perm,
    Student, Class, Course, Takes, Instructor,
)
from .permissions import (
    StudentObjectPermissions, StudentCoursesObjectPermissions,
    FourLevelObjectPermissions
)


# -----------------------------------------------------------------------------
# Filters
# -----------------------------------------------------------------------------
class FourLevelObjectPermissionsFilter(filters.BaseFilterBackend):
    """
    A filter backend that limits results to those where the requesting user
    has four-level read object level permissions.

    A variant of DjangoObjectPermissionsFilter.
    """
    perm_formats = ['%(app_label)s.view_%(model_name)s',
                    '%(app_label)s.view_%(model_name)s_base',
                    '%(app_label)s.view_%(model_name)s_normal',
                    '%(app_label)s.view_%(model_name)s_advanced']

    def filter_queryset(self, request, queryset, view):
        user = request.user
        model_cls = queryset.model
        kwargs = {
            'app_label': model_cls._meta.app_label,
            'model_name': model_cls._meta.model_name
        }
        permissions = [perm % kwargs for perm in self.perm_formats]
        return get_objects_for_user(user, permissions, queryset,
                                    any_perm=True, accept_global_perms=False)


# -----------------------------------------------------------------------------
# Custom Base ViewSet
# -----------------------------------------------------------------------------
class FourLevelPermCreateModelMixin(mixins.CreateModelMixin):
    def create(self, request, *args, **kwargs):
        serializer_class = self.get_write_serializer_class()
        serializer = serializer_class(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class FourLevelPermListModelMixin(mixins.ListModelMixin):
    def list(self, request, *args, **kwargs):
        serializer_class = self.get_read_serializer_class()
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = serializer_class(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = serializer_class(queryset, many=True, context=self.get_serializer_context())
        return Response(serializer.data)


class FourLevelPermRetrieveModelMixin(mixins.RetrieveModelMixin):
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer_class = self.get_read_serializer_class()
        serializer = serializer_class(instance, context=self.get_serializer_context())
        return Response(serializer.data)


class FourLevelPermUpdateModelMixin(mixins.UpdateModelMixin):
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        queryset = self.get_queryset()
        perm_kwargs = {
            'app_label': queryset.model._meta.app_label,
            'model_name': queryset.model._meta.model_name,
        }
        all_perm = '{app_label}.change_{model_name}'.format(**perm_kwargs)
        base_perm = all_perm + '_base'
        normal_perm = all_perm + '_normal'
        advanced_perm = all_perm + '_advanced'
        user = request.user

        serializer_class = self.get_write_serializer_class()
        if not user.has_perm(all_perm, instance):
            serializer_class = self.get_advanced_write_serializer_class()
            if not user.has_perm(advanced_perm, instance):
                serializer_class = self.get_normal_write_serializer_class()
                if not user.has_perm(normal_perm, instance):
                    serializer_class = self.get_base_write_serializer_class()
        serializer = serializer_class(instance, data=request.data, partial=partial,
                                      context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


class FourLevelPermDestroyModelMixin(mixins.DestroyModelMixin):
    pass


class FourLevelPermGenericViewSet(viewsets.GenericViewSet):
    read_serializer_class = None
    write_serializer_class = None
    base_write_serializer_class = None
    normal_write_serializer_class = None
    advanced_write_serializer_class = None

    def get_read_serializer_class(self):
        assert self.read_serializer_class is not None, (
            "'%s' should either include a `read_serializer_class` attribute, "
            "or override the `get_read_serializer_class()` method."
            % self.__class__.__name__
        )
        return self.read_serializer_class

    def get_write_serializer_class(self):
        assert self.write_serializer_class is not None, (
            "'%s' should either include a `write_serializer_class` attribute, "
            "or override the `get_write_serializer_class()` method."
            % self.__class__.__name__
        )
        return self.write_serializer_class

    def get_base_write_serializer_class(self):
        assert self.base_write_serializer_class is not None, (
            "'%s' should either include a `base_write_serializer_class` attribute, "
            "or override the `get_base_write_serializer_class()` method."
            % self.__class__.__name__
        )
        return self.base_write_serializer_class

    def get_normal_write_serializer_class(self):
        assert self.normal_write_serializer_class is not None, (
            "'%s' should either include a `normal_write_serializer_class` attribute, "
            "or override the `get_normal_write_serializer_class()` method."
            % self.__class__.__name__
        )
        return self.normal_write_serializer_class

    def get_advanced_write_serializer_class(self):
        assert self.advanced_write_serializer_class is not None, (
            "'%s' should either include a `advanced_write_serializer_class` attribute, "
            "or override the `get_advanced_write_serializer_class()` method."
            % self.__class__.__name__
        )
        return self.advanced_write_serializer_class


class FourLevelPermModelViewSet(FourLevelPermCreateModelMixin,
                                FourLevelPermListModelMixin,
                                FourLevelPermRetrieveModelMixin,
                                FourLevelPermUpdateModelMixin,
                                FourLevelPermDestroyModelMixin,
                                FourLevelPermGenericViewSet):
    pass


# -----------------------------------------------------------------------------
# Student ViewSets
# -----------------------------------------------------------------------------
class StudentViewSet(FourLevelPermModelViewSet):
    queryset = Student.objects.all()
    filter_backends = (FourLevelObjectPermissionsFilter,
                       filters.DjangoFilterBackend, )
    filter_fields = ('s_class', )
    permission_classes = (FourLevelObjectPermissions, )
    serializer_class = ReadStudentSerializer    # add this to ensure browsable api is okay

    read_serializer_class = ReadStudentSerializer
    write_serializer_class = StudentSerializer
    base_write_serializer_class = write_serializer_class
    normal_write_serializer_class = write_serializer_class
    advanced_write_serializer_class = write_serializer_class


class StudentCoursesViewSet(NestedViewSetMixin, viewsets.ModelViewSet):

    queryset = Takes.objects.all()
    filter_backends = (filters.DjangoObjectPermissionsFilter, )
    permission_classes = (StudentCoursesObjectPermissions, )

    def get_serializer_class(self):
        if self.request.user.is_staff:
            return AdminStudentCoursesSerializer
        return NormalStudentCoursesSerializer


# -----------------------------------------------------------------------------
# Instructor ViewSets
# -----------------------------------------------------------------------------
class InstructorViewSet(FourLevelPermModelViewSet):
    queryset = Instructor.objects.all()
    filter_backends = (FourLevelObjectPermissionsFilter, )
    permission_classes = (FourLevelObjectPermissions, )
    serializer_class = ReadInstructorSerializer     # add this to ensure browsable api is okay

    read_serializer_class = ReadInstructorSerializer
    write_serializer_class = InstructorSerializer
    base_write_serializer_class = write_serializer_class
    normal_write_serializer_class = write_serializer_class
    advanced_write_serializer_class = write_serializer_class


class ClassViewSet(viewsets.ModelViewSet):

    queryset = Class.objects.all()
    serializer_class = ClassSerializer


class CourseViewSet(viewsets.ModelViewSet):

    queryset = Course.objects.all()
    serializer_class = CourseSerializer
