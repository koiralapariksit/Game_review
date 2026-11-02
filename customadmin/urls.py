from django.urls import path
from . import views

app_name = 'customadmin'

urlpatterns = [
    path('', views.admin_dashboard, name='dashboard'),
    path('login/', views.admin_login, name='login'),
    path('logout/', views.admin_logout, name='logout'),
    path('community/moderate/<int:post_id>/', views.moderate_post, name='moderate_post'),
    path('community/report/<int:report_id>/resolve/', views.resolve_report, name='resolve_report'),
]
