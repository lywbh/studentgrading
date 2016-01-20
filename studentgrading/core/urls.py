# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.conf.urls import patterns, url, include
import django

from . import views
from . import forms

urlpatterns = [
    url(r'^login/$', django.contrib.auth.views.login, {
        'template_name': 'core/login.html',
        'authentication_form': forms.LoginAuthenticationForm,
    }, name='login'),
    url(r'^~redirect/$', views.UserRedirectView.as_view(), name='redirect'),
    url(r'^teacher/', include([
            url(r'^$', views.InstructorView.as_view(), name='teacher'),
            url(r'^stuxls/$', views.stuXls, name='stuxls'),
        ]
    )),
    url(r'^student/', include([
            url(r'^$', views.StudentView.as_view(), name='student'),
        ]
    )),
]
