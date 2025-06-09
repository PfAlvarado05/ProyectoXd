from django.urls import path
from . import views

urlpatterns = [
    path('grafico/', views.grafico_gastos, name='grafico'),
]
