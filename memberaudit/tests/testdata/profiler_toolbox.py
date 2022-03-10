# flake8: noqa
"""
This is a standalone scripts that generates a test character
"""

import inspect
import os
import sys

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
myauth_dir = (
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(currentdir))))
    + "/myauth"
)
sys.path.insert(0, myauth_dir)


import django

# init and setup django project
print("Initializing Django...")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myauth.settings.local")
django.setup()

import cProfile

from memberaudit.core.fittings import Fitting
from memberaudit.tests.test_core_fittings import read_fitting_file


def main():
    fitting.required_skills()


fitting_text = read_fitting_file("fitting_tristan.txt")
fitting = Fitting.create_from_eft(fitting_text)

cProfile.run("main()", sort="cumtime")
