from django.urls import path
from . import views

app_name = 'camp'  # Optional but recommended for namespacing

urlpatterns = [
    path('', views.home, name='home'),
    path('media/', views.media, name='media'),  # ✅ Corrected
]
