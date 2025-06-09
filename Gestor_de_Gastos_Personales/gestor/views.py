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

@login_required
def alertas_presupuesto(request):
    presupuestos = Presupuesto.objects.filter(usuario=request.user)
    alertas = []
    for presupuesto in presupuestos:
        total_gastado = Transaccion.objects.filter(
            categoria=presupuesto.categoria,
            usuario=request.user
        ).aggregate(Sum('monto'))['monto__sum'] or Decimal('0')

        limite_decimal = Decimal(str(presupuesto.limite))

        if total_gastado >= Decimal('0.8') * limite_decimal:
            porcentaje = round((total_gastado / limite_decimal) * Decimal('100'), 2)
            alertas.append({
                'categoria': presupuesto.categoria.nombre,
                'limite': limite_decimal,
                'gastado': total_gastado,
                'porcentaje': porcentaje,
            })

    return render(request, 'gestor/alertas.html', {
        'alertas': alertas,
    })
