from django.urls import path
from . import views

urlpatterns = [
    path('', views.login, name='login'),  # Vista principal
    path('login/', views.login, name='login'),
    path('control/', views.control, name='control'),
    path('autocomplete/empresa/', views.autocomplete_empresa, name='autocomplete_empresa'),
    path('autocomplete/chuto/', views.autocomplete_chuto, name='autocomplete_chuto'),
    path('autocomplete/tanque/', views.autocomplete_tanque, name='autocomplete_tanque'),
    path('autocomplete/destino/', views.autocomplete_destino, name='autocomplete_destino'),
    path('autocomplete/conductor/', views.autocomplete_conductor, name='autocomplete_conductor'),
    path('reporte_historial/', views.reporte_historial, name='reporte_historial'),
    path('logout/', views.logout, name='logout'),
]