# -*- coding: utf-8 -*-

from test_plus.test import TestCase
from ..import_data import import_student, import_student_takes
from studentgrading.core.models import Student, Class, Takes


class MethodTests(TestCase):

    def test_import_student(self):
        import environ
        xlpath = str((environ.Path(__file__) - 1).path('stu.xls'))
        self.assertEqual(Student.objects.count(), 0)
        Class.objects.create(class_id='301')
        import_student(xlpath)

        self.assertEqual(Student.objects.count(), 10)

    def import_student_takes(self):
        import environ
        xlpath = str((environ.Path(__file__) - 1).path('stu.xls'))
        self.assertEqual(Takes.objects.count(), 0)
        Class.objects.create(class_id='301')
        import_student(xlpath)
        cours = Course.objects.create(
            title='Software Engineering Project',
            year=2015,
            semester='AUT',
        )
        import_student_takes(xlpath, cours.pk)

        self.assertEqual(Takes.objects.count(), 10)
