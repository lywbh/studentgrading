# -*- coding: utf-8 -*-
from rest_framework import viewsets, filters, mixins, status
from rest_framework.response import Response
from rest_framework.relations import reverse
from rest_framework.decorators import detail_route, list_route
from rest_framework.views import APIView

from rest_framework_extensions.mixins import NestedViewSetMixin
from guardian.shortcuts import get_objects_for_user

from .serializers import (
    CreateStudentSerializer, ReadStudentSerializer,
    CreateStudentCoursesSerializer, ReadStudentCoursesSerializer, BaseWriteStudentCoursesSerializer,
    CreateInstructorSerializer, ReadInstructorSerializer,
    CreateInstructorCoursesSerializer, ReadInstructorCoursesSerializer,
    CreateCourseSerializer, ReadCourseSerializer, BaseWriteCourseSerializer,
    CourseInstructorsSerializer, ReadCourseInstructorsSerializer,
    CreateCourseTakesSerializer, ReadCourseTakesSerializer, BaseWriteCourseTakesSerializer,
    ReadGroupSerializer, CreateGroupSerializer, WriteGroupSerializer,
    ClassSerializer,
)
from .models import (
    Student, Class, Course, Takes, Instructor, Teaches, Group,
    get_role_of,
)
from .permissions import (
    FourLevelObjectPermissions, CreateGroupPermission, IsInstructor, IsStudent,
)
from . import filters as my_filters


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
        serializer_data = self.get_serializer_data(request, *args, **kwargs)
        serializer = serializer_class(data=serializer_data, context=self.get_serializer_context())
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
        normal_perm = all_perm + '_normal'
        advanced_perm = all_perm + '_advanced'
        user = request.user

        serializer_data = self.get_serializer_data(request, *args, **kwargs)
        serializer_class = self.get_write_serializer_class()
        if not user.has_perm(all_perm, instance):
            serializer_class = self.get_advanced_write_serializer_class()
            if not user.has_perm(advanced_perm, instance):
                serializer_class = self.get_normal_write_serializer_class()
                if not user.has_perm(normal_perm, instance):
                    serializer_class = self.get_base_write_serializer_class()
        serializer = serializer_class(instance, data=serializer_data, partial=partial,
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

    def get_serializer_data(self, request, *args, **kwargs):
        return request.data


class FourLevelPermModelViewSet(FourLevelPermCreateModelMixin,
                                FourLevelPermListModelMixin,
                                FourLevelPermRetrieveModelMixin,
                                FourLevelPermUpdateModelMixin,
                                FourLevelPermDestroyModelMixin,
                                FourLevelPermGenericViewSet):
    pass


class FourLevelPermNestedGenericViewSet(NestedViewSetMixin,
                                        FourLevelPermGenericViewSet):

    def get_serializer_data(self, request, *args, **kwargs):
        data = request.data.copy()
        parent_field_name, parent_pk = list(self.get_parents_query_dict().items())[0]
        data[parent_field_name] = reverse('api:{0}-detail'.format(parent_field_name), kwargs=dict(pk=parent_pk))
        return data


class FourLevelPermNestedModelViewSet(FourLevelPermCreateModelMixin,
                                      FourLevelPermListModelMixin,
                                      FourLevelPermRetrieveModelMixin,
                                      FourLevelPermUpdateModelMixin,
                                      FourLevelPermDestroyModelMixin,
                                      FourLevelPermNestedGenericViewSet):
    pass


class Myself(APIView):

    def get(self, request, format=None):
        user_role = get_role_of(request.user)
        if isinstance(user_role, Student):
            url = reverse('api:student-detail', kwargs=dict(pk=user_role.pk))
        elif isinstance(user_role, Instructor):
            url = reverse('api:instructor-detail', kwargs=dict(pk=user_role.pk))
        else:
            return Response(dict(detail="You are not a student or instructor."), status=status.HTTP_400_BAD_REQUEST)

        return Response(dict(url=url), status=status.HTTP_200_OK)


# -----------------------------------------------------------------------------
# Student ViewSets
# -----------------------------------------------------------------------------
class StudentViewSet(FourLevelPermModelViewSet):
    queryset = Student.objects.all()

    filter_backends = (FourLevelObjectPermissionsFilter,
                       filters.DjangoFilterBackend, )
    filter_class = my_filters.StudentFilter

    permission_classes = (FourLevelObjectPermissions, )
    serializer_class = ReadStudentSerializer    # add this to ensure browsable api is okay

    read_serializer_class = ReadStudentSerializer
    write_serializer_class = CreateStudentSerializer
    base_write_serializer_class = write_serializer_class
    normal_write_serializer_class = write_serializer_class
    advanced_write_serializer_class = write_serializer_class


# -----------------------------------------------------------------------------
# StudentCourses ViewSet
# -----------------------------------------------------------------------------
class StudentCoursesViewSet(FourLevelPermNestedModelViewSet):
    queryset = Takes.objects.all()
    filter_backends = (FourLevelObjectPermissionsFilter, )
    permission_classes = (FourLevelObjectPermissions, )
    serializer_class = ReadStudentCoursesSerializer     # add this to ensure browsable api is okay

    read_serializer_class = ReadStudentCoursesSerializer
    write_serializer_class = CreateStudentCoursesSerializer
    base_write_serializer_class = BaseWriteStudentCoursesSerializer
    normal_write_serializer_class = write_serializer_class
    advanced_write_serializer_class = write_serializer_class


# -----------------------------------------------------------------------------
# Instructor ViewSets
# -----------------------------------------------------------------------------
class InstructorViewSet(FourLevelPermModelViewSet):
    queryset = Instructor.objects.all()
    filter_backends = (FourLevelObjectPermissionsFilter, )
    permission_classes = (FourLevelObjectPermissions, )
    serializer_class = ReadInstructorSerializer     # add this to ensure browsable api is okay

    read_serializer_class = ReadInstructorSerializer
    write_serializer_class = CreateInstructorSerializer
    base_write_serializer_class = write_serializer_class
    normal_write_serializer_class = write_serializer_class
    advanced_write_serializer_class = write_serializer_class


# -----------------------------------------------------------------------------
# InstructorCourses ViewSets
# -----------------------------------------------------------------------------
class InstructorCoursesViewSet(FourLevelPermNestedModelViewSet):
    queryset = Teaches.objects.all()
    filter_backends = (FourLevelObjectPermissionsFilter, )
    permission_classes = (FourLevelObjectPermissions, )
    serializer_class = ReadInstructorCoursesSerializer

    read_serializer_class = ReadInstructorCoursesSerializer
    write_serializer_class = CreateInstructorCoursesSerializer
    base_write_serializer_class = write_serializer_class
    normal_write_serializer_class = write_serializer_class
    advanced_write_serializer_class = write_serializer_class


# -----------------------------------------------------------------------------
# Course ViewSets
# -----------------------------------------------------------------------------
class CourseViewSet(FourLevelPermModelViewSet):
    queryset = Course.objects.all()
    filter_backends = (FourLevelObjectPermissionsFilter, )
    permission_classes = (FourLevelObjectPermissions, )
    serializer_class = ReadCourseSerializer

    read_serializer_class = ReadCourseSerializer
    write_serializer_class = CreateCourseSerializer
    base_write_serializer_class = BaseWriteCourseSerializer
    normal_write_serializer_class = write_serializer_class
    advanced_write_serializer_class = write_serializer_class

    @detail_route(methods=['post'], permission_classes=[CreateGroupPermission])
    def add_group(self, request, pk=None):
        """
        Create a group to the course
        """
        self.check_object_permissions(request, Course.objects.get(pk=pk))
        # put in `course` parameter
        data = request.data.copy()
        data['course'] = reverse('api:course-detail', kwargs=dict(pk=pk))
        serializer = CreateGroupSerializer(data=data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @list_route(methods=['get'], permission_classes=[IsInstructor])
    def giving(self, request):
        """
        Get a list of courses given by this instructor
        """
        self.check_permissions(request)

        queryset = Course.objects.given_by(get_role_of(request.user))

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ReadCourseSerializer(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = ReadCourseSerializer(queryset, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    @list_route(methods=['get'], permission_classes=[IsStudent])
    def taking(self, request):
        """
        Get a list of courses taken by this student
        """
        self.check_permissions(request)

        queryset = Course.objects.taken_by(get_role_of(request.user))

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ReadCourseSerializer(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = ReadCourseSerializer(queryset, many=True, context=self.get_serializer_context())
        return Response(serializer.data)


# -----------------------------------------------------------------------------
# CourseInstructors ViewSets
# -----------------------------------------------------------------------------
class CourseInstructorsViewSet(FourLevelPermListModelMixin,
                               FourLevelPermRetrieveModelMixin,
                               FourLevelPermCreateModelMixin,
                               FourLevelPermDestroyModelMixin,
                               FourLevelPermNestedGenericViewSet):
    queryset = Teaches.objects.all()
    filter_backends = (FourLevelObjectPermissionsFilter, )
    permission_classes = (FourLevelObjectPermissions, )
    serializer_class = ReadCourseInstructorsSerializer

    read_serializer_class = ReadCourseInstructorsSerializer
    write_serializer_class = CourseInstructorsSerializer
    base_write_serializer_class = write_serializer_class
    normal_write_serializer_class = write_serializer_class
    advanced_write_serializer_class = write_serializer_class


# -----------------------------------------------------------------------------
# CourseTakes ViewSets
# -----------------------------------------------------------------------------
class CourseTakesViewSet(FourLevelPermNestedModelViewSet):
    queryset = Takes.objects.all()
    filter_backends = (FourLevelObjectPermissionsFilter, )
    permission_classes = (FourLevelObjectPermissions, )
    serializer_class = ReadCourseTakesSerializer

    read_serializer_class = ReadCourseTakesSerializer
    write_serializer_class = CreateCourseTakesSerializer
    base_write_serializer_class = BaseWriteCourseTakesSerializer
    normal_write_serializer_class = write_serializer_class
    advanced_write_serializer_class = write_serializer_class


# -----------------------------------------------------------------------------
# Group ViewSets
# -----------------------------------------------------------------------------
class GroupViewSet(FourLevelPermListModelMixin,
                   FourLevelPermRetrieveModelMixin,
                   FourLevelPermUpdateModelMixin,
                   FourLevelPermDestroyModelMixin,
                   FourLevelPermGenericViewSet):
    # PUT method is not allowed
    http_method_names = [name for name in FourLevelPermGenericViewSet.http_method_names if name not in ['put']]

    queryset = Group.objects.all()

    filter_backends = (FourLevelObjectPermissionsFilter,
                       filters.DjangoFilterBackend)
    filter_class = my_filters.GroupFilter

    permission_classes = (FourLevelObjectPermissions, )
    serializer_class = ReadGroupSerializer

    read_serializer_class = ReadGroupSerializer
    write_serializer_class = CreateGroupSerializer
    advanced_write_serializer_class = WriteGroupSerializer
    normal_write_serializer_class = advanced_write_serializer_class
    base_write_serializer_class = advanced_write_serializer_class


class CourseGroupsViewSet(FourLevelPermListModelMixin,
                          FourLevelPermRetrieveModelMixin,
                          FourLevelPermNestedGenericViewSet):
    queryset = Group.objects.all()
    filter_backends = (FourLevelObjectPermissionsFilter, )
    permission_classes = (FourLevelObjectPermissions, )
    serializer_class = ReadGroupSerializer

    read_serializer_class = ReadGroupSerializer


class ClassViewSet(viewsets.ModelViewSet):

    queryset = Class.objects.all()
    serializer_class = ClassSerializer


