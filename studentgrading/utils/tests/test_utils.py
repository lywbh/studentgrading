# -*- coding: utf-8 -*-
from test_plus import TestCase
import environ

from ..import_data import get_student_dataset


class ImportXlsTests(TestCase):

    def test_get_student_dateset(self):
        with self.assertRaises(TypeError):
            get_student_dataset(
                str((environ.Path(__file__) - 1).path('test1.txt'))
            )