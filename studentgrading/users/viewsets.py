# -*- coding: utf-8 -*-
from rest_framework import viewsets
from rest_framework import filters

from .serializers import NormalUserSerializer, AdminUserSerializer
from .models import User
from .permissions import UserObjectPermissions


class UserViewSet(viewsets.ModelViewSet):
    """
    User resource.
    """
    queryset = User.objects.all()
    filter_backends = (filters.DjangoObjectPermissionsFilter, )
    permission_classes = (UserObjectPermissions, )

    def get_serializer_class(self):
        if self.request.user.is_staff:
            return AdminUserSerializer
        return NormalUserSerializer
