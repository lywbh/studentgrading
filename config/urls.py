from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib import admin


urlpatterns = patterns(
    '',

    # Django Admin, use {% url 'admin:index' %}
    url(settings.ADMIN_URL, include(admin.site.urls)),

    url(
        r'^core/',
        include("studentgrading.core.urls", namespace="core")
    ),

    url(
        r'^api/',
        include('studentgrading.core.api', namespace='api')
    ),
    url(
        r'^api/api-auth/',
        include('rest_framework.urls', namespace='rest_framework')),
)
