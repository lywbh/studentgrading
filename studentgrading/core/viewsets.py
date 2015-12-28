# -*- coding: utf-8 -*-
from rest_framework import viewsets
from rest_framework_extensions.mixins import NestedViewSetMixin
from rest_framework import filters
from rest_framework import permissions

from .serializers import (
    StudentSerializer, ClassSerializer, CourseSerializer,
    StudentCoursesSerializer,
)
from .models import (
    Student, Class, Course, Takes,
)


class StudentViewSet(viewsets.ModelViewSet):

    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    filter_backends = (filters.DjangoFilterBackend, )
    filter_fields = ('s_class', )

    permission_classes = (permissions.IsAuthenticatedOrReadOnly, )


class StudentCoursesViewSet(NestedViewSetMixin, viewsets.ModelViewSet):

    queryset = Takes.objects.all()
    serializer_class = StudentCoursesSerializer


class ClassViewSet(viewsets.ModelViewSet):

    queryset = Class.objects.all()
    serializer_class = ClassSerializer


class CourseViewSet(viewsets.ModelViewSet):

    queryset = Course.objects.all()
    serializer_class = CourseSerializer
