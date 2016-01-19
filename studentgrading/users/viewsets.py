# -*- coding: utf-8 -*-
from rest_framework import viewsets
from rest_framework import filters

from .serializers import ReadlUserSerializer, CreateUserSerializer
from .models import User
from .permissions import IsUserItself


SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')


class UserViewSet(viewsets.ModelViewSet):
    """
    User resource.
    """
    queryset = User.objects.all()
    filter_backends = (filters.DjangoObjectPermissionsFilter, )
    permission_classes = (IsUserItself, )

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return ReadlUserSerializer
        else:
            return CreateUserSerializer
