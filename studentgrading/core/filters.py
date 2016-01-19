# -*- coding: utf-8 -*-
from . import models

import django_filters


class StudentFilter(django_filters.FilterSet):

    class Meta:
        model = models.Student


class GroupFilter(django_filters.FilterSet):

    course = django_filters.NumberFilter(name='course__id')
    leader = django_filters.NumberFilter(name='leader__id')
    has_member = django_filters.NumberFilter(name='members__id')
    has_student = django_filters.MethodFilter()

    class Meta:
        model = models.Group
        fields = ['course', 'leader', 'has_member', 'has_student']

    def filter_has_student(self, queryset, value):
        return queryset.has_student(value)


class AssignmentFilter(django_filters.FilterSet):

    course = django_filters.NumberFilter(name='course__id')

    class Meta:
        model = models.Assignment
        fields = ['course']
