
# transfers/urls.py
from django.urls import path
from . import views

# URL namespace for the transfers app
app_name = 'transfers'

urlpatterns = [
    # Main transfer list view - supports filtering by type via GET parameter
    path('', views.transfer_list, name='transfer_list'),
    
    # Latest confirmed transfers
    path('latest/', views.latest_transfers, name='latest_transfers'),
    
    # Transfer rumors
    path('rumors/', views.transfer_rumors, name='transfer_rumors'),
    
    # Individual transfer detail view
    path('<int:id>/', views.transfer_detail, name='transfer_detail'),
]
