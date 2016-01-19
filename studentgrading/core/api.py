# -*- coding: utf-8 -*-
from django.conf.urls import url, include, patterns

from rest_framework.urlpatterns import format_suffix_patterns
from rest_framework_extensions.routers import ExtendedDefaultRouter

from . import viewsets as core_viewsets
from ..users import viewsets as users_viewsets


router = ExtendedDefaultRouter()

router.register(r'users', users_viewsets.UserViewSet)
(
    router.register(r'students', core_viewsets.StudentViewSet)
          .register(r'takes',
                    core_viewsets.StudentTakesViewSet,
                    'student-course',
                    parents_query_lookups=['student'])
)
(
    router.register(r'instructors', core_viewsets.InstructorViewSet)
          .register(r'teaches',
                    core_viewsets.InstructorTeachesViewSet,
                    'instructor-course',
                    parents_query_lookups=['instructor'])
)
course_router = router.register(r'courses', core_viewsets.CourseViewSet)
course_router.register(r'teaches',
                       core_viewsets.CourseTeachesViewSet,
                       'course-instructor',
                       parents_query_lookups=['course'])
course_router.register(r'takes',
                       core_viewsets.CourseTakesViewSet,
                       'course-takes',
                       parents_query_lookups=['course'])
course_router.register(r'groups',
                       core_viewsets.CourseGroupsViewSet,
                       'course-group',
                       parents_query_lookups=['course'])

group_router = router.register(r'groups', core_viewsets.GroupViewSet)

router.register(r'assignments', core_viewsets.AssignmentViewSet)

router.register(r'classes', core_viewsets.ClassViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]

myself_urlpatterns = [
    url(r'^myself/$', core_viewsets.Myself.as_view(), name='myself'),
]
myself_urlpatterns = format_suffix_patterns(myself_urlpatterns)

urlpatterns += myself_urlpatterns
