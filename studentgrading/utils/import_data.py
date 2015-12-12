from ..core.models import *
import tablib
from studentgrading.users.models import User


def get_class_pk(row):
    return Class.objects.get(class_id=str(row[1])).pk


def get_student_pk(row):
    return Student.objects.get(s_id=str(row[0])).pk


def get_student_dataset(xlpath):
    f = open(xlpath, 'rb')
    data = tablib.import_set(f.read())
    data.headers = ['s_id', 'class_id', 'name', 'sex']

    f.close()
    return data


def import_student_takes(xlpath, course_pk):
    data = get_student_dataset(xlpath)
    data.append_col(get_student_pk, header='student')
    data.append_col(course_pk, header='course')
    del data['s_id']
    del data['class_id']
    del data['name']
    del data['sex']

    rows = data.dict

    for row in rows:
        stu = Student.objects.get(pk=row['student'])
        cours = Course.objects.get(pk=row['course'])
        Takes.objects.create(student=stu, course=cours)


def import_student(xlpath):
    data = get_student_dataset(xlpath)
    data.insert_col(1, get_class_pk, header='s_class')
    del data['class_id']

    rows = data.dict

    for row in rows:
        s_class = Class.objects.get(pk=str(row['s_class']))
        # init username  paswd
        s_user = User.objects.create_user(
            username=row['s_id'],
            password=row['s_id']
        )

        Student.objects.create(
            user=s_user,
            name=row['name'],
            sex=row['sex'],
            s_id=row['s_id'],
            s_class=s_class
        )
