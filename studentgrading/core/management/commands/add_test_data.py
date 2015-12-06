# -*- coding: utf-8 -*-
from decimal import Decimal

from django.core.management.base import BaseCommand

from studentgrading.users.models import User
from studentgrading.core.tests import factories
from studentgrading.core.models import (
    ContactInfoType, Class, Course, Instructor, Teaches,
    Student, Takes, CourseAssignment,
)


class Command(BaseCommand):
    args = 'no args needed'
    help = 'Add tests data to db'

    def handle(self, *args, **options):

        # Create a superuser
        User.objects.create_superuser(username='admin', password='sep2015')

        # Create contact info types
        info_type_qq = ContactInfoType.objects.create(type_string='QQ')
        info_type_email = ContactInfoType.objects.create(type_string='Email')
        info_type_telephone = ContactInfoType.objects.create(type_string='Telephone')

        # Create classes
        class_303 = Class.objects.create(class_id='2012211303')
        class_304 = Class.objects.create(class_id='2012211304')
        class_305 = Class.objects.create(class_id='2012211305')
        class_306 = Class.objects.create(class_id='2012211306')

        # Create courses
        course_sep = Course.objects.create(
            title='Software Engineering Project',
            year=2015,
            semester='AUT',
        )
        course_dbc = Course.objects.create(
            title='Database Concepts',
            year=2015,
            semester='AUT',
        )
        course_ide = Course.objects.create(
            title='Introduction to Differential Equations',
            year=2015,
            semester='AUT',
        )

        course_fda = Course.objects.create(
            title='Foundations of Data Analysis',
            year=2015,
            semester='AUT',
        )

        # Create students and users for them
        user_stu_yifan = User.objects.create_user(
            username='2012211165',
            password='211165',
        )
        stu_yifan = Student.objects.create(
            user=user_stu_yifan,
            name='Yifan Y Liao',
            sex='M',
            s_id='2012211165',
            s_class=class_303,
        )

        user_stu_lanny = User.objects.create_user(
            username='2012211983',
            password='211983',
        )
        stu_lanny = Student.objects.create(
            user=user_stu_lanny,
            name='Lanny Ready',
            sex='M',
            s_id='2012211983',
            s_class=class_303,
        )

        user_stu_jojo = User.objects.create_user(
            username='2012211780',
            password='211780',
        )
        stu_jojo = Student.objects.create(
            user=user_stu_jojo,
            name='Jojo Atteberry',
            s_id='2012211780',
            s_class=class_303,
        )

        user_stu_gord = User.objects.create_user(
            username='2012211625',
            password='211625',
        )
        stu_gord = Student.objects.create(
            user=user_stu_gord,
            name='Gord Barker',
            s_id='2012211625',
            s_class=class_304,
        )

        user_stu_algar = User.objects.create_user(
            username='2012211207',
            password='211207',
        )
        stu_algar = Student.objects.create(
            user=user_stu_algar,
            name='Algar Terrell',
            s_id='2012211207',
            s_class=class_304,
        )

        user_stu_bryce = User.objects.create_user(
            username='2012211437',
            password='211437',
        )
        stu_bryce = Student.objects.create(
            user=user_stu_bryce,
            name='Bryce Romilly',
            s_id='2012211437',
            s_class=class_305,
        )

        user_stu_norris = User.objects.create_user(
            username='2012211030',
            password='211030',
        )
        stu_norris = Student.objects.create(
            user=user_stu_norris,
            name='Norris Faulkner',
            s_id='2012211030',
            s_class=class_305,
        )

        # Create instructors and users for them
        user_inst_ding = User.objects.create_user(
            username='1120378',
            password='120378',
        )
        inst_ding = Instructor.objects.create(
            user=user_inst_ding,
            inst_id='1120378',
            name='Ding Xiao',
            sex='M',
        )

        user_inst_paul = User.objects.create_user(
            username='1120960',
            password='120960',
        )
        inst_paul = Instructor.objects.create(
            user=user_inst_paul,
            inst_id='1120960',
            name='Paul Blanchard',
            sex='M',
        )

        user_michael = User.objects.create_user(
            username='1120232',
            password='120232',
        )
        inst_michael = Instructor.objects.create(
            user=user_michael,
            inst_id='1120232',
            name='Michael J. Mahometa',
            sex='M',
        )

        user_jennifer = User.objects.create_user(
            username='1120492',
            password='120492',
        )
        inst_jennifer = Instructor.objects.create(
            user=user_jennifer,
            inst_id='1120492',
            name='Jennifer Widom',
            sex='F',
        )

        # Create Teaches relationships
        dxiao_teaches_sep = Teaches.objects.create(
            instructor=inst_ding,
            course=course_sep,
        )

        paul_teaches_ide = Teaches.objects.create(
            instructor=inst_paul,
            course=course_ide,
        )

        michael_teaches_fda = Teaches.objects.create(
            instructor=inst_michael,
            course=course_fda,
        )

        jennifer_teaches_dbc = Teaches.objects.create(
            instructor=inst_jennifer,
            course=course_dbc,
        )

        michael_teaches_dbc = Teaches.objects.create(
            instructor=inst_michael,
            course=course_dbc,
        )

        # Create Takes relationship
        Takes.objects.create(student=stu_norris, course=course_dbc, )
        Takes.objects.create(student=stu_norris, course=course_ide, )
        Takes.objects.create(student=stu_norris, course=course_sep, )
        Takes.objects.create(student=stu_norris, course=course_fda, )

        Takes.objects.create(student=stu_bryce, course=course_ide, )

        Takes.objects.create(student=stu_algar, course=course_ide, )
        Takes.objects.create(student=stu_algar, course=course_fda, )

        Takes.objects.create(student=stu_gord, course=course_ide, )
        Takes.objects.create(student=stu_gord, course=course_sep, )
        Takes.objects.create(student=stu_gord, course=course_fda, )

        Takes.objects.create(student=stu_jojo, course=course_dbc, )
        Takes.objects.create(student=stu_jojo, course=course_ide, )
        Takes.objects.create(student=stu_jojo, course=course_sep, )
        Takes.objects.create(student=stu_jojo, course=course_fda, )

        Takes.objects.create(student=stu_lanny, course=course_dbc, )
        Takes.objects.create(student=stu_lanny, course=course_fda, )

        Takes.objects.create(student=stu_yifan, course=course_ide, )
        Takes.objects.create(student=stu_yifan, course=course_sep, )
        Takes.objects.create(student=stu_yifan, course=course_fda, )

        # Create assignments
        assignmnt_dbc_1 = CourseAssignment.objects.create(
            course=course_dbc,
            title='Chapter 1 assignment',
            grade_ratio=Decimal(0.1),
        )
        jennifer_teaches_dbc.assignments.add(assignmnt_dbc_1)
        michael_teaches_dbc.assignments.add(assignmnt_dbc_1)

        assignmnt_ide_1 = CourseAssignment.objects.create(
            course=course_ide,
            title='Chapter 1 assignment',
            grade_ratio=Decimal(0.1),
        )
        paul_teaches_ide.assignments.add(assignmnt_ide_1)

        assignmnt_sep_1 = CourseAssignment.objects.create(
            course=course_sep,
            title='Chapter 1 assignment',
            grade_ratio=Decimal(0.1),
        )
        dxiao_teaches_sep.assignments.add(assignmnt_sep_1)

        assignmnt_fda_1 = CourseAssignment.objects.create(
            course=course_fda,
            title='Chapter 1 assignment',
            grade_ratio=Decimal(0.1),
        )
        michael_teaches_fda.assignments.add(assignmnt_fda_1)

