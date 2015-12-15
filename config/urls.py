from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.contrib import admin

urlpatterns = patterns(
    '',

    # Django Admin, use {% url 'admin:index' %}
    url(settings.ADMIN_URL, include(admin.site.urls)),

    url(
        r'^core/',
        include("studentgrading.core.urls", namespace="core")
    ),
)
"""
    # User management
    url(
        r'^users/',
        include("studentgrading.users.urls", namespace="users")
    ),
"""