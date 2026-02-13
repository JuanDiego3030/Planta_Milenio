
from django.urls import path

from . import views

urlpatterns = [
    path('reporte_pdf/materia_prima/', views.reporte_pdf_materia_prima, name='reporte_pdf_materia_prima'),
    path('reporte_pdf/personal/', views.reporte_pdf_personal, name='reporte_pdf_personal'),
    path('autocomplete/persona/nombre/', views.autocomplete_persona_nombre, name='autocomplete_persona_nombre'),
    path('autocomplete/persona/apellido/', views.autocomplete_persona_apellido, name='autocomplete_persona_apellido'),
    path('autocomplete/persona/cedula/', views.autocomplete_persona_cedula, name='autocomplete_persona_cedula'),
    path('autocomplete/persona/placa/', views.autocomplete_persona_placa, name='autocomplete_persona_placa'),
    path('', views.login, name='login'),  # Vista principal
    path('login/', views.login, name='login'),
    path('control/', views.control, name='control'),
    path('autocomplete/persona/empresa/', views.autocomplete_persona_empresa, name='autocomplete_persona_empresa'),
    path('control_personas/', views.control_personas, name='control_personas'),
    path('autocomplete/empresa/', views.autocomplete_empresa, name='autocomplete_empresa'),
    path('autocomplete/chuto/', views.autocomplete_chuto, name='autocomplete_chuto'),
    path('autocomplete/tanque/', views.autocomplete_tanque, name='autocomplete_tanque'),
    path('autocomplete/destino/', views.autocomplete_destino, name='autocomplete_destino'),
    path('autocomplete/conductor/', views.autocomplete_conductor, name='autocomplete_conductor'),
    path('reporte_historial/', views.reporte_historial, name='reporte_historial'),
    path('reportes/', views.reportes, name='reportes'),
    path('logout/', views.logout, name='logout'),
    path('usuarios/', views.control_usuarios, name='control_usuarios'),
    path('auditoria/', views.auditoria, name='auditoria'),
]