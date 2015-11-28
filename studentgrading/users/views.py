# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.contrib import auth
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseRedirect, HttpResponseNotFound, JsonResponse
from django.shortcuts import redirect, render
from django.core.urlresolvers import reverse
from django.views.generic import View, DetailView, ListView, RedirectView

from braces.views import LoginRequiredMixin

from .models import *

class UserLoginView(View):
    def post(self, request, *args, **kwargs):
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username = username, password = password)
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse('core:teacher'))
            
    def get(self, requset, *args, **kwargs):
        return render(requset, 'users/login.html', {'form': AuthenticationForm()})

def logout_view(request):
    auth.logout(request)
    return HttpResponseRedirect(reverse('users:login'))

class UserRedirectView(RedirectView):
    permanent = False

    def get_redirect_url(self):
        return reverse("users:detail",
                       kwargs={"username": self.request.user.username})

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(UserRedirectView, self).dispatch(*args, **kwargs)