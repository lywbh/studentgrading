# -*- coding: utf-8 -*-

from django.contrib import admin
from django.forms.widgets import Widget
from django.forms.utils import flatatt
from django.forms import ModelForm
from django.utils.html import format_html

from .models import (
    Instructor, Student, Course, Class,
    Group, CourseAssignment, ContactInfoType,
    InstructorContactInfo, StudentContactInfo, GroupContactInfo,
    Teaches, Takes,
)


# Class Admin
# ------------------------------------------------------------------------------
class StudentInlineForClass(admin.TabularInline):
    verbose_name = ''
    model = Student
    extra = 0

    readonly_fields = ('s_id', 'name', 'sex', )

    def has_add_permission(self, request):
        return False


class ClassAdmin(admin.ModelAdmin):
    inlines = [StudentInlineForClass, ]


# Instructor Admin
# ------------------------------------------------------------------------------
class InstructorContactInfoInline(admin.StackedInline):
    model = InstructorContactInfo
    extra = 1


class InstructorAdmin(admin.ModelAdmin):
    fields = ['user', 'name', 'inst_id', 'sex', ]
    list_display = ['name', 'user', 'inst_id', ]
    inlines = (InstructorContactInfoInline, )


# Student Admin
# ------------------------------------------------------------------------------
class StudentContactInfoInline(admin.StackedInline):
    model = StudentContactInfo
    extra = 1


class StudentAdmin(admin.ModelAdmin):
    fields = ['user', 'name', 's_id', 'sex', 's_class', ]
    list_display = ['name', 'user', 's_id', 's_class', ]
    inlines = (StudentContactInfoInline, )


# Takes relationship Admin
# ------------------------------------------------------------------------------
class TakesAdmin(admin.ModelAdmin):
    list_display = ['student', 'get_course_title', 'get_course_year',
                    'get_course_semester', ]

    def get_course_title(self, obj):
        return obj.course.title
    get_course_title.short_description = 'course'
    get_course_title.admin_order_field = 'course__title'

    def get_course_year(self, obj):
        return obj.course.year
    get_course_year.short_description = 'year'
    get_course_year.admin_order_field = 'course__year'

    def get_course_semester(self, obj):
        return obj.course.get_semester_display()
    get_course_semester.short_description = 'semester'
    get_course_semester.admin_order_field = 'course__semester'


# Course Admin
# ------------------------------------------------------------------------------


# Group Admin
# ------------------------------------------------------------------------------
class GroupContactInfoInline(admin.StackedInline):
    model = InstructorContactInfo
    extra = 1


class GroupAdmin(admin.ModelAdmin):
    inlines = (GroupContactInfoInline, )


# Teaches relationship Admin
# ------------------------------------------------------------------------------
class TeachesAdmin(admin.ModelAdmin):
    list_display = ['instructor', 'get_course_title', 'get_course_year',
                    'get_course_semester', 'assignments_count', ]

    def get_course_title(self, obj):
        return obj.course.title
    get_course_title.short_description = 'course'
    get_course_title.admin_order_field = 'course__title'

    def get_course_year(self, obj):
        return obj.course.year
    get_course_year.short_description = 'year'
    get_course_year.admin_order_field = 'course__year'

    def get_course_semester(self, obj):
        return obj.course.get_semester_display()
    get_course_semester.short_description = 'semester'
    get_course_semester.admin_order_field = 'course__semester'


# Course assignment Admin
# ------------------------------------------------------------------------------
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('course', 'title', 'assigned_dtm', 'deadline_dtm', )


admin.site.register(Instructor, InstructorAdmin)
admin.site.register(Teaches, TeachesAdmin)
admin.site.register(Student, StudentAdmin)
admin.site.register(Course)
admin.site.register(Class, ClassAdmin)
admin.site.register(ContactInfoType)
admin.site.register(Takes, TakesAdmin)
