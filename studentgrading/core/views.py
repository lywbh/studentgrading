# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django.core import serializers
from django.views.decorators.csrf import csrf_exempt
from django.core.urlresolvers import reverse

from .models import *

def teacher_view(request):
    return render(request, 'core/teacher.html')

def student_view(request):
    return render(request, 'core/student.html')
    
def getTeachCourse(request):
    if request.method == 'GET':
        role = get_role_of(request.user)
        if 'id' in request.GET:
            course = role.get_course(request.GET['id'])
            data = {
                'id': course.id,
                'title': course.title,
                'year': course.year,
                'semester': course.semester,
                'description': course.description,
                'min_group_size': course.min_group_size,
                'max_group_size': course.max_group_size,
            }
            return JsonResponse(data)
        else:
            courselist = role.get_all_courses()
            data = serializers.serialize('json', courselist)
            return HttpResponse(data, content_type = 'application/json')

def getStuCourse(request):
    if request.method == 'GET':
        role = get_role_of(request.user)
        if 'id' in request.GET:
            course = role.get_course(request.GET['id'])
            data = {
                'id': course.id,
                'title': course.title,
                'year': course.year,
                'semester': course.semester,
                'description': course.description,
            }
            return JsonResponse(data)
        else:
            courselist = role.get_all_courses()
            data = serializers.serialize('json', courselist)
            return HttpResponse(data, content_type = 'application/json')
            
def getAllStudent(request):
    if request.method == 'GET':
        role = get_role_of(request.user)
        if 'course_id' in request.GET:
            course = role.get_course(request.GET['course_id'])
            studentlist = course.get_all_students()
            data = []
            for member in studentlist:
                data.append({
                    's_id': member.s_id,
                    'name': member.name,
                    's_class': member.s_class.class_id,
                })
            return JsonResponse({'content': data})
            
            
def getGroup(request):
    if request.method == 'GET':
        role = get_role_of(request.user)
        if 'course_id' in request.GET and 'group_id' in request.GET:
            course = role.get_course(request.GET['course_id'])
            group = course.get_group(request.GET['group_id'])
            data = [{
                's_id': group.leader.s_id,
                'name': group.leader.name,
                's_class': group.leader.s_class.class_id,
            }]
            for member in group.members.all():
                data.append({
                    's_id': member.s_id,
                    'name': member.name,
                    's_class': member.s_class.class_id,
                })
            return JsonResponse({'content': data})
            
        elif 'course_id' in request.GET:
            course = role.get_course(request.GET['course_id'])
            grouplist = course.get_all_groups()
            data = []
            for group in grouplist:
                if group.leader.contact_infos.all():
                    contact = group.leader.contact_infos.all()[0]
                else:
                    contact = None
                data.append({
                    'id': group.id,
                    'number': group.number,
                    'name': group.__str__(),
                    'leader': group.leader.name,
                    'contact': contact,
                })
            return JsonResponse({'content': data})
        else:
            return HttpResponse('Error')

def getStuGroup(request):
    if request.method == 'GET':
        role = get_role_of(request.user)
        if 'course_id' in request.GET:
            course = role.get_course(request.GET['course_id'])
            group = None
            data = [{
                's_id': group.leader.s_id,
                'name': group.leader.name,
                's_class': group.leader.s_class.class_id,
            }]
            for member in group.members.all():
                data.append({
                    's_id': member.s_id,
                    'name': member.name,
                    's_class': member.s_class.class_id,
                })
            return JsonResponse({'content': data})
        else:
            return HttpResponse('Error')
            
@csrf_exempt
def setGroupConfig(request):
    if request.method == 'POST':
        role = get_role_of(request.user)
        if 'course_id' in request.POST and 'group_min' in request.POST and 'group_max' in request.POST:
            course = role.get_course(request.POST['course_id'])
            course.min_group_size = request.POST['group_min']
            course.max_group_size = request.POST['group_max']
            course.save()
            return HttpResponse('success')
        else:
            return HttpResponse('fail')

@csrf_exempt
def newCourse(request):
    if request.method == 'POST':
        role = get_role_of(request.user)
        if 'title' in request.POST and 'year' in request.POST and 'semester' in request.POST and 'description' in request.POST:
            title = request.POST['title']
            year = request.POST['year']
            semester = request.POST['semester']
            description = request.POST['description']
            
            role.add_course(title = title, year = year, semester = semester, description = description)
            return HttpResponse('success')
        else:
            return HttpResponse('fail')
            
@csrf_exempt
def delCourse(request):
    if request.method == 'POST':
        role = get_role_of(request.user)
        if 'id' in request.POST:
            role.delete_course(request.POST['id'])
            return HttpResponse('success')
        else:
            return HttpResponse('fail')
          
@csrf_exempt
def stuXls(request):        
    if request.method == 'POST':
        # TODO: delete after test
        import_student(request.FILES['stuxls'])
        return HttpResponseRedirect(reverse('core:teacher'))
        role = get_role_of(request.user)
        if isinstance(role, Instructor):
            
            return HttpResponseRedirect(reverse('core:teacher'))
            
