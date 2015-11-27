# -*- coding: utf-8 -*-

from django.contrib import admin
from .models import (
    Instructor, Student, Course, Class,
    Group, CourseAssignment,
)

admin.site.register(Instructor)
admin.site.register(Student)
admin.site.register(Course)
admin.site.register(Class)

