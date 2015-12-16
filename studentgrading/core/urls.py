# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from django.conf.urls import patterns, url, include

from . import views
from . import forms

urlpatterns = patterns(
    '',
    url(r'^login/$', 'django.contrib.auth.views.login', {
        'template_name': 'core/login.html',
        'authentication_form': forms.LoginAuthenticationForm,
    }, name='login'),
    url(r'^~redirect/$', views.UserRedirectView.as_view(), name='redirect'),
    url(r'^teacher/', include(patterns(
        '',
        url(r'^$', views.InstructorView.as_view(), name='teacher'),
        url(r'^getcourse/$', views.getTeachCourse, name='getteachcourse'),
        url(r'^getallstudent/$', views.getAllStudent, name='getallstudent'),
        url(r'^getgroup/$', views.getGroup, name='getgroup'),
        url(r'^setgroupconfig/$', views.setGroupConfig, name='setgroupconfig'),
        url(r'^newcourse/$', views.newCourse, name='newcourse'),
        url(r'^delcourse/$', views.delCourse, name='delcourse'),
        url(r'^stuxls/$', views.stuXls, name='stuxls'),
    ))),
    url(r'^student/', include(patterns(
        '',
        url(r'^$', views.StudentView.as_view(), name='student'),
        url(r'^getcourse/$', views.getStuCourse, name='getstucourse'),
        url(r'^getgroup/$', views.getStuGroup, name='getstugroup'),
        url(r'^getcandidatestudent/$',
            views.getCandidateStudent, name='getcandidatestudent'),
        url(r'^savegroup/$', views.saveGroup, name='savegroup'),
    ))),
)
