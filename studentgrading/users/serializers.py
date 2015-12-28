# -*- coding: utf-8 -*-
from django.conf import settings

from rest_framework import serializers

from .models import User


class UserSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        read_only=True,
        view_name='api:user-detail',
    )

    class Meta:
        model = User
        fields = ('url', 'id', 'username', 'is_staff', 'is_active', 'date_joined', )
