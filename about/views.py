# about/views.py
from django.shortcuts import render

def about_page(request):
    return render(request, 'about/about.html', {
        'page_title': 'About FC Barcelona'
    })
