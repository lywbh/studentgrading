# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model

from rest_framework import serializers
from rest_framework.relations import reverse

from .models import (
    Student, Class, Course, Takes, Teaches,
    Instructor, Teaches,
    has_four_level_perm,
    get_role_of,
)


# -----------------------------------------------------------------------------
# Custom Fields Class
# -----------------------------------------------------------------------------
class ChildHyperlinkedIdentityField(serializers.HyperlinkedIdentityField):

    def __init__(self, *args, **kwargs):
        self.parent_field_name = kwargs.pop('parent_field_name', None)
        self.parent_query_lookup = kwargs.pop('parent_query_lookup', None)
        super(ChildHyperlinkedIdentityField, self).__init__(*args, **kwargs)

    def get_parent_field_name(self):
        assert self.parent_field_name is not None, (
            "'%s' should either include a `parent_field_name` attribute, "
            "or override the `get_parent_field_name()` method."
            % self.__class__.__name__
        )
        return self.parent_field_name

    def get_parent_query_lookup(self):
        if not self.parent_query_lookup:
            return 'parent_lookup_{0}'.format(self.get_parent_field_name())
        return self.parent_query_lookup

    def get_url(self, obj, view_name, request, format):
        url_kwargs = {
            self.get_parent_query_lookup(): getattr(obj, self.get_parent_field_name()).pk,
            'pk': obj.pk,
        }
        return reverse(view_name, kwargs=url_kwargs, request=request, format=format)


# -----------------------------------------------------------------------------
# Relationship Serializers
# -----------------------------------------------------------------------------
class TakesSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Takes
        fields = ('url', 'id', 'student', 'course', 'grade')
        extra_kwargs = {
            'student': {'view_name': 'api:student-detail'},
            'course': {'view_name': 'api:course-detail'},
        }

    def to_representation(self, instance):
        ret = super(TakesSerializer, self).to_representation(instance)
        user = self.context['request'].user
        if not has_four_level_perm('core.view_takes', user, instance):
            del ret['grade']

        return ret

    def to_internal_value(self, data):
        validated_data = super(TakesSerializer, self).to_internal_value(data)
        if getattr(self, 'context'):
            request = self.context['request']
            user = request.user
            user_role = get_role_of(user)
            if (isinstance(user_role, Instructor) and
                    request.method == 'POST' and
                    'course' in validated_data):
                # When instructor tries to add a 'takes' with this student,
                # it can only add the student to its course
                request_instructor = user_role
                course = validated_data['course']
                if not request_instructor.is_giving(course):
                    raise serializers.ValidationError({
                        'course': 'Cannot add student to a course not given by you.'
                    })
        return validated_data


class TeachesSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Teaches
        fields = ('url', 'id', 'instructor', 'course')
        extra_kwargs = {
            'instructor': {'view_name': 'api:instructor-detail'},
            'course': {'view_name': 'api:course-detail'},
        }

    def to_internal_value(self, data):
        validated_data = super(TeachesSerializer, self).to_internal_value(data)
        if getattr(self, 'context'):
            request = self.context['request']
            user = request.user
            user_role = get_role_of(user)

            if (isinstance(user_role, Instructor) and
                    request.method == 'POST' and
                    'course' in validated_data and
                    'instructor' in validated_data):
                # When instructor tries to add 'teaches' with a course not given by itself,
                # it can only add itself to this course
                requeset_inst = user_role
                instructor = validated_data['instructor']
                course = validated_data['course']
                if not instructor.pk == requeset_inst.pk and not course.is_given_by(requeset_inst):
                    raise serializers.ValidationError({
                        'course': 'Cannot add an instructor to a course not given by you.'
                    })
        return validated_data


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
    courses = serializers.HyperlinkedIdentityField(
        source='teaches',
        view_name='api:instructor-course-list',
        lookup_url_kwarg='parent_lookup_instructor',
    )

    class Meta:
        model = Instructor
        fields = ('url', 'id', 'user', 'name', 'sex', 'inst_id', 'courses')
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
        read_only_fields = ('user', 'name', 'sex', 'inst_id', 'courses', )


# -----------------------------------------------------------------------------
# StudentCourses Serializers (students/{pk}/courses/)
# -----------------------------------------------------------------------------
class StudentCoursesSerializer(TakesSerializer):

    url = ChildHyperlinkedIdentityField(
        view_name='api:student-course-detail',
        parent_field_name='student',
    )

    class Meta(TakesSerializer.Meta):
        pass


class ReadStudentCoursesSerializer(StudentCoursesSerializer):
    class Meta(StudentCoursesSerializer.Meta):
        read_only_fields = ('student', 'course', 'grade', )


class BaseWriteStudentCoursesSerializer(StudentCoursesSerializer):
    class Meta(StudentCoursesSerializer.Meta):
        fields = ('url', 'id', 'grade')


# -----------------------------------------------------------------------------
# InstructorCourses Serializers (instructors/{pk}/courses/)
# -----------------------------------------------------------------------------
class InstructorCoursesSerializer(TeachesSerializer):

    url = ChildHyperlinkedIdentityField(
        view_name='api:instructor-course-detail',
        parent_field_name='instructor',
    )

    class Meta(TeachesSerializer.Meta):
        pass


class ReadInstructorCoursesSerializer(InstructorCoursesSerializer):
    class Meta(InstructorCoursesSerializer.Meta):
        read_only_fields = ('instructor', 'course', )


# -----------------------------------------------------------------------------
# Course Serializers (courses/{pk}/)
# -----------------------------------------------------------------------------
class CourseSerializer(serializers.HyperlinkedModelSerializer):

    instructors = serializers.HyperlinkedRelatedField(
        many=True,
        required=False,
        queryset=Instructor.objects.all(),
        view_name='api:instructor-detail',
    )

    class Meta:
        model = Course
        fields = ('url', 'id', 'title', 'year', 'semester', 'description',
                  'min_group_size', 'max_group_size', 'instructors')
        extra_kwargs = {
            'url': {'view_name': 'api:course-detail'},
        }

    def create(self, validated_data):
        instructors_data = validated_data.pop('instructors', None)
        course = Course.objects.create(**validated_data)
        if instructors_data:
            for instructor in instructors_data:
                Teaches.objects.create(instructor=instructor, course=course)
        return course

    def to_representation(self, instance):
        ret = super(CourseSerializer, self).to_representation(instance)
        user = self.context['request'].user
        if not has_four_level_perm('core.view_course', user, instance):
            del ret['min_group_size']
            del ret['max_group_size']

            if not has_four_level_perm('core.view_course_advanced', user, instance):
                del ret['instructors']

        return ret


class ReadCourseSerializer(CourseSerializer):
    instructors = serializers.HyperlinkedIdentityField(
        source='teaches',
        view_name='api:course-instructor-list',
        lookup_url_kwarg='parent_lookup_course',
    )

    class Meta(CourseSerializer.Meta):
        read_only_fields = (
            'title', 'year', 'semester', 'description',
            'min_group_size', 'max_group_size', 'instructors'
        )


class BaseWriteCourseSerializer(CourseSerializer):
    class Meta(CourseSerializer.Meta):
        fields = ('url', 'id', 'min_group_size', 'max_group_size', 'description')


# -----------------------------------------------------------------------------
# CourseInstructors Serializers (courses/{pk}/instructors/)
# -----------------------------------------------------------------------------
class CourseInstructorsSerializer(TeachesSerializer):

    url = ChildHyperlinkedIdentityField(
        view_name='api:course-instructor-detail',
        parent_field_name='course',
    )

    class Meta(TeachesSerializer.Meta):
        pass


class ReadCourseInstructorsSerializer(CourseInstructorsSerializer):
    class Meta(CourseInstructorsSerializer.Meta):
        read_only_fields = ('instructor', 'course')


# -----------------------------------------------------------------------------
# CourseStudents Serializers (courses/{pk}/students/)
# -----------------------------------------------------------------------------
class CourseStudentsSerializer(TakesSerializer):

    url = ChildHyperlinkedIdentityField(
        view_name='api:course-student-detail',
        parent_field_name='course',
    )

    class Meta(TakesSerializer.Meta):
        pass


class ReadCourseStudentsSerializer(CourseStudentsSerializer):
    class Meta(CourseStudentsSerializer.Meta):
        read_only_fields = ('student', 'course', 'grade', )


class BaseWriteCourseStudentsSerializer(CourseStudentsSerializer):
    class Meta(CourseStudentsSerializer.Meta):
        fields = ('url', 'id', 'grade')


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


