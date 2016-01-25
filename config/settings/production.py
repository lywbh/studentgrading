# -*- coding: utf-8 -*-
'''
Production Configurations
'''
from config.settings.common import *

# SECRET CONFIGURATION
# ------------------------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY")

ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
