# community/urls.py
from django.urls import path
from . import views

app_name = 'community'

urlpatterns = [
    path('', views.post_list, name='post_list'),
    path('post/create/', views.post_create, name='post_create'),
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('post/<int:pk>/comment/', views.add_comment, name='add_comment'),
]
