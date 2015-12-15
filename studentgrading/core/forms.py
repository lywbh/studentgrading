# -*- coding: utf-8 -*-

from django.contrib.auth.forms import AuthenticationForm
from django import forms

from .models import get_role_of


class LoginAuthenticationForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        role = get_role_of(user)
        if not role:
            raise forms.ValidationError(
                "Invalid user type",
                code='invalid',
            )
