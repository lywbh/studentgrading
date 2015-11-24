# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.conf.urls import patterns, url, include

from . import views

urlpatterns = patterns(
    '',
    url(
        r'^$',
        views.UserListView.as_view(),
        name='list',
    ),
    url(
        r'^(?P<username>[\w.@+-]+)\$',
        views.UserDetailView.as_view(),
        name='detail',
    ),
    url(
        r'^login/$',
        views.UserLoginView.as_view(),
        name='login',
    ),
    url(
        r'^logout/$',
        views.logout_view,
        name='logout',
    ),
    # URL pattern for the UserRedirectView
    url(
        r'^~redirect/$',
        views.UserRedirectView.as_view(),
        name='redirect'
    ),
)
