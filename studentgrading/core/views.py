# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.http import Http404, HttpResponse, HttpResponseRedirect, HttpResponseNotFound, JsonResponse
from django.shortcuts import redirect, render
from django.core import serializers


from .models import Course


def teacher_view(request):
    return render(request, 'core/teacher.html')


def getTeachCourse(request):
    if request.method == 'GET':
        if 'id' in request.GET:
            course = Course.getCourseById(request.GET['id'])
            return JsonResponse(course)
        else:
            #courselist = Course.getCourses()
            courselist = Course.get_all_courses()
            data = serializers.serialize('json', courselist)
            return HttpResponse(data, content_type = 'application/json')


def getGroup(request):
    if request.method == 'GET':
        if 'course_id' in request.GET and 'group_id' in request.GET:
            print('a')
        elif 'course_id' in request.GET:
            print('b')
        else:
            print('c')
        