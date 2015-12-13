import tablib
from django.conf import settings
import os


def get_student_dataset(xlpath):
    f = open(xlpath, 'rb')
    data = tablib.import_set(f.read())
    data.headers = ['s_id', 'class_id', 'name', 'sex']

    f.close()
    return data


def handle_uploaded_file(f):
    file_name = ""

    try:
        path = settings.MEDIA_ROOT
        if not os.path.exists(path):
            os.makedirs(path)

        file_name = path + f.name + time.strftime('%Y%m%d%H%M%S')
        destination = open(file_name, 'wb+')
        for chunk in f.chunks():
            destination.write(chunk)
        destination.close()
    except Exception as e:
        raise e

    return file_name


def delete_uploaded_file(file_name):
    os.remove(file_name)
