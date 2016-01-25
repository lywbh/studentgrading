# studentgrading

A student grading website based on Django 1.9
The project structure is based on [pydanny/cookiecutter-django](https://github.com/pydanny/cookiecutter-django)

## Prerequisites

Python 3.4

## Installation

First make a virtual environment using `virtualenvwrappper`:
```
$ mkvirtualenv project_name
```
Then install libs under project root:
```
$ pip install -r requirements.txt
```  
Create `.env` file to store secret info and place it in project root:
e.g.
```txt
DJANGO_SETTINGS_MODULE=config.settings.local_yifan
SECRET_KEY=u&ai&6cw@_^9m(^wm)1z529-3$(9av(!=p6ct=8h@io($zza21
DATABASE_URL=sqlite:////path/to/your/sqlite/file
```
The DATABASE url pattern can be found at
[kennethreitz/dj-database-url](https://github.com/kennethreitz/dj-database-url#url-schema)

Use your own setting file(place it in setting directory):
```
DJANGO_SETTINGS_MODULE=config.settings.local_your_name
```

