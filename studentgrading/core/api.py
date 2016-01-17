# -*- coding: utf-8 -*-
from django.conf.urls import url, include, patterns

from rest_framework_extensions.routers import ExtendedDefaultRouter

from . import viewsets as core_viewsets
from ..users import viewsets as users_viewsets


router = ExtendedDefaultRouter()

router.register(r'users', users_viewsets.UserViewSet)
(
    router.register(r'students', core_viewsets.StudentViewSet)
          .register(r'courses',
                    core_viewsets.StudentCoursesViewSet,
                    'student-course',
                    parents_query_lookups=['student'])
)
(
    router.register(r'instructors', core_viewsets.InstructorViewSet)
          .register(r'courses',
                    core_viewsets.InstructorCoursesViewSet,
                    'instructor-course',
                    parents_query_lookups=['instructor'])
)
course_router = router.register(r'courses', core_viewsets.CourseViewSet)
course_router.register(r'instructors',
                       core_viewsets.CourseInstructorsViewSet,
                       'course-instructor',
                       parents_query_lookups=['course'])
course_router.register(r'students',
                       core_viewsets.CourseStudentsViewSet,
                       'course-student',
                       parents_query_lookups=['course'])
course_router.register(r'groups',
                       core_viewsets.CourseGroupsViewSet,
                       'course-group',
                       parents_query_lookups=['course'])

group_router = router.register(r'groups', core_viewsets.GroupViewSet)

router.register(r'classes', core_viewsets.ClassViewSet)

urlpatterns = patterns(
    '',
    url(r'^', include(router.urls)),
)
