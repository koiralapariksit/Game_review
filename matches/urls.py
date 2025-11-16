from django.urls import path
from . import views

app_name = 'matches'

urlpatterns = [
    path('', views.match_list, name='match_list'),
    path('<int:match_id>/', views.match_detail, name='match_detail'),
    path('upcoming/', views.upcoming_matches, name='upcoming_matches'),
    path('completed/', views.completed_matches, name='completed_matches'),
    # ✅ Fix here: remove 'matches/' prefix
    path('<int:match_id>/post_comment/', views.post_comment, name='post_comment'),
]
