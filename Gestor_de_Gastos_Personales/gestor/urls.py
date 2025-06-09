from django.urls import path
from . import views

urlpatterns = [
    path('grafico/', views.grafico_gastos, name='grafico'),
    path('alertas/', views.alertas_presupuesto, name='alertas'),
]
