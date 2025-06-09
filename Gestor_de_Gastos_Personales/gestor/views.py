from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from decimal import Decimal
from .models import Transaccion, CategoriaGasto, Presupuesto

@login_required
def grafico_gastos(request):
    categorias = CategoriaGasto.objects.all()
    etiquetas = []
    datos = []
    for categoria in categorias:
        total = Transaccion.objects.filter(
            categoria=categoria,
            usuario=request.user
        ).aggregate(Sum('monto'))['monto__sum'] or 0
        if total > 0:
            etiquetas.append(categoria.nombre)
            datos.append(float(total))
    return render(request, 'gestor/grafico.html', {
        'etiquetas': etiquetas,
        'datos': datos,
    })