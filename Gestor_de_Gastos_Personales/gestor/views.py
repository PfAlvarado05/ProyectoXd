from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Sum
from decimal import Decimal
import datetime

from .forms import (
    RegistroForm, CategoriaForm, TransaccionForm, PresupuestoForm, 
    IngresoForm, FiltroFechaForm
)
from .models import CategoriaGasto, Transaccion, Presupuesto, Ingreso

# Librerías para PDF y Excel (asegúrate de instalarlas: pip install xhtml2pdf openpyxl)
from xhtml2pdf import pisa
from django.template.loader import get_template
import openpyxl
from io import BytesIO


def registro_usuario(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuario registrado correctamente. Ahora inicia sesión.')
            return redirect('login')
    else:
        form = RegistroForm()
    return render(request, 'gestor/registro.html', {'form': form})


def login_usuario(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
    return render(request, 'gestor/login.html')


@login_required
def logout_usuario(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    # Datos resumen para mostrar en el dashboard
    total_gastos = Transaccion.objects.filter(usuario=request.user).aggregate(total=Sum('monto'))['total'] or 0
    total_ingresos = Ingreso.objects.filter(usuario=request.user).aggregate(total=Sum('monto'))['total'] or 0
    balance = total_ingresos - total_gastos
    context = {
        'total_gastos': total_gastos,
        'total_ingresos': total_ingresos,
        'balance': balance,
    }
    return render(request, 'gestor/dashboard.html', context)


@login_required
def agregar_categoria(request):
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría agregada con éxito.')
            return redirect('dashboard')
    else:
        form = CategoriaForm()
    return render(request, 'gestor/agregar_categoria.html', {'form': form})


@login_required
def agregar_transaccion(request):
    if request.method == 'POST':
        form = TransaccionForm(request.POST)
        if form.is_valid():
            transaccion = form.save(commit=False)
            transaccion.usuario = request.user
            transaccion.save()
            messages.success(request, 'Transacción agregada con éxito.')
            return redirect('dashboard')
    else:
        form = TransaccionForm()
    return render(request, 'gestor/agregar_gasto.html', {'form': form})


@login_required
def agregar_presupuesto(request):
    if request.method == 'POST':
        form = PresupuestoForm(request.POST)
        if form.is_valid():
            presupuesto = form.save(commit=False)
            presupuesto.usuario = request.user
            presupuesto.save()
            messages.success(request, 'Presupuesto agregado con éxito.')
            return redirect('dashboard')
    else:
        form = PresupuestoForm()
    return render(request, 'gestor/crear_presupuesto.html', {'form': form})


@login_required
def agregar_ingreso(request):
    if request.method == 'POST':
        form = IngresoForm(request.POST)
        if form.is_valid():
            ingreso = form.save(commit=False)
            ingreso.usuario = request.user
            ingreso.save()
            messages.success(request, 'Ingreso agregado con éxito.')
            return redirect('dashboard')
    else:
        form = IngresoForm()
    return render(request, 'gestor/agregar_ingreso.html', {'form': form})


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


@login_required
def filtrar_transacciones(request):
    form = FiltroFechaForm(request.GET or None)
    transacciones = Transaccion.objects.filter(usuario=request.user).order_by('-fecha')
    ingresos = Ingreso.objects.filter(usuario=request.user).order_by('-fecha')

    if form.is_valid():
        fecha_inicio = form.cleaned_data.get('fecha_inicio')
        fecha_fin = form.cleaned_data.get('fecha_fin')
        if fecha_inicio:
            transacciones = transacciones.filter(fecha__gte=fecha_inicio)
            ingresos = ingresos.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            transacciones = transacciones.filter(fecha__lte=fecha_fin)
            ingresos = ingresos.filter(fecha__lte=fecha_fin)

    context = {
        'transacciones': transacciones,
        'ingresos': ingresos,
        'form': form,
    }
    return render(request, 'gestor/filtro.html', context)


@login_required
def exportar_pdf(request):
    transacciones = Transaccion.objects.filter(usuario=request.user)
    ingresos = Ingreso.objects.filter(usuario=request.user)
    template_path = 'gestor/pdf_template.html'
    context = {'transacciones': transacciones, 'ingresos': ingresos, 'usuario': request.user}
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_gastos_ingresos.pdf"'
    template = get_template(template_path)
    html = template.render(context)

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error al generar PDF <pre>' + html + '</pre>')
    return response


@login_required
def exportar_excel(request):
    transacciones = Transaccion.objects.filter(usuario=request.user)
    ingresos = Ingreso.objects.filter(usuario=request.user)

    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "Transacciones"
    ws1.append(['Categoría', 'Monto', 'Fecha', 'Descripción'])
    for t in transacciones:
        ws1.append([t.categoria.nombre, float(t.monto), t.fecha.strftime('%Y-%m-%d'), t.descripcion])

    ws2 = wb.create_sheet(title="Ingresos")
    ws2.append(['Monto', 'Fecha', 'Descripción'])
    for i in ingresos:
        ws2.append([float(i.monto), i.fecha.strftime('%Y-%m-%d'), i.descripcion])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="reporte_gastos_ingresos.xlsx"'
    output = BytesIO()
    wb.save(output)
    response.write(output.getvalue())
    return response
