# -*- coding: utf-8 -*-
import json
import random
from decimal import Decimal

import factory
from faker.providers import BaseProvider

from studentgrading.core.models import (
    CourseAssignment, Course,
)


class CourseProvider(BaseProvider):
    def __init__(self, *args, **kwargs):
        super(CourseProvider, self).__init__(*args, **kwargs)
        import os
        with open(os.path.dirname(os.path.abspath(__file__)) + '/courses.json') as f:
            self.courses = json.load(f)

    def course_title(self):
        return self.courses[random.randint(0, len(self.courses) - 1)]['title']

    def course_year(self):
        return self.courses[random.randint(0, len(self.courses) - 1)]['year']

    def course_semester(self):
        choices = Course.SEMESTER_CHOICES
        return choices[random.randint(0, len(choices) - 1)][0]

factory.Faker.add_provider(CourseProvider)


class CourseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Course

    title = factory.Faker('course_title')
    year = factory.Faker('course_year')
    semester = factory.Faker('course_semester')


class CourseAssignmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CourseAssignment

    course = factory.SubFactory(CourseFactory)
    title = factory.LazyAttributeSequence(
        lambda o, n: '{0}#{1}'.format(o.course.title, n)
    )
    grade_ratio = Decimal(0.1)
