# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model

from rest_framework import serializers
from rest_framework.relations import reverse

from .models import (
    Student, Class, Course, Takes,
)


class StudentCoursesHyperlinkedIdentityField(serializers.HyperlinkedIdentityField):
    """
    The HyperlinkedIdentityField in StudentCoursesSerializer
    """
    def get_url(self, obj, view_name, request, format):
        url_kwargs = {
            'parent_lookup_student': obj.student.pk,
            'pk': obj.pk,
        }
        return reverse(view_name, kwargs=url_kwargs, request=request, format=format)


class StudentCoursesHyperlinkedRelatedField(serializers.HyperlinkedRelatedField):

    view_name = 'api:student-course-detail'

    def get_url(self, obj, view_name, request, format):
        url_kwargs = {
            'parent_lookup_student': obj.student.pk,
            'pk': obj.pk,
        }
        return reverse(view_name, kwargs=url_kwargs, request=request, format=format)

    def get_object(self, view_name, view_args, view_kwargs):
        lookup_kwargs = {
            'student__pk': view_kwargs['parent_lookup_student'],
            'pk': view_kwargs['pk'],
        }
        return self.get_queryset().get(**lookup_kwargs)


class StudentSerializer(serializers.HyperlinkedModelSerializer):

    courses = serializers.HyperlinkedIdentityField(
        source='takes',
        view_name='api:student-course-list',
        lookup_url_kwarg='parent_lookup_student',
    )

    class Meta:
        model = Student
        fields = ('url', 'id', 'user', 's_id', 's_class', 'name', 'sex', 'courses', )
        extra_kwargs = {
            'url': {'view_name': 'api:student-detail', },
            'user': {
                'queryset': get_user_model().objects.all(),
                'view_name': 'api:user-detail',
            },
            's_class': {
                'queryset': Class.objects.all(),
                'view_name': 'api:class-detail',
            }
        }


class StudentCoursesSerializer(serializers.HyperlinkedModelSerializer):

    url = StudentCoursesHyperlinkedIdentityField(
        view_name='api:student-course-detail',
    )

    class Meta:
        model = Takes
        fields = ('url', 'id', 'course', 'grade')
        extra_kwargs = {
            'course': {'view_name': 'api:course-detail'},
        }


class ClassSerializer(serializers.HyperlinkedModelSerializer):

    url = serializers.HyperlinkedIdentityField(view_name='api:class-detail')
    students = serializers.HyperlinkedRelatedField(
        many=True,
        queryset=Class.objects.all(),
        view_name='api:student-detail',
    )

    class Meta:
        model = Class
        fields = ('url', 'class_id', 'students', )
        read_only_fields = ('url', 'class_id', )


class CourseSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Course
        fields = ('url', 'title', 'year', 'semester', 'description',
                  'min_group_size', 'max_group_size', )
        extra_kwargs = {
            'url': {'view_name': 'api:course-detail'},
        }
