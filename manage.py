#!/usr/bin/env python
import sys
import environ
import os

if __name__ == "__main__":

    environ.Env.read_env()
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
