from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from .models import User_admin, Historial
from django.http import JsonResponse
from django.db import connections
from django.template.loader import render_to_string
from django.http import HttpResponse
import datetime



def login(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        password = request.POST.get('password', '')

        try:
            user = User_admin.objects.get(nombre=nombre)
            if user.bloqueado:
                messages.error(request, 'Usuario bloqueado')
            elif user.password == password or check_password(password, user.password):
                request.session['user_admin_id'] = user.id
                return redirect('control')
            else:
                messages.error(request, 'Contraseña incorrecta')
            return render(request, 'login.html')
        except User_admin.DoesNotExist:
            messages.error(request, 'Usuario no encontrado')
            return render(request, 'login.html')

    return render(request, 'login.html')

def format_number_backend(value):
    try:
        n = float(value)
        int_part, dec_part = f"{n:.5f}".split('.')
        int_part = "{:,}".format(int(int_part)).replace(",", ".")
        return f"{int_part},{dec_part}"
    except Exception:
        return value

def control(request):
    user_id = request.session.get('user_admin_id')
    if not user_id:
        messages.error(request, 'Debe iniciar sesión primero')
        return redirect('login')
    try:
        user = User_admin.objects.get(id=user_id)
    except User_admin.DoesNotExist:
        messages.error(request, 'Usuario no encontrado')
        return redirect('login')

    # --- Nueva lógica tipo index de app1 ---
    message = None
    error = None

    # Consultar empresas y conductores
    empresas = []
    try:
        with connections['sqlserver'].cursor() as cursor:
            cursor.execute("SELECT rif, nombre FROM empresas ORDER BY nombre")
            empresas = [{'id': row[0], 'rif': row[0], 'nombre': row[1]} for row in cursor.fetchall()]
    except Exception as e:
        error = f"Error al cargar empresas: {str(e)}"

    # Validación de orden por POST
    if request.method == 'POST' and request.POST.get('validar_fact_num'):
        fact_num = request.POST.get('validar_fact_num')
        proveedor_id = request.POST.get('proveedor_id')
        proveedor_nombre = request.POST.get('proveedor_nombre')
        fecha_orden = request.POST.get('fecha_orden')
        status = request.POST.get('status', 'A')
        empresa_rif = request.POST.get('empresa_rif')
        conductor_cedula = request.POST.get('conductor')
        vehiculo_placa = request.POST.get('vehiculo')
        vehiculo_remolque_placa = request.POST.get('vehiculo_remolque')
        destino_nombre = request.POST.get('destino')

        # --- Convertir fecha_orden a formato YYYY-MM-DD HH:MM:SS.mmm para SQL Server ---
        from datetime import datetime
        import pytz
        fecha_orden_sql = None
        venezuela_tz = pytz.timezone("America/Caracas")
        if fecha_orden:
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
                try:
                    dt = datetime.strptime(fecha_orden, fmt)
                    dt = venezuela_tz.localize(dt)
                    fecha_orden_sql = dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    break
                except Exception:
                    continue
        if not fecha_orden_sql:
            # Si no se pudo convertir, usar fecha y hora actual de Venezuela
            dt = datetime.now(venezuela_tz)
            fecha_orden_sql = dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        # --- Obtener datos completos de cada entidad desde ceres_romana ---
        empresa_id = 0
        empresa_nombre = ''
        try:
            with connections['ceres_romana'].cursor() as cursor:
                cursor.execute("SELECT TOP 1 Empresa_ID, Empresa_Nombre FROM empresa WHERE Empresa_Rif = %s", [empresa_rif])
                row = cursor.fetchone()
                if row:
                    empresa_id, empresa_nombre = row
        except Exception:
            pass

        vehiculo_id = 0
        vehiculo_nombre = ''
        if vehiculo_placa:
            try:
                with connections['ceres_romana'].cursor() as cursor:
                    cursor.execute("SELECT TOP 1 Vehiculo_id, Vehiculo_nombre FROM Vehiculo WHERE Vehiculo_placa = %s", [vehiculo_placa])
                    row = cursor.fetchone()
                    if row:
                        vehiculo_id, vehiculo_nombre = row
            except Exception:
                pass

        vehiculo_remolque_id = None
        vehiculo_remolque_nombre = ''
        if vehiculo_remolque_placa:
            try:
                with connections['ceres_romana'].cursor() as cursor:
                    cursor.execute("SELECT TOP 1 Vehiculo_Remolque_id, Vehiculo_Remolque_Nombre FROM Vehiculo_Remolque WHERE Vehiculo_Remolque_Placa = %s", [vehiculo_remolque_placa])
                    row = cursor.fetchone()
                    if row:
                        vehiculo_remolque_id, vehiculo_remolque_nombre = row
            except Exception:
                pass

        conductor_id = 0
        conductor_nombre = ''
        conductor_apellido = ''
        if conductor_cedula:
            try:
                with connections['ceres_romana'].cursor() as cursor:
                    cursor.execute("SELECT TOP 1 Conductor_id, Conductor_Nombre, Conductor_Apelido FROM conductor WHERE Conductor_Cedula = %s", [conductor_cedula])
                    row = cursor.fetchone()
                    if row:
                        conductor_id, conductor_nombre, conductor_apellido = row
            except Exception:
                pass

        destino_id = 0
        if destino_nombre:
            try:
                with connections['ceres_romana'].cursor() as cursor:
                    cursor.execute("SELECT TOP 1 Destino_Id FROM Destino WHERE Destino_Nombre = %s", [destino_nombre])
                    row = cursor.fetchone()
                    if row:
                        destino_id = row[0]
            except Exception:
                pass

        # --- Datos de producto (ajusta según tu lógica) ---
        # Se deben enviar valores válidos, no vacíos
        producto_id = '1'
        producto_codigo = '001'
        producto_nombre = 'Producto genérico'
        cantidad = 1
        peso = 0

        # --- Inserción en Orden_Profit_Insert (solo los 11 parámetros requeridos, sin OUTPUT) ---
        try:
            with connections['ceres_romana'].cursor() as cursor:
                cursor.execute("""
                    EXEC [dbo].[Orden_Profit_Insert] %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                """, [
                    fact_num or '',
                    status or 'A',
                    proveedor_id or '',
                    empresa_rif or '',
                    proveedor_nombre or '',
                    producto_id or '1',
                    producto_codigo or '001',
                    producto_nombre or 'Producto genérico',
                    cantidad if cantidad is not None else 1,
                    peso if peso is not None else 0,
                    fecha_orden_sql
                ])
        except Exception as e:
            # Si el error es "Ya este Codigo esta Registrado", mostrar mensaje amigable y no continuar
            if "Ya este Codigo esta Registrado" in str(e):
                error = f"La orden {fact_num} ya fue registrada previamente en Romana."
                return render(request, 'control.html', {
                    'registros': [],
                    'fact_num': '',
                    'message': message,
                    'error': error,
                    'empresas': empresas,
                })
            else:
                error = f"Error al validar la orden (Orden_Profit_Insert): {str(e)}"
                return render(request, 'control.html', {
                    'registros': [],
                    'fact_num': '',
                    'message': message,
                    'error': error,
                    'empresas': empresas,
                })

        # --- Obtener Orden_Id desde la tabla orden_profit ---
        orden_id = None
        try:
            with connections['ceres_romana'].cursor() as cursor:
                cursor.execute(
                    "SELECT TOP 1 orden_id FROM orden_profit WHERE orden = %s ORDER BY orden_id DESC",
                    [fact_num]
                )
                row = cursor.fetchone()
                if row:
                    orden_id = row[0]
        except Exception:
            orden_id = None

        # --- Inserción en Orden_Profit_Transporte_Insert ---
        try:
            with connections['ceres_romana'].cursor() as cursor:
                cursor.execute("""
                    EXEC [dbo].[Orden_Profit_Transporte_Insert] %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                """, [
                    orden_id,  # Orden_Id obtenido arriba
                    fact_num,
                    producto_id,
                    producto_codigo,
                    None,  # Pesada_Id
                    empresa_id,
                    empresa_rif,
                    empresa_nombre,
                    vehiculo_id,
                    vehiculo_placa,
                    vehiculo_remolque_id,
                    vehiculo_remolque_placa,
                    conductor_id,
                    conductor_cedula,
                    conductor_nombre,
                    conductor_apellido,
                    destino_id,
                    destino_nombre
                ])
            # Solo usar messages.success, no sobrescribir message aquí
            messages.success(request, f"¡Registro exitoso! La orden {fact_num} fue registrada correctamente en Romana.")
        except Exception as e:
            error = f"Error al validar la orden (Orden_Profit_Transporte_Insert): {str(e)}"

        # Guardar en historial si hay placa y número de orden
        try:
            # Guardar en historial si hay placa y número de orden
            if vehiculo_placa and fact_num:
                Historial.objects.create(
                    placa_vehiculo=vehiculo_placa,
                    numero_orden=fact_num
                )
        except Exception as e:
            error = f"Error al guardar en historial: {str(e)}"

    # Consulta de órdenes (GET)
    raw = request.GET.get('fact_num', '').strip()
    if 'fact_num' not in request.GET:
        return render(request, 'control.html', {
            'registros': [],
            'fact_num': '',
            'message': message,
            'error': error,
        })

    vals = [v.strip() for v in raw.split(',') if v.strip()]
    if not vals:
        error = "Ingrese un fact_num válido."
        return render(request, 'control.html', {'registros': [], 'fact_num': raw, 'message': message, 'error': error})

    if len(vals) > 1:
        error = "Solo puedes consultar o registrar una orden de compra a la vez."
        return render(request, 'control.html', {'registros': [], 'fact_num': raw, 'message': message, 'error': error})

    if len(vals) == 1:
        sql = """
        select h.fact_num, h.fec_emis, h.status, h.co_cli, p.prov_des, h.descrip, h.comentario as hcoment,
               r.comentario as rcoment, r.reng_num, r.co_art, a.art_des, l.lin_des, r.total_art, r.uni_venta, r.pendiente
        from reng_ord r
        left join ordenes h on h.fact_num=r.fact_num
        left join prov p on p.co_prov=h.co_cli
        left join art a on a.co_art=r.co_art
        left join lin_art l on l.co_lin=a.co_lin
        where h.fact_num = %s
        """
        params = [vals[0]]
        message = f"Mostrando resultados para fact_num = {vals[0]}"
    else:
        placeholders = ','.join(['%s'] * len(vals))
        sql = f"""
        select h.fact_num, h.fec_emis, h.status, h.co_cli, p.prov_des, h.descrip, h.comentario as hcoment,
               r.comentario as rcoment, r.reng_num, r.co_art, a.art_des, l.lin_des, r.total_art, r.uni_venta, r.pendiente
        from reng_ord r
        left join ordenes h on h.fact_num=r.fact_num
        left join prov p on p.co_prov=h.co_cli
        left join art a on a.co_art=r.co_art
        left join lin_art l on l.co_lin=a.co_lin
        where h.fact_num IN ({placeholders})
        """
        params = vals
        message = f"Mostrando resultados para {len(vals)} fact_num(s)."

    registros = []
    orden_id_map = {}
    try:
        # Obtener orden_id para el/los fact_num consultados
        if vals:
            with connections['ceres_romana'].cursor() as cursor:
                cursor.execute(
                    f"SELECT orden, orden_id FROM orden_profit WHERE orden IN ({','.join(['%s']*len(vals))})",
                    vals
                )
                for row in cursor.fetchall():
                    orden_id_map[str(row[0])] = row[1]
        with connections['sqlserver'].cursor() as cursor:
            cursor.execute(sql, params)
            cols = [c[0] for c in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            for row in rows:
                reg = dict(zip(cols, row))
                # Formatear los campos numéricos
                for campo in ['total_art', 'uni_venta', 'pendiente']:
                    reg[campo] = format_number_backend(reg.get(campo))
                # Agregar orden_id si existe
                reg['orden_id'] = orden_id_map.get(str(reg.get('fact_num')))
                registros.append(reg)
    except Exception as e:
        registros = []
        error = str(e)

    status_cond = request.GET.get('status_cond', '')

    # Obtener historial de ingresos (ordenado por fecha descendente, últimos 30)
    historial = Historial.objects.all().order_by('-fecha_hora')[:30]

    return render(request, 'control.html', {
        'registros': registros,
        'fact_num': raw,
        'message': message,
        'error': error,
        'empresas': empresas,
        'status_cond': status_cond,
        'historial': historial,
        # 'conductores': conductores,  # Eliminado porque ya no se usa
    })

def autocomplete_empresa(request):
    q = request.GET.get('q', '').strip()
    results = []
    if q:
        with connections['ceres_romana'].cursor() as cursor:
            cursor.execute(
                "SELECT Empresa_ID, Empresa_Rif, Empresa_Nombre FROM empresa WHERE Empresa_Rif LIKE %s OR Empresa_Nombre LIKE %s ORDER BY Empresa_Nombre",
                [f"%{q}%", f"%{q}%"]
            )
            for row in cursor.fetchall():
                results.append({'id': row[0], 'rif': row[1], 'nombre': row[2]})
    return JsonResponse(results, safe=False)

def autocomplete_chuto(request):
    q = request.GET.get('q', '').strip()
    results = []
    if q:
        with connections['ceres_romana'].cursor() as cursor:
            cursor.execute(
                "SELECT Vehiculo_id, Vehiculo_placa, Vehiculo_nombre FROM Vehiculo WHERE Vehiculo_placa LIKE %s",
                [f"%{q}%"]
            )
            for row in cursor.fetchall():
                results.append({'id': row[0], 'placa': row[1], 'nombre': row[2]})
    return JsonResponse(results, safe=False)

def autocomplete_tanque(request):
    q = request.GET.get('q', '').strip()
    results = []
    if q:
        with connections['ceres_romana'].cursor() as cursor:
            cursor.execute(
                "SELECT Vehiculo_Remolque_Placa, Vehiculo_Remolque_Nombre, Vehiculo_Remolque_Descripcion FROM Vehiculo_Remolque WHERE Vehiculo_Remolque_Placa LIKE %s",
                [f"%{q}%"]
            )
            for row in cursor.fetchall():
                results.append({'placa': row[0], 'nombre': row[1], 'descripcion': row[2]})
    return JsonResponse(results, safe=False)

def autocomplete_destino(request):
    q = request.GET.get('q', '').strip()
    results = []
    with connections['ceres_romana'].cursor() as cursor:
        if q:
            cursor.execute(
                "SELECT Destino_Id, Destino_Nombre, Destino_Descripcion FROM Destino WHERE Destino_Nombre LIKE %s ORDER BY Destino_Nombre",
                [f"%{q}%"]
            )
        else:
            cursor.execute(
                "SELECT Destino_Id, Destino_Nombre, Destino_Descripcion FROM Destino ORDER BY Destino_Nombre"
            )
        for row in cursor.fetchall():
            results.append({'id': row[0], 'nombre': row[1], 'descripcion': row[2]})
    return JsonResponse(results, safe=False)

def autocomplete_conductor(request):
    q = request.GET.get('q', '').strip()
    results = []
    if q:
        with connections['ceres_romana'].cursor() as cursor:
            cursor.execute(
                "SELECT Conductor_id, Conductor_Cedula, Conductor_Nombre, Conductor_Apelido, Conductor_Descripcion, Conductor_Telf FROM conductor WHERE Conductor_Cedula LIKE %s",
                [f"%{q}%"]
            )
            for row in cursor.fetchall():
                results.append({
                    'id': row[0], 'cedula': row[1], 'nombre': row[2], 'apellido': row[3],
                    'descripcion': row[4], 'telf': row[5]
                })
    return JsonResponse(results, safe=False)

def reporte_historial(request):

    from weasyprint import HTML

    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    try:
        if fecha_inicio and fecha_fin:
            fecha_inicio_dt = datetime.datetime.strptime(fecha_inicio, "%Y-%m-%d")
            fecha_fin_dt = datetime.datetime.strptime(fecha_fin, "%Y-%m-%d") + datetime.timedelta(days=1)
            historial = Historial.objects.filter(
                fecha_hora__gte=fecha_inicio_dt,
                fecha_hora__lt=fecha_fin_dt
            ).order_by('-fecha_hora')
        else:
            historial = Historial.objects.all().order_by('-fecha_hora')[:100]
    except Exception:
        historial = Historial.objects.all().order_by('-fecha_hora')[:100]

    html_string = render_to_string('reporte_historial.html', {
        'historial': historial,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    })

    pdf_file = HTML(string=html_string).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_historial.pdf"'
    return response

def logout(request):
    request.session.flush()
    messages.success(request, 'Has cerrado sesión exitosamente.')
    return redirect('login')