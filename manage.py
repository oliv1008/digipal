#!/home/env/bin python2
import os
import sys

if __name__ == "__main__":
    #os.environ.setdefault("DJANGO_SETTINGS_MODULE", "digipal_django.settings")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "digipal_project.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
