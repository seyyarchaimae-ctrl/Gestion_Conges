from django.urls import path
from teams.views import team_list
from . import views

urlpatterns = [
    path('', team_list, name='team_list'),
    path('collaborators/', views.get_collaborators, name='get_collaborators'),
    path('collaborators/page/', views.collaborators_page, name='collaborators_page'),
    path('collaborators/<int:collaborator_id>/', views.get_collaborator_profile, name='get_collaborator_profile'),
    path('collaborators/<int:collaborator_id>/profile/', views.collaborator_profile_page, name='collaborator_profile_page'),
    path('managers/', views.managers_page, name='managers_page'),
    path('managers-data/', views.get_managers, name='get_managers'),
    path('managers/<int:manager_id>/demandes/', views.manager_detail, name='manager_detail'),
]
