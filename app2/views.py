from .crud import ControlAuditoria

# Vista de auditoría de transportes (orden_profit_transporte)
def auditoria(request):
    """Vista para ver, editar y borrar registros de orden_profit_transporte."""
    user_id = request.session.get('user_admin_id')
    if not user_id:
        from django.contrib import messages
        messages.error(request, 'Debe iniciar sesión primero')
        from django.shortcuts import redirect
        return redirect('login')
    try:
        from .models import User_admin
        user = User_admin.objects.get(id=user_id)
    except User_admin.DoesNotExist:
        from django.contrib import messages
        messages.error(request, 'Usuario no encontrado')
        from django.shortcuts import redirect
        return redirect('login')
    # Validar permiso de acceso a auditoría
    if not user.permiso_auditoria:
        from django.contrib import messages
        messages.error(request, 'No tiene permiso para acceder a la auditoría.')
        from django.shortcuts import redirect
        return redirect('login')
    ctrl = ControlAuditoria()
    from django.contrib import messages
    error = None
    message = None
    # Borrar registro por SQL directo (solo si no es solo consulta)
    if request.method == 'POST' and 'eliminar_registro' in request.POST:
        if user.solo_consulta:
            from django.contrib import messages
            messages.error(request, 'No tiene permiso para eliminar registros en auditoría.')
            from django.shortcuts import redirect
            return redirect('auditoria')
        registro_id = request.POST.get('registro_id')
        if registro_id:
            try:
                from django.db import connections
                with connections['ceres_romana'].cursor() as cursor:
                    cursor.execute("DELETE FROM orden_profit_transporte WHERE Orden_Transporte_Id = %s", [registro_id])
                messages.success(request, 'Registro eliminado correctamente.')
            except Exception as e:
                messages.error(request, f'Error al eliminar: {str(e)}')
            from django.shortcuts import redirect
            return redirect('auditoria')

    # Editar registro por SQL directo (solo si no es solo consulta)
    if request.method == 'POST' and 'editar_registro' in request.POST:
        if user.solo_consulta:
            from django.contrib import messages
            messages.error(request, 'No tiene permiso para editar registros en auditoría.')
            from django.shortcuts import redirect
            return redirect('auditoria')
        registro_id = request.POST.get('registro_id')
        campos = {}
        for campo in request.POST:
            if campo.startswith('campo_'):
                nombre = campo.replace('campo_', '')
                campos[nombre] = request.POST[campo]
        if registro_id and campos:
            try:
                from django.db import connections
                set_clause = ', '.join([f"{k} = %s" for k in campos.keys()])
                values = list(campos.values())
                values.append(registro_id)
                with connections['ceres_romana'].cursor() as cursor:
                    cursor.execute(f"UPDATE orden_profit_transporte SET {set_clause} WHERE Orden_Transporte_Id = %s", values)
                messages.success(request, 'Registro actualizado correctamente.')
            except Exception as e:
                messages.error(request, f'Error al actualizar: {str(e)}')
            from django.shortcuts import redirect
            return redirect('auditoria')
    # Buscador: filtrar por número de orden, placa de vehículo o conductor
    termino_busqueda = request.GET.get('buscar', '').strip()
    registros = ctrl.listar_registros(100)
    if termino_busqueda:
        termino = termino_busqueda.lower()
        registros = [r for r in registros if (
            termino in str(r.get('Numero_Orden', '')).lower() or
            termino in str(r.get('Vehiculo_Placa', '')).lower() or
            termino in str(r.get('Conductor_Nombre', '')).lower() or
            termino in str(r.get('Conductor_Apellido', '')).lower() or
            termino in str(r.get('Conductor_Cedula', '')).lower()
        )]
    # Paginación de registros de Romana
    from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
    page = request.GET.get('page', 1)
    paginator = Paginator(registros, 10)
    try:
        registros_pagina = paginator.page(page)
    except PageNotAnInteger:
        registros_pagina = paginator.page(1)
    except EmptyPage:
        registros_pagina = paginator.page(paginator.num_pages)

    return render(request, 'control_auditoria.html', {
        'registros': registros_pagina,
        'error': error,
        'message': message,
        'paginator': paginator,
        'page_obj': registros_pagina,
        'buscar': termino_busqueda,
        'user_admin': user,
    })
from .crud import ControlUsuarios
# Vista para gestión de usuarios
from django.views.decorators.cache import never_cache
@never_cache
def control_usuarios(request):
    user_id = request.session.get('user_admin_id')
    if not user_id:
        from django.contrib import messages
        messages.error(request, 'Debe iniciar sesión primero')
        from django.shortcuts import redirect
        return redirect('login')
    try:
        from .models import User_admin
        user = User_admin.objects.get(id=user_id)
    except User_admin.DoesNotExist:
        from django.contrib import messages
        messages.error(request, 'Usuario no encontrado')
        from django.shortcuts import redirect
        return redirect('login')
    # Validar permiso de acceso a usuarios
    if not user.permiso_usuarios:
        from django.contrib import messages
        messages.error(request, 'No tiene permiso para acceder a la gestión de usuarios.')
        from django.shortcuts import redirect
        return redirect('login')
    ctrl = ControlUsuarios()
    error = None
    message = None
    # Restringir acciones CRUD si solo_consulta está activo
    if request.method == 'POST':
        if user.solo_consulta:
            from django.contrib import messages
            messages.error(request, 'No tiene permisos para crear, editar o eliminar usuarios. Solo puede consultar.')
            from django.shortcuts import redirect
            return redirect('control_usuarios')
        # Crear usuario
        if 'crear_usuario' in request.POST:
            nombre = request.POST.get('nombre', '').strip()
            password = request.POST.get('password', '').strip()
            email = request.POST.get('email', '').strip()
            telefono = request.POST.get('telefono', '').strip()
            solo_consulta = bool(request.POST.get('solo_consulta'))
            bloqueado = bool(request.POST.get('bloqueado'))
            # Permisos
            permiso_control = request.POST.get('permiso_control') == '1'
            permiso_control_personas = request.POST.get('permiso_control_personas') == '1'
            permiso_reportes = request.POST.get('permiso_reportes') == '1'
            permiso_auditoria = request.POST.get('permiso_auditoria') == '1'
            permiso_usuarios = request.POST.get('permiso_usuarios') == '1'
            if not nombre or not password:
                error = 'Nombre y contraseña son obligatorios.'
            else:
                try:
                    ctrl.crear_usuario(
                        nombre, password, email, telefono, solo_consulta, bloqueado,
                        permiso_control=permiso_control,
                        permiso_control_personas=permiso_control_personas,
                        permiso_reportes=permiso_reportes,
                        permiso_auditoria=permiso_auditoria,
                        permiso_usuarios=permiso_usuarios
                    )
                    message = 'Usuario creado correctamente.'
                except Exception as e:
                    error = f'Error al crear usuario: {str(e)}'
        # Editar usuario
        if 'editar_usuario' in request.POST:
            usuario_id = request.POST.get('usuario_id')
            nombre = request.POST.get('nombre', '').strip()
            password = request.POST.get('password', '').strip()
            email = request.POST.get('email', '').strip()
            telefono = request.POST.get('telefono', '').strip()
            solo_consulta = bool(request.POST.get('solo_consulta'))
            bloqueado = bool(request.POST.get('bloqueado'))
            permiso_control = request.POST.get('permiso_control') == '1'
            permiso_control_personas = request.POST.get('permiso_control_personas') == '1'
            permiso_reportes = request.POST.get('permiso_reportes') == '1'
            permiso_auditoria = request.POST.get('permiso_auditoria') == '1'
            permiso_usuarios = request.POST.get('permiso_usuarios') == '1'
            if not usuario_id:
                error = 'ID de usuario requerido.'
            else:
                try:
                    update_data = {
                        'nombre': nombre,
                        'email': email,
                        'telefono': telefono,
                        'solo_consulta': solo_consulta,
                        'bloqueado': bloqueado,
                        'permiso_control': permiso_control,
                        'permiso_control_personas': permiso_control_personas,
                        'permiso_reportes': permiso_reportes,
                        'permiso_auditoria': permiso_auditoria,
                        'permiso_usuarios': permiso_usuarios,
                    }
                    if password:
                        update_data['password'] = password
                    ctrl.actualizar_usuario(usuario_id, **update_data)
                    message = 'Usuario actualizado correctamente.'
                except Exception as e:
                    error = f'Error al actualizar usuario: {str(e)}'
        # Eliminar usuario
        if 'eliminar_usuario' in request.POST:
            usuario_id = request.POST.get('usuario_id')
            if not usuario_id:
                error = 'ID de usuario requerido.'
            else:
                try:
                    ctrl.eliminar_usuario(usuario_id)
                    message = 'Usuario eliminado correctamente.'
                except Exception as e:
                    error = f'Error al eliminar usuario: {str(e)}'

    # PAGINACIÓN
    usuarios_qs = ctrl.listar_usuarios()
    page = request.GET.get('page', 1)
    from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
    paginator = Paginator(usuarios_qs, 10)
    try:
        usuarios = paginator.page(page)
    except PageNotAnInteger:
        usuarios = paginator.page(1)
    except EmptyPage:
        usuarios = paginator.page(paginator.num_pages)

    return render(request, 'control_usuarios.html', {
        'usuarios': usuarios,
        'error': error,
        'message': message,
        'user_admin': user,
        'paginator': paginator,
        'page_obj': usuarios,
    })
from weasyprint import HTML
from django.template.loader import render_to_string
def reporte_pdf_materia_prima(request):
    """Genera PDF de entradas de materia prima según filtros de fecha."""
    user_id = request.session.get('user_admin_id')
    if not user_id:
        messages.error(request, 'Debe iniciar sesión primero')
        return redirect('login')
    try:
        user = User_admin.objects.get(id=user_id)
    except User_admin.DoesNotExist:
        messages.error(request, 'Usuario no encontrado')
        return redirect('login')
    # Validar permiso de acceso a reportes (o control_personas si aplica)
    if not user.permiso_reportes:
        messages.error(request, 'No tiene permiso para acceder a la vista de reportes.')
        return redirect('control')
    # Solo_consulta: permitir acceso a la vista y buscador, solo bloquear POST
    if request.method == 'POST' and user.solo_consulta:
        messages.error(request, 'No tiene permisos para registrar o modificar accesos de personas. Solo puede consultar.')
        return redirect('control_personas')
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    qs = Historial.objects.all().order_by('-fecha_hora')
    if fecha_inicio:
        try:
            fecha_inicio_dt = timezone.datetime.strptime(fecha_inicio, "%Y-%m-%d")
            qs = qs.filter(fecha_hora__gte=fecha_inicio_dt)
        except Exception:
            pass
    if fecha_fin:
        try:
            fecha_fin_dt = timezone.datetime.strptime(fecha_fin, "%Y-%m-%d") + timezone.timedelta(days=1)
            qs = qs.filter(fecha_hora__lt=fecha_fin_dt)
        except Exception:
            pass
    entradas = qs[:200]
    html_string = render_to_string('pdf_materia_prima.html', {
        'entradas': entradas,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    })
    pdf_file = HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_materia_prima.pdf"'
    return response

def reporte_pdf_personal(request):
    """Genera PDF de entradas/salidas de personal según filtros de fecha."""
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    qs = AccesoPersona.objects.all().order_by('-hora_entrada')
    if fecha_inicio:
        try:
            fecha_inicio_dt = timezone.datetime.strptime(fecha_inicio, "%Y-%m-%d")
            qs = qs.filter(hora_entrada__gte=fecha_inicio_dt)
        except Exception:
            pass
    if fecha_fin:
        try:
            fecha_fin_dt = timezone.datetime.strptime(fecha_fin, "%Y-%m-%d") + timezone.timedelta(days=1)
            qs = qs.filter(hora_entrada__lt=fecha_fin_dt)
        except Exception:
            pass
    entradas = qs[:200]
    html_string = render_to_string('pdf_personal.html', {
        'entradas': entradas,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    })
    pdf_file = HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_personal.pdf"'
    return response


from django.views.decorators.http import require_GET
from django.utils import timezone

def reportes(request):
    """
    Vista para mostrar y descargar reportes de entrada de materia prima (control) y de personal (control_personas).
    Permite filtrar por fechas y descargar PDF de ambos tipos de reportes.
    """
    user_id = request.session.get('user_admin_id')
    if not user_id:
        from django.contrib import messages
        messages.error(request, 'Debe iniciar sesión primero')
        from django.shortcuts import redirect
        return redirect('login')
    try:
        from .models import User_admin
        user = User_admin.objects.get(id=user_id)
    except User_admin.DoesNotExist:
        from django.contrib import messages
        messages.error(request, 'Usuario no encontrado')
        from django.shortcuts import redirect
        return redirect('login')
    # Validar permiso de acceso a reportes
    if not user.permiso_reportes:
        from django.contrib import messages
        messages.error(request, 'No tiene permiso para acceder a la vista de reportes.')
        from django.shortcuts import redirect
        return redirect('login')
    
    tipo = request.GET.get('tipo', 'materia_prima')  # 'materia_prima' o 'personal'
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    entradas = []
    error = None
    if tipo == 'materia_prima':
        # Historial de materia prima (de la vista control)
        qs = Historial.objects.all().order_by('-fecha_hora')
        if fecha_inicio:
            try:
                fecha_inicio_dt = timezone.datetime.strptime(fecha_inicio, "%Y-%m-%d")
                qs = qs.filter(fecha_hora__gte=fecha_inicio_dt)
            except Exception:
                error = 'Fecha de inicio inválida.'
        if fecha_fin:
            try:
                fecha_fin_dt = timezone.datetime.strptime(fecha_fin, "%Y-%m-%d") + timezone.timedelta(days=1)
                qs = qs.filter(fecha_hora__lt=fecha_fin_dt)
            except Exception:
                error = 'Fecha de fin inválida.'
        entradas = qs[:200]
        paginador = None
        pagina_actual = None
    elif tipo == 'personal':
        # Entradas y salidas de personal, paginadas de a 10
        qs = AccesoPersona.objects.all().order_by('-hora_entrada')
        if fecha_inicio:
            try:
                fecha_inicio_dt = timezone.datetime.strptime(fecha_inicio, "%Y-%m-%d")
                qs = qs.filter(hora_entrada__gte=fecha_inicio_dt)
            except Exception:
                error = 'Fecha de inicio inválida.'
        if fecha_fin:
            try:
                fecha_fin_dt = timezone.datetime.strptime(fecha_fin, "%Y-%m-%d") + timezone.timedelta(days=1)
                qs = qs.filter(hora_entrada__lt=fecha_fin_dt)
            except Exception:
                error = 'Fecha de fin inválida.'
        from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
        paginador = Paginator(qs, 10)
        page = request.GET.get('page', 1)
        try:
            entradas = paginador.page(page)
            pagina_actual = entradas.number
        except PageNotAnInteger:
            entradas = paginador.page(1)
            pagina_actual = 1
        except EmptyPage:
            entradas = paginador.page(paginador.num_pages)
            pagina_actual = paginador.num_pages
    else:
        error = 'Tipo de reporte no válido.'
        entradas = []
        paginador = None
        pagina_actual = None

    return render(request, 'reportes.html', {
        'tipo': tipo,
        'entradas': entradas,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'error': error,
        'paginador': paginador,
        'pagina_actual': pagina_actual,
        'user_admin': user,
    })

@require_GET
def autocomplete_persona_empresa(request):
    q = request.GET.get('q', '').strip()
    results = []
    if q:
        empresas = (AccesoPersona.objects.filter(empresa__icontains=q)
                    .values_list('empresa', flat=True).exclude(empresa__isnull=True).exclude(empresa='').distinct()[:10])
        results = list(empresas)
    return JsonResponse(results, safe=False)

@require_GET
def autocomplete_persona_nombre(request):
    q = request.GET.get('q', '').strip()
    results = []
    if q:
        nombres = (AccesoPersona.objects.filter(nombre__icontains=q)
                   .values_list('nombre', flat=True).distinct()[:10])
        results = list(nombres)
    return JsonResponse(results, safe=False)

@require_GET
def autocomplete_persona_apellido(request):
    q = request.GET.get('q', '').strip()
    results = []
    if q:
        apellidos = (AccesoPersona.objects.filter(apellido__icontains=q)
                     .values_list('apellido', flat=True).distinct()[:10])
        results = list(apellidos)
    return JsonResponse(results, safe=False)

@require_GET
def autocomplete_persona_cedula(request):
    q = request.GET.get('q', '').strip()
    results = []
    if q:
        cedulas = (AccesoPersona.objects.filter(cedula__icontains=q)
                   .values_list('cedula', flat=True).distinct()[:10])
        results = list(cedulas)
    return JsonResponse(results, safe=False)

@require_GET
def autocomplete_persona_placa(request):
    q = request.GET.get('q', '').strip()
    results = []
    if q:
        placas = (AccesoPersona.objects.filter(placa_vehiculo__icontains=q)
                  .values_list('placa_vehiculo', flat=True).distinct()[:10])
        results = list(placas)
    return JsonResponse(results, safe=False)
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from .models import User_admin, Historial, AccesoPersona
from django.http import JsonResponse
from django.db import connections
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import datetime
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.cache import never_cache
from .crud import ControlDeMateriaPrima

# Instancia reutilizable para operaciones DB
ctrl = ControlDeMateriaPrima()



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

@never_cache
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
    # Validar permiso de acceso a control
    if not user.permiso_control:
        messages.error(request, 'No tiene permiso para acceder a la vista de control.')
        return redirect('login')

    # --- Nueva lógica tipo index de app1 ---
    message = None
    error = None

    # Consultar empresas y conductores
    empresas = ctrl.fetch_empresas()

    # Restringir acciones CRUD si solo_consulta está activo
    if user.solo_consulta and request.method == 'POST' and request.POST.get('validar_fact_num'):
        messages.error(request, 'No tiene permisos para registrar ingresos. Solo puede consultar y descargar el historial.')
        return redirect('control')

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
        reng_num = request.POST.get('reng_num')
        co_art = request.POST.get('co_art')

        # --- Obtener datos del producto/renglón seleccionado ---
        producto_nombre = 'Producto genérico'
        cantidad = 1
        reng_info = ctrl.get_reng_info(fact_num, reng_num, co_art)
        if reng_info:
            producto_nombre = reng_info.get('art_des') or producto_nombre
            cantidad = reng_info.get('total_art') or cantidad

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
            dt = datetime.now(venezuela_tz)
            historial_qs = Historial.objects.all().order_by('-fecha_hora')
            buscar_historial = request.GET.get('buscar_historial', '').strip()
            if buscar_historial:
                from django.db.models import Q
                historial_qs = historial_qs.filter(
                    Q(numero_orden__icontains=buscar_historial) |
                    Q(placa_vehiculo__icontains=buscar_historial) |
                    Q(descripcion__icontains=buscar_historial)
                )

        # --- NUEVO: obtener fecha/hora actual e IP para el registro de transporte ---
        fecha_ingreso = datetime.now(venezuela_tz).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        ip_ingreso = request.META.get('REMOTE_ADDR', '')

        # --- Obtener datos completos de cada entidad desde ceres_romana ---
        empresa_id, empresa_nombre = ctrl.get_empresa_by_rif(empresa_rif)
        vehiculo_id, vehiculo_nombre = ctrl.get_vehiculo_by_placa(vehiculo_placa)
        vehiculo_remolque_id, vehiculo_remolque_nombre = ctrl.get_vehiculo_remolque_by_placa(vehiculo_remolque_placa)
        conductor_id, conductor_nombre, conductor_apellido = ctrl.get_conductor_by_cedula(conductor_cedula)
        destino_id = ctrl.get_destino_id_by_name(destino_nombre)

        # --- DATOS DE PRODUCTO: obtener campo8 y producto_id (desde reng_info o fallback POST) ---
        producto_codigo = None
        producto_id = None
        peso = 0
        campo8 = reng_info.get('campo8') if reng_info else None
        producto_codigo = campo8
        producto_id_db = None
        if campo8:
            producto_id_db = ctrl.lookup_producto_id_by_codigo(campo8)
        if not producto_id_db:
            producto_id_db = request.POST.get('producto_id')
        producto_id = producto_id_db

        # --- Validar que producto_id y producto_codigo existan antes de continuar ---
        if not producto_id or not producto_codigo or not reng_num or not co_art:
            error = "No se encontró el ID de producto, el código de producto (campo 8) o el renglón seleccionado. Debe seleccionar el producto específico de la orden para registrar."
            return render(request, 'control.html', {
                'registros': [],
                'fact_num': '',
                'message': message,
                'error': error,
                'empresas': empresas,
            })
        # Solo se registra el producto/renglón seleccionado

        # --- Obtener Orden_Id desde la tabla orden_profit ---
        orden_id = ctrl.get_orden_id(fact_num)

        # --- Inserción en Orden_Profit_Transporte_Insert ---
        try:
            # Preparar parámetros del producto para la inserción
            producto_codigo_final = producto_codigo
            producto_id_final = producto_id
            orden_id_param = orden_id if orden_id is not None else 0
            ctrl.insert_orden_transporte(
                orden_id_param,
                fact_num,
                producto_id_final,
                producto_codigo_final,
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
            )
            messages.success(request, f"¡Registro exitoso! La orden {fact_num} fue registrada correctamente en Romana.")
        except Exception as e:
            error = f"Error al validar la orden (Orden_Profit_Transporte_Insert): {str(e)}"
            return render(request, 'control.html', {
                'registros': [],
                'fact_num': '',
                'message': message,
                'error': error,
                'empresas': empresas,
            })

        # --- Guardar en historial si hay placa y número de orden ---
        try:
            pendiente_hist = None
            producto_nombre_real = producto_nombre
            try:
                with connections['sqlserver'].cursor() as cursor:
                    if reng_num and co_art:
                        cursor.execute(
                            "SELECT a.art_des, r.pendiente FROM reng_ord r LEFT JOIN art a ON a.co_art = r.co_art WHERE r.fact_num = %s AND r.reng_num = %s AND r.co_art = %s",
                            [fact_num, reng_num, co_art]
                        )
                    else:
                        cursor.execute(
                            "SELECT TOP 1 a.art_des, r.pendiente FROM reng_ord r LEFT JOIN art a ON a.co_art = r.co_art WHERE r.fact_num = %s",
                            [fact_num]
                        )
                    row = cursor.fetchone()
                    if row:
                        producto_nombre_real = row[0] or producto_nombre
                        pendiente_hist = row[1]
            except Exception:
                pass
            # Asegúrate de obtener la placa correctamente del POST
            vehiculo_placa_hist = request.POST.get('vehiculo', '').strip()
            if vehiculo_placa_hist and fact_num:
                existe = Historial.objects.filter(
                    placa_vehiculo=vehiculo_placa_hist,
                    numero_orden=fact_num,
                    descripcion=producto_nombre_real
                ).order_by('-fecha_hora').first()
                # Solo guarda si no existe uno igual con el mismo pendiente
                pendiente_hist_val = pendiente_hist
                if pendiente_hist_val is not None:
                    try:
                        pendiente_hist_val = float(pendiente_hist_val)
                    except Exception:
                        pendiente_hist_val = pendiente_hist
                if not existe or (existe and existe.pendiente != pendiente_hist_val):
                    Historial.objects.create(
                        placa_vehiculo=vehiculo_placa_hist,
                        numero_orden=fact_num,
                        descripcion=producto_nombre_real,
                        pendiente=pendiente_hist
                    )
        except Exception as e:
            error = f"Error al guardar en historial: {str(e)}"

        # --- REDIRECT después de procesar el formulario para evitar reenvío al recargar ---
        # Puedes pasar fact_num como parámetro GET si quieres mostrar el resultado de la orden recién registrada
        fact_num = request.POST.get('validar_fact_num', '')
        # Puedes agregar más parámetros si lo necesitas
        return HttpResponseRedirect(f"{reverse('control')}?fact_num={fact_num}")

    # --- Historial de ingresos con paginación y filtros (esto debe ir antes de la consulta de órdenes) ---
    page = request.GET.get('page', 1)
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')

    historial_qs = Historial.objects.all().order_by('-fecha_hora')
    if fecha_inicio:
        try:
            fecha_inicio_dt = datetime.datetime.strptime(fecha_inicio, "%Y-%m-%d")
            historial_qs = historial_qs.filter(fecha_hora__gte=fecha_inicio_dt)
        except Exception:
            pass
    if fecha_fin:
        try:
            fecha_fin_dt = datetime.datetime.strptime(fecha_fin, "%Y-%m-%d") + datetime.timedelta(days=1)
            historial_qs = historial_qs.filter(fecha_hora__lt=fecha_fin_dt)
        except Exception:
            pass

    paginator = Paginator(historial_qs, 10)
    try:
        historial = paginator.page(page)
    except PageNotAnInteger:
        historial = paginator.page(1)
    except EmptyPage:
        historial = paginator.page(paginator.num_pages)

    # Consulta de órdenes (GET)
    raw = request.GET.get('fact_num', '').strip()
    if 'fact_num' not in request.GET:
        # Siempre renderiza el historial aunque no haya búsqueda de orden
        return render(request, 'control.html', {
            'registros': [],
            'fact_num': '',
            'message': message,
            'error': error,
            'empresas': empresas,
            'status_cond': request.GET.get('status_cond', ''),
            'historial': historial,
            'historial_paginator': paginator,
            'historial_page': historial.number,
            'historial_has_previous': historial.has_previous(),
            'historial_has_next': historial.has_next(),
            'historial_previous_page_number': historial.previous_page_number() if historial.has_previous() else None,
            'historial_next_page_number': historial.next_page_number() if historial.has_next() else None,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'user_admin': user,
        })

    vals = [v.strip() for v in raw.split(',') if v.strip()]
    if not vals:
        error = "Ingrese un fact_num válido."
        return render(request, 'control.html', {'registros': [], 'fact_num': raw, 'message': message, 'error': error, 'user_admin': user})

    if len(vals) > 1:
        error = "Solo puedes consultar o registrar una orden de compra a la vez."
        return render(request, 'control.html', {'registros': [], 'fact_num': raw, 'message': message, 'error': error, 'user_admin': user})

    if len(vals) == 1:
        sql = """
        select h.fact_num, h.fec_emis, h.status, h.co_cli, p.prov_des, h.descrip, h.comentario as hcoment,
               r.comentario as rcoment, r.reng_num, r.co_art, a.art_des, l.lin_des, r.total_art, r.uni_venta, r.pendiente,
               a.campo8
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
               r.comentario as rcoment, r.reng_num, r.co_art, a.art_des, l.lin_des, r.total_art, r.uni_venta, r.pendiente,
               a.campo8, p.Producto_Codigo, p.Producto_Nombre, p.Producto_Descripcion
        from reng_ord r
        left join ordenes h on h.fact_num=r.fact_num
        left join prov p on p.co_prov=h.co_cli
        left join art a on a.co_art=r.co_art
        left join lin_art l on l.co_lin=a.co_lin
        where h.fact_num IN ({placeholders})
        """
        params = vals
        message = f"Mostrando resultados para {len(vals)} fact_num(s)."

    registros, err = ctrl.get_registros(vals)
    error = err
    # Formatear los campos numéricos en los registros obtenidos
    for reg in registros:
        for campo in ['total_art', 'uni_venta', 'pendiente']:
            reg[campo] = format_number_backend(reg.get(campo))

    status_cond = request.GET.get('status_cond', '')

    return render(request, 'control.html', {
        'registros': registros,
        'fact_num': raw,
        'message': message,
        'error': error,
        'empresas': empresas,
        'status_cond': status_cond,
        'historial': historial,
        'historial_paginator': paginator,
        'historial_page': historial.number,
        'historial_has_previous': historial.has_previous(),
        'historial_has_next': historial.has_next(),
        'historial_previous_page_number': historial.previous_page_number() if historial.has_previous() else None,
        'historial_next_page_number': historial.next_page_number() if historial.has_next() else None,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'user_admin': user,
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


@never_cache
def control_personas(request):
    """Vista para control de acceso de personas: muestra formulario y lista de accesos recientes.
    POST crea una entrada `AccesoPersona` con hora_entrada automática.
    """
    user_id = request.session.get('user_admin_id')
    if not user_id:
        from django.contrib import messages
        messages.error(request, 'Debe iniciar sesión primero')
        from django.shortcuts import redirect
        return redirect('login')
    try:
        from .models import User_admin
        user = User_admin.objects.get(id=user_id)
    except User_admin.DoesNotExist:
        from django.contrib import messages
        messages.error(request, 'Usuario no encontrado')
        from django.shortcuts import redirect
        return redirect('login')
    from django.contrib import messages
    from django.shortcuts import redirect
    # Validar permiso de acceso a control_personas
    if not user.permiso_control_personas:
        messages.error(request, 'No tiene permiso para acceder a la vista de control de personas.')
        return redirect('login')
    # No redirigir aquí si el usuario es solo_consulta — permitir GET/consulta.
    read_only = user.solo_consulta
    from .crud import ControlDeMateriaPrima
    ctrl = ControlDeMateriaPrima()
    if request.method == 'POST':
        # Bloquear operaciones de escritura si está en modo solo consulta
        if read_only:
            messages.error(request, 'No tiene permisos para registrar o modificar accesos de personas. Solo puede consultar.')
            return redirect('control_personas')
        # Solo permite registrar entradas/salidas si tiene permiso booleano
        if not user.permiso_control_personas:
            from django.contrib import messages
            messages.error(request, 'No tiene permisos para registrar o modificar accesos de personas. Solo puede consultar.')
            from django.shortcuts import redirect
            return redirect('control_personas')
        salida_id = request.POST.get('salida_id')
        if salida_id:
            try:
                updated = ctrl.registrar_salida_persona(salida_id)
                if updated:
                    messages.success(request, 'Salida registrada correctamente.')
                else:
                    messages.warning(request, 'La salida ya estaba registrada o el registro no existe.')
            except Exception as e:
                messages.error(request, f'Error al registrar salida: {str(e)}')
            return redirect('control_personas')

        nombre = request.POST.get('nombre', '').strip()
        apellido = request.POST.get('apellido', '').strip()
        cedula = request.POST.get('cedula', '').strip()
        empresa = request.POST.get('empresa', '').strip()
        motivo_ingreso = request.POST.get('motivo_ingreso', '').strip()
        placa = request.POST.get('placa', '').strip()

        if not nombre or not cedula or not motivo_ingreso:
            messages.error(request, 'Nombre, cédula y motivo de ingreso son obligatorios.')
            return redirect('control_personas')

        try:
            ctrl.crear_acceso_persona(
                nombre=nombre,
                apellido=apellido,
                cedula=cedula,
                empresa=empresa,
                motivo_ingreso=motivo_ingreso,
                placa_vehiculo=placa if placa else None
            )
            messages.success(request, 'Entrada registrada correctamente.')
        except Exception as e:
            messages.error(request, f'Error al guardar entrada: {str(e)}')
        return redirect('control_personas')


    # Buscador: filtrar historial paginado
    buscar = request.GET.get('buscar', '').strip()
    from django.db.models import Q
    if buscar:
        historial_qs = AccesoPersona.objects.filter(
            Q(nombre__icontains=buscar) |
            Q(apellido__icontains=buscar) |
            Q(cedula__icontains=buscar) |
            Q(placa_vehiculo__icontains=buscar)
        ).order_by('-hora_entrada')
    else:
        historial_qs = AccesoPersona.objects.all().order_by('-hora_entrada')
    from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
    historial_paginator = Paginator(historial_qs, 10)
    historial_page = request.GET.get('historial_page', 1)
    try:
        historial = historial_paginator.page(historial_page)
        historial_page_num = historial.number
    except PageNotAnInteger:
        historial = historial_paginator.page(1)
        historial_page_num = 1
    except EmptyPage:
        historial = historial_paginator.page(historial_paginator.num_pages)
        historial_page_num = historial_paginator.num_pages

    return render(request, 'control_personas.html', {
        'request': request,
        'historial': historial,
        'historial_paginator': historial_paginator,
        'historial_page': historial_page_num,
        'historial_has_previous': historial.has_previous(),
        'historial_has_next': historial.has_next(),
        'historial_previous_page_number': historial.previous_page_number() if historial.has_previous() else None,
        'historial_next_page_number': historial.next_page_number() if historial.has_next() else None,
        'user_admin': user,
    })

