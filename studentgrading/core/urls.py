# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from django.conf.urls import patterns, url
from . import views

urlpatterns = patterns(
    '',
    url(
        r'^teacher/$',
        views.teacher_view,
        name='teacher',
    ),
    url(
        r'^teacher/getcourse/$',
        views.getTeachCourse,
        name='getteachcourse',
    ),
    url(
        r'^teacher/getgroup/$',
        views.getGroup,
        name='getgroup',
    ),
)
