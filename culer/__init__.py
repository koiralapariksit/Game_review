"""
Culer Django Project Initialization.
Includes compatibility fixes for Python 3.15 runtime.
"""
from copy import copy
import django.template.context as d_context

# Python 3.15 compatibility fix for copy(super()) in Django template BaseContext
def _basecontext_copy(self):
    duplicate = self.__class__.__new__(self.__class__)
    duplicate.dicts = self.dicts[:]
    return duplicate

d_context.BaseContext.__copy__ = _basecontext_copy

