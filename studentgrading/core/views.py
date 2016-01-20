# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django.core import serializers
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import RedirectView, View
from django.core.urlresolvers import reverse
from braces.views import LoginRequiredMixin

from .models import Student, Instructor, get_role_of


class InstructorView(LoginRequiredMixin, View):

    def get(self, request):
        return render(request, 'core/teacher.html')


class StudentView(LoginRequiredMixin, View):

    def get(self, request):
        return render(request, 'core/student.html')


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        role = get_role_of(self.request.user)
        if isinstance(role, Student):
            return reverse('core:student')
        elif isinstance(role, Instructor):
            return reverse('core:teacher')

@csrf_exempt
def stuXls(request):
    if request.method == 'POST':
        role = get_role_of(request.user)
        if 'stuxls' in request.FILES:
            role.import_student_takes(
                request.FILES['stuxls'],
                request.GET['course_id'])
            return HttpResponseRedirect(reverse('core:teacher'))
        else:
            return HttpResponse('Error')
