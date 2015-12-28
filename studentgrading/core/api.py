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
router.register(r'classes', core_viewsets.ClassViewSet)
router.register(r'courses', core_viewsets.CourseViewSet)

urlpatterns = patterns(
    '',
    url(r'^', include(router.urls)),
)
