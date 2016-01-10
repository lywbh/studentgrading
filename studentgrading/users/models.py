# -*- coding: utf-8 -*-
"""
This file is almost a copy of https://github.com/fusionbox/django-authtools/blob/master/authtools/models.py
"""
from __future__ import unicode_literals, absolute_import

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.conf import settings
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType

from guardian.models import UserObjectPermission
from guardian.models import GroupObjectPermission
from guardian.shortcuts import assign_perm
from guardian.mixins import GuardianUserMixin


class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **kwargs):
        if not username:
            raise ValueError('Users must have a username')
        user = self.model(username=username, **kwargs)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, **kwargs):
        user = self.create_user(**kwargs)
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user


class User(GuardianUserMixin, PermissionsMixin, AbstractBaseUser):

    username = models.CharField(
        max_length=255,
        unique=True,
    )
    is_staff = models.BooleanField(_('staff status'), default=False,
                                   help_text=_('Designates whether the user can log into this admin '
                                   'site.'))
    is_active = models.BooleanField(_('active'), default=True,
                                    help_text=_('Designates whether this user should be treated as '
                                    'active. Unselect this instead of deleting accounts.'))
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ['username']
        verbose_name = _('user')
        verbose_name_plural = _('users')
        permissions = (
            ('view_user', 'View User'),
        )

    def get_full_name(self):
        return self.username

    def get_short_name(self):
        return self.username

    def __str__(self):
        return self.username


@receiver(post_save, sender=User)
def user_assign_perms(sender, **kwargs):
    """
    Assign related perms to user after creation
    """
    user, created = kwargs['instance'], kwargs['created']
    if created and user.pk != settings.ANONYMOUS_USER_ID:
        assign_perm('users.view_user', user)
        assign_perm('users.view_user', user, user)
        assign_perm('users.change_user', user)
        assign_perm('users.change_user', user, user)


@receiver(pre_delete, sender=User)
def remove_obj_perms_connected_with_user(sender, instance, **kwargs):
    """
    Remove all object permissions connected with user before deletion
    """
    filters = Q(content_type=ContentType.objects.get_for_model(instance),
                object_pk=instance.pk)
    UserObjectPermission.objects.filter(filters).delete()
    GroupObjectPermission.objects.filter(filters).delete()
