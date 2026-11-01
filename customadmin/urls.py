from django.urls import path
from . import views

app_name = 'customadmin'

urlpatterns = [
    path('', views.admin_dashboard, name='dashboard'),
    path('login/', views.admin_login, name='login'),
    path('logout/', views.admin_logout, name='logout'),
]

