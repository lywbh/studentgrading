# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model

from rest_framework import serializers
from rest_framework.relations import reverse

from .models import (
    Student, Class, Course, Takes,
    Instructor,
    has_four_level_perm,
)


# -----------------------------------------------------------------------------
# Custom Fields Class
# -----------------------------------------------------------------------------
class StudentCoursesHyperlinkedIdentityField(serializers.HyperlinkedIdentityField):
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


# -----------------------------------------------------------------------------
# Student Serializers
# -----------------------------------------------------------------------------
class StudentSerializer(serializers.HyperlinkedModelSerializer):
    courses = serializers.HyperlinkedIdentityField(
        source='takes',
        view_name='api:student-course-list',
        lookup_url_kwarg='parent_lookup_student',
    )

    class Meta:
        model = Student
        fields = ('url', 'id', 'user', 'name', 'sex', 's_id', 's_class', 'courses', )
        extra_kwargs = {
            'url': {'view_name': 'api:student-detail', },
            'user': {
                'view_name': 'api:user-detail',
            },
            's_class': {
                'view_name': 'api:class-detail',
            }
        }

    def to_representation(self, instance):
        ret = super(StudentSerializer, self).to_representation(instance)
        user = self.context['request'].user
        if not has_four_level_perm('core.view_student', user, instance):
            del ret['user']

            if not has_four_level_perm('core.view_student_advanced', user, instance):
                del ret['courses']

                if not has_four_level_perm('core.view_student_normal', user, instance):
                    del ret['s_id']
                    del ret['s_class']

        return ret


class ReadStudentSerializer(StudentSerializer):
    class Meta(StudentSerializer.Meta):
        read_only_fields = ('user', 'name', 'sex', 's_id', 's_class', 'courses', )


# -----------------------------------------------------------------------------
# Instructor Serializers
# -----------------------------------------------------------------------------
class InstructorSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Instructor
        fields = ('url', 'id', 'user', 'name', 'sex', 'inst_id', )
        extra_kwargs = {
            'url': {'view_name': 'api:instructor-detail', },
            'user': {'view_name': 'api:user-detail', },
        }

    def to_representation(self, instance):
        ret = super(InstructorSerializer, self).to_representation(instance)
        user = self.context['request'].user
        if not has_four_level_perm('core.view_instructor', user, instance):
            del ret['user']

            if not has_four_level_perm('core.view_instructor_normal', user, instance):
                del ret['inst_id']

        return ret


class ReadInstructorSerializer(InstructorSerializer):
    class Meta(InstructorSerializer.Meta):
        read_only_fields = ('user', 'name', 'sex', 'inst_id', )


# -----------------------------------------------------------------------------
# StudentCourses Serializers (students/{pk}/courses/)
# -----------------------------------------------------------------------------
class StudentCoursesSerializer(serializers.HyperlinkedModelSerializer):

    url = StudentCoursesHyperlinkedIdentityField(
        view_name='api:student-course-detail',
    )

    class Meta:
        model = Takes
        fields = ('url', 'id', 'student', 'course', 'grade')
        extra_kwargs = {
            'student': {'view_name': 'api:student-detail'},
            'course': {'view_name': 'api:course-detail'},
        }


class ReadStudentCoursesSerializer(StudentCoursesSerializer):
    class Meta(StudentCoursesSerializer.Meta):
        read_only_fields = ('student', 'course', 'grade', )


class WriteStudentCoursesSerializer(StudentCoursesSerializer):
    class Meta(StudentCoursesSerializer.Meta):
        fields = ('url', 'id', 'grade')


class AdminStudentCoursesSerializer(serializers.HyperlinkedModelSerializer):

    url = StudentCoursesHyperlinkedIdentityField(
        view_name='api:student-course-detail',
    )

    class Meta:
        model = Takes
        fields = ('url', 'id', 'course', 'grade')
        extra_kwargs = {
            'course': {'view_name': 'api:course-detail'},
        }


class NormalStudentCoursesSerializer(serializers.HyperlinkedModelSerializer):

    url = StudentCoursesHyperlinkedIdentityField(
        view_name='api:student-course-detail',
    )

    class Meta:
        model = Takes
        fields = ('url', 'id', 'course', 'grade')
        read_only_fields = ('course', 'grade', )
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
