from django.urls import path
from . import views

app_name = 'conges'

urlpatterns = [
    path('', views.home, name='home'),
    path('conges/', views.conges_list, name='conges_list'),
    path('conges/nouveau/', views.conge_new, name='conge_new'),
    path('conges/<int:pk>/', views.conge_detail, name='conge_detail'),
    path('demande-conge/<int:collaborator_id>/', views.demande_conge_form, name='demande_conge_form'),
    path('historique-demandes/<int:collaborator_id>/', views.historique_demandes, name='historique_demandes'),
    path("demandes/", views.liste_demandes_manager, name="liste_demandes_manager"),
    path("demandes/<int:demande_id>/decision/", views.decision_manager, name="decision_manager"),
    path('demande/<int:pk>/modifier/', views.modifier_demande, name='modifier_demande'),
    path('demande/<int:pk>/annuler/', views.annuler_demande, name='annuler_demande'),
]