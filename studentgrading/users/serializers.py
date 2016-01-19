# -*- coding: utf-8 -*-
from rest_framework import serializers

from .models import User


class ReadlUserSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = User
        fields = ('url', 'id', 'username', 'date_joined', )
        read_only_fields = ('username', 'date_joined', )
        extra_kwargs = {
            'url': {'view_name': 'api:user-detail'}
        }


class CreateUserSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = User
        fields = ('url', 'id', 'username', 'date_joined', )
        read_only_fields = ('date_joined', )
        extra_kwargs = {
            'url': {'view_name': 'api:user-detail'}
        }
