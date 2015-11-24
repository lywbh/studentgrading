# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.contrib import auth
from django.contrib.auth.forms import AuthenticationForm
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.core.urlresolvers import reverse
from django.views.generic import View, DetailView, ListView, RedirectView

from braces.views import LoginRequiredMixin

from .models import User

class UserLoginView(View):

    def post(self, request, *args, **kwargs):
        form = AuthenticationForm(request)
        # form = LoginForm(request.POST)
        if form.is_valid():
            user = auth.authenticate(username=form.cleaned_data['username'],
                                     password=form.cleaned_data['password'])
            if user is not None:
                if user.is_active:
                    auth.login(request, user)
                    return redirect(reverse('users:detail', kwargs={"username": request.user.username}))
                else:
                    raise Http404("disabled account")
            else:
                raise Http404("Invalid login")

    def get(self, requset, *args, **kwargs):
        return render(requset, 'users/login.html', {'form': AuthenticationForm()})

def logout_view(request):
    auth.logout(request)
    return redirect('users:login')

class UserRedirectView(RedirectView):
    permanent = False

    def get_redirect_url(self):
        return reverse("users:detail",
                       kwargs={"username": self.request.user.username})

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(UserRedirectView, self).dispatch(*args, **kwargs)

class UserDetailView(DetailView):
    model = User
    # These next two lines tell the view to index lookups by username
    # slug_field = "username"
    # slug_url_kwarg = "username"

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(UserDetailView, self).dispatch(*args, **kwargs)

class UserListView(ListView):
    model = User
    # These next two lines tell the view to index lookups by username
    # slug_field = "username"
    # slug_url_kwarg = "username"

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(UserListView, self).dispatch(*args, **kwargs)
