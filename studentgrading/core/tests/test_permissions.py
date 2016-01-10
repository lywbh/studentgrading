# -*- coding: utf-8 -*-
from guardian.shortcuts import assign_perm, get_objects_for_user
from test_plus.test import TestCase

from . import factories


class PermsTests(TestCase):

    def test_perms(self):
        stu1 = factories.StudentFactory()
        stu_user1 = stu1.user
        self.assertTrue(stu_user1.has_perm('core.view_student'))
        self.assertTrue(stu_user1.has_perm('core.view_student', stu1))

        stu2 = factories.StudentFactory()
        stu_user2 = stu2.user

        self.assertFalse(stu_user2.has_perm('core.view_student', stu1))
        assign_perm('core.view_student_base', stu_user2, stu1)
        self.assertEqual(
            list(get_objects_for_user(stu_user2, 'core.view_student_base')),
            [stu1]
        )

        stu2.delete()
        print('{0}'.format(stu2.user.get_all_permissions()))
