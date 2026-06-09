from django.db import connections
import logging

logger = logging.getLogger(__name__)

# --- CRUD para auditoría de orden_profit_transporte ---
class ControlAuditoria:
    """CRUD para la tabla orden_profit_transporte (auditoría de transportes)."""
    def listar_registros(self, limite=100):
        registros = []
        try:
            with connections['ceres_romana'].cursor() as cursor:
                # TOP no acepta parámetros, debe ser un número literal
                sql = f"SELECT TOP {int(limite)} * FROM orden_profit_transporte ORDER BY orden_id DESC"
                cursor.execute(sql)
                cols = [col[0] for col in cursor.description]
                for row in cursor.fetchall():
                    rec = dict(zip(cols, row))
                    # Normalizar Pesada_Id: convertir '0' o b'0' o '' a integer 0
                    pesada_keys = [k for k in rec.keys() if 'pesada' in k.lower()]
                    pesada_val = None
                    if pesada_keys:
                        pesada_raw = rec.get(pesada_keys[0])
                        try:
                            # manejar bytes
                            if isinstance(pesada_raw, (bytes, bytearray)):
                                pesada_raw = pesada_raw.decode(errors='ignore')
                            if pesada_raw is None:
                                pesada_val = 0
                            elif isinstance(pesada_raw, str) and pesada_raw.strip() == '':
                                pesada_val = 0
                            else:
                                pesada_val = int(pesada_raw)
                        except Exception:
                            # si no se puede convertir, dejar el valor original
                            pesada_val = pesada_raw
                    else:
                        pesada_val = 0
                    rec['Pesada_Id'] = pesada_val
                    # Asegurar que exista Orden_Transporte_Id (variantes de nombre)
                    transporte_keys = [k for k in rec.keys() if 'transporte' in k.lower() or 'transporte_id' in k.lower() or 'transporteid' in k.lower()]
                    if transporte_keys:
                        rec['Orden_Transporte_Id'] = rec.get(transporte_keys[0])
                    elif 'transporte_id' in rec:
                        rec['Orden_Transporte_Id'] = rec.get('transporte_id')
                    # Añadir registro normalizado
                    registros.append(rec)
        except Exception as e:
            print(f"Error en listar_registros: {e}")
        return registros

    def obtener_registro(self, registro_id):
        try:
            with connections['ceres_romana'].cursor() as cursor:
                cursor.execute("SELECT * FROM orden_profit_transporte WHERE transporte_id = %s", [registro_id])
                cols = [col[0] for col in cursor.description]
                row = cursor.fetchone()
                if row:
                    return dict(zip(cols, row))
        except Exception:
            pass
        return None

    def actualizar_registro(self, registro_id, **kwargs):
        """Actualizar registro usando el stored procedure Orden_Profit_Transporte_Update.

        Se intenta construir los parámetros mínimos necesarios a partir del registro
        actual y de los `kwargs` provistos. Devuelve el valor de salida `@exito`
        devuelto por el SP (int) o 0 en caso de error.
        """
        try:
            registro_actual = self.obtener_registro(registro_id) or {}
            if not registro_actual:
                logger.debug("registro no encontrado para id=%s", registro_id)
                return 0

            # No permitir edición si el registro ya tiene Pesada_Id
            pesada_val = registro_actual.get('Pesada_Id')
            if pesada_val is not None and pesada_val != 0:
                return 0

            # Valores base tomando preferencia por kwargs sobre el registro actual
            orden_id = kwargs.get('Orden_Id') or registro_actual.get('Orden_Id')
            orden = kwargs.get('Orden') or registro_actual.get('Orden') or ''

            producto_codigo = kwargs.get('Producto_Codigo') or registro_actual.get('Producto_Codigo') or ''
            producto_id = kwargs.get('Producto_Id')
            # Si no se proporcionó Producto_Id, intentar buscar por código
            if not producto_id and producto_codigo:
                producto_id = ControlDeMateriaPrima().lookup_producto_id_by_codigo(producto_codigo)

            pesada_id = kwargs.get('Pesada_Id') if 'Pesada_Id' in kwargs else registro_actual.get('Pesada_Id')

            empresa_rif = kwargs.get('Empresa_Rif') or registro_actual.get('Empresa_Rif') or ''
            empresa_nombre = kwargs.get('Empresa_Nombre') or registro_actual.get('Empresa_Nombre') or ''
            empresa_id = kwargs.get('Empresa_Id') or registro_actual.get('Empresa_Id') or 0

            vehiculo_placa = kwargs.get('Vehiculo_Placa') or registro_actual.get('Vehiculo_Placa') or ''
            vehiculo_id = kwargs.get('Vehiculo_id')
            if not vehiculo_id and vehiculo_placa:
                vehiculo_id, _ = ControlDeMateriaPrima().get_vehiculo_by_placa(vehiculo_placa)

            veh_rem_placa = kwargs.get('Vehiculo_Remolque_Placa') or registro_actual.get('Vehiculo_Remolque_Placa') or None
            veh_rem_id = kwargs.get('Vehiculo_Remolque_id')
            if not veh_rem_id and veh_rem_placa:
                veh_rem_id, _ = ControlDeMateriaPrima().get_vehiculo_remolque_by_placa(veh_rem_placa)

            conductor_cedula = kwargs.get('Conductor_Cedula') or registro_actual.get('Conductor_Cedula') or ''
            conductor_id = kwargs.get('Conductor_Id')
            conductor_nombre = kwargs.get('Conductor_Nombre') or registro_actual.get('Conductor_Nombre') or ''
            conductor_apellido = kwargs.get('Conductor_Apellido') or registro_actual.get('Conductor_Apellido') or ''
            if not conductor_id and conductor_cedula:
                conductor_id, conductor_nombre, conductor_apellido = ControlDeMateriaPrima().get_conductor_by_cedula(conductor_cedula)

            destino_nombre = kwargs.get('Destino_Nombre') or registro_actual.get('Destino_Nombre') or ''
            destino_id = kwargs.get('Destino_Id') or registro_actual.get('Destino_Id') or 0
            if not destino_id and destino_nombre:
                destino_id = ControlDeMateriaPrima().get_destino_id_by_name(destino_nombre)

            # Ejecutar el stored procedure y obtener el valor de salida @exito
            params = [
                orden_id or 0,
                registro_id,
                orden,
                producto_id or 0,
                producto_codigo,
                pesada_id,
                empresa_id or 0,
                empresa_rif,
                empresa_nombre,
                vehiculo_id or 0,
                vehiculo_placa,
                veh_rem_id,
                veh_rem_placa,
                conductor_id or 0,
                conductor_cedula,
                conductor_nombre,
                conductor_apellido,
                destino_id or 0,
                destino_nombre
            ]
            logger.debug("orden_profit_transporte_update params=%s", params)
            with connections['ceres_romana'].cursor() as cursor:
                try:
                    cursor.execute("""
                        DECLARE @exito int;
                        EXEC dbo.Orden_Profit_Transporte_Update @exito OUTPUT,
                            @Orden_Id=%s,
                            @Orden_Transporte_Id=%s,
                            @Orden=%s,
                            @Producto_Id=%s,
                            @Producto_Codigo=%s,
                            @Pesada_Id=%s,
                            @Empresa_Id=%s,
                            @Empresa_Rif=%s,
                            @Empresa_Nombre=%s,
                            @Vehiculo_id=%s,
                            @Vehiculo_Placa=%s,
                            @Vehiculo_Remolque_id=%s,
                            @Vehiculo_Remolque_Placa=%s,
                            @Conductor_Id=%s,
                            @Conductor_Cedula=%s,
                            @Conductor_Nombre=%s,
                            @Conductor_Apellido=%s,
                            @Destino_Id=%s,
                            @Destino_Nombre=%s;
                        SELECT @exito;
                    """, params)
                except Exception:
                    logger.exception("Error ejecutando SP Orden_Profit_Transporte_Update")
                    raise
                row = cursor.fetchone()
                logger.debug("SP Orden_Profit_Transporte_Update returned=%s", row)
                if row:
                    try:
                        return int(row[0]) if row[0] is not None else 0
                    except Exception:
                        logger.exception("Error parseando valor devuelto por SP")
                        return 0
        except Exception:
            return 0
        return 0

    def eliminar_registro(self, registro_id):
        try:
            with connections['ceres_romana'].cursor() as cursor:
                cursor.execute("DELETE FROM orden_profit_transporte WHERE transporte_id = %s", [registro_id])
                return cursor.rowcount
        except Exception:
            return 0
from .models import User_admin
# --- CRUD para usuarios ---
class ControlUsuarios:
    def crear_usuario(self, nombre, password, email=None, telefono=None, solo_consulta=False, bloqueado=False,
                      permiso_control=False, permiso_control_personas=False, permiso_reportes=False, permiso_auditoria=False, permiso_usuarios=False):
        return User_admin.objects.create(
            nombre=nombre,
            password=password,
            email=email,
            telefono=telefono,
            solo_consulta=solo_consulta,
            bloqueado=bloqueado,
            permiso_control=permiso_control,
            permiso_control_personas=permiso_control_personas,
            permiso_reportes=permiso_reportes,
            permiso_auditoria=permiso_auditoria,
            permiso_usuarios=permiso_usuarios
        )

    def listar_usuarios(self):
        return User_admin.objects.all().order_by('nombre')

    def eliminar_usuario(self, usuario_id):
        User_admin.objects.filter(id=usuario_id).delete()

    def actualizar_usuario(self, usuario_id, **kwargs):
        User_admin.objects.filter(id=usuario_id).update(**kwargs)

    def obtener_usuario(self, usuario_id):
        return User_admin.objects.filter(id=usuario_id).first()
from django.db import connections

from .models import Historial, AccesoPersona


class ControlDeMateriaPrima:
    """Encapsula operaciones CRUD y consultas a las bases de datos usadas en la vista `control`.
    Métodos usan las conexiones `sqlserver` y `ceres_romana` (definidas en settings).
    """

    def registrar_salida_persona(self, acceso_id):
        from django.utils import timezone
        return AccesoPersona.objects.filter(id=acceso_id, hora_salida__isnull=True).update(hora_salida=timezone.now())

    # CRUD para AccesoPersona
    def crear_acceso_persona(self, nombre, apellido, cedula, motivo_ingreso, placa_vehiculo=None, empresa=None, autorizado_por=None, estado_visita='aprobada', a_quien_visita=None, tiempo_visita=None, hora_salida=None):
        return AccesoPersona.objects.create(
            nombre=nombre,
            apellido=apellido,
            cedula=cedula,
            empresa=empresa,
            motivo_ingreso=motivo_ingreso,
            placa_vehiculo=placa_vehiculo,
            autorizado_por=autorizado_por,
            estado_visita=estado_visita,
            a_quien_visita=a_quien_visita,
            tiempo_visita=tiempo_visita,
            hora_salida=hora_salida
        )

    def listar_accesos_persona(self, limite=100):
        return AccesoPersona.objects.all().order_by('-hora_entrada')[:limite]

    def eliminar_acceso_persona(self, acceso_id):
        AccesoPersona.objects.filter(id=acceso_id).delete()

    def actualizar_acceso_persona(self, acceso_id, **kwargs):
        AccesoPersona.objects.filter(id=acceso_id).update(**kwargs)

    def fetch_empresas(self):
        empresas = []
        try:
            with connections['sqlserver'].cursor() as cursor:
                cursor.execute("SELECT rif, nombre FROM empresas ORDER BY nombre")
                empresas = [{'id': row[0], 'rif': row[0], 'nombre': row[1]} for row in cursor.fetchall()]
        except Exception:
            empresas = []
        return empresas

    def get_reng_info(self, fact_num, reng_num, co_art):
        """Devuelve diccionario con art_des, total_art, campo8, pendiente (o None si no existe)."""
        try:
            with connections['sqlserver'].cursor() as cursor:
                cursor.execute(
                    "SELECT a.art_des, r.total_art, a.campo8, r.pendiente FROM reng_ord r LEFT JOIN art a ON a.co_art = r.co_art "
                    "WHERE r.fact_num = %s AND r.reng_num = %s AND r.co_art = %s",
                    [fact_num, reng_num, co_art]
                )
                row = cursor.fetchone()
                if row:
                    return {'art_des': row[0], 'total_art': row[1], 'campo8': row[2], 'pendiente': row[3]}
        except Exception:
            pass
        return {'art_des': None, 'total_art': None, 'campo8': None, 'pendiente': None}

    def get_empresa_by_rif(self, empresa_rif):
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
        return empresa_id, empresa_nombre

    def get_vehiculo_by_placa(self, placa):
        vehiculo_id = 0
        vehiculo_nombre = ''
        if not placa:
            return vehiculo_id, vehiculo_nombre
        try:
            with connections['ceres_romana'].cursor() as cursor:
                cursor.execute("SELECT TOP 1 Vehiculo_id, Vehiculo_nombre FROM Vehiculo WHERE Vehiculo_placa = %s", [placa])
                row = cursor.fetchone()
                if row:
                    vehiculo_id, vehiculo_nombre = row
        except Exception:
            pass
        return vehiculo_id, vehiculo_nombre

    def get_vehiculo_remolque_by_placa(self, placa):
        vid = None
        nombre = ''
        if not placa:
            return vid, nombre
        try:
            with connections['ceres_romana'].cursor() as cursor:
                cursor.execute("SELECT TOP 1 Vehiculo_Remolque_id, Vehiculo_Remolque_Nombre FROM Vehiculo_Remolque WHERE Vehiculo_Remolque_Placa = %s", [placa])
                row = cursor.fetchone()
                if row:
                    vid, nombre = row
        except Exception:
            pass
        return vid, nombre

    def get_conductor_by_cedula(self, cedula):
        cid = 0
        nombre = ''
        apellido = ''
        if not cedula:
            return cid, nombre, apellido
        try:
            with connections['ceres_romana'].cursor() as cursor:
                cursor.execute("SELECT TOP 1 Conductor_id, Conductor_Nombre, Conductor_Apelido FROM conductor WHERE Conductor_Cedula = %s", [cedula])
                row = cursor.fetchone()
                if row:
                    cid, nombre, apellido = row
        except Exception:
            pass
        return cid, nombre, apellido

    def get_destino_id_by_name(self, destino_nombre):
        did = 0
        if not destino_nombre:
            return did
        try:
            with connections['ceres_romana'].cursor() as cursor:
                cursor.execute("SELECT TOP 1 Destino_Id FROM Destino WHERE Destino_Nombre = %s", [destino_nombre])
                row = cursor.fetchone()
                if row:
                    did = row[0]
        except Exception:
            pass
        return did

    def lookup_producto_id_by_codigo(self, codigo):
        if not codigo:
            return None
        try:
            with connections['ceres_romana'].cursor() as cursor:
                cursor.execute("SELECT Producto_Id FROM PRODUCTO WHERE RTRIM(Producto_Codigo) = %s", [codigo.strip()])
                row = cursor.fetchone()
                if row:
                    return row[0]
        except Exception:
            pass
        return None

    def get_orden_id(self, fact_num):
        orden_id = None
        try:
            with connections['ceres_romana'].cursor() as cursor:
                cursor.execute("SELECT TOP 1 orden_id FROM orden_profit WHERE orden = %s ORDER BY orden_id DESC", [fact_num])
                row = cursor.fetchone()
                if row:
                    orden_id = row[0]
        except Exception:
            orden_id = None
        return orden_id

    def insert_orden_transporte(self, orden_id_param, fact_num, producto_id_final, producto_codigo_final,
                                 empresa_id, empresa_rif, empresa_nombre, vehiculo_id, vehiculo_placa,
                                 vehiculo_remolque_id, vehiculo_remolque_placa, conductor_id, conductor_cedula,
                                 conductor_nombre, conductor_apellido, destino_id, destino_nombre):
        with connections['ceres_romana'].cursor() as cursor:
            cursor.execute("""
                EXEC [dbo].[Orden_Profit_Transporte_Insert] %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            """, [
                orden_id_param,
                fact_num,
                producto_id_final,
                producto_codigo_final,
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

    def get_registros(self, vals):
        """Obtiene registros de órdenes desde la tabla orden_profit de ceres_romana."""
        registros = []
        error = None
        try:
            # Consulta a ceres_romana.orden_profit
            placeholders = ','.join(['%s'] * len(vals))
            sql = f"""
                SELECT Orden_Id, Orden, Status, Proveedor_Id, Proveedor_Rif, Proveedor_Nombre,
                       Producto_Id, Producto_Codigo, Producto_Nombre, Cantidad, Peso, Fecha_Orden, Fecha, Importacion
                FROM orden_profit
                WHERE Orden IN ({placeholders})
                ORDER BY Orden_Id DESC
            """
            params = vals
            with connections['ceres_romana'].cursor() as cursor:
                cursor.execute(sql, params)
                cols = [c[0] for c in cursor.description] if cursor.description else []
                rows = cursor.fetchall()

            # Pre-cargar historial
            historial_objs = Historial.objects.all()
            historial_map = {}
            for h in historial_objs:
                key = (h.numero_orden, h.placa_vehiculo, h.descripcion)
                if key not in historial_map or h.fecha_hora > historial_map[key].fecha_hora:
                    historial_map[key] = h

            for row in rows:
                reg = dict(zip(cols, row))
                # Formateo y mapeo de campos para compatibilidad con la vista/template
                reg['fact_num'] = reg.get('Orden')
                reg['fec_emis'] = reg.get('Fecha_Orden')
                reg['status'] = reg.get('Status')
                reg['co_cli'] = reg.get('Proveedor_Id')
                reg['prov_des'] = reg.get('Proveedor_Nombre')
                reg['descrip'] = reg.get('Producto_Nombre')
                reg['total_art'] = reg.get('Cantidad')
                reg['uni_venta'] = reg.get('Peso')
                reg['pendiente'] = reg.get('Cantidad')  # O ajustar según lógica de pendiente
                reg['co_art'] = reg.get('Producto_Codigo')
                reg['art_des'] = reg.get('Producto_Nombre')
                reg['producto_id'] = reg.get('Producto_Id')
                reg['empresa_rif'] = reg.get('Proveedor_Rif')
                reg['vehiculo_placa'] = ''
                reg['descripcion'] = reg.get('Producto_Nombre')
                reg['reng_num'] = 1  # No hay renglones, poner 1 por defecto
                reg['campo8'] = reg.get('Producto_Codigo')
                # Historial y registro de ingreso
                key = (reg['fact_num'], reg['vehiculo_placa'], reg['descripcion'])
                hist = historial_map.get(key)
                pendiente_actual = None
                try:
                    pendiente_actual = float(reg.get('pendiente')) if reg.get('pendiente') is not None else None
                except Exception:
                    pendiente_actual = None
                ingreso_registrado = False
                if hist:
                    if (hist.pendiente is not None and pendiente_actual is not None and float(hist.pendiente) == float(pendiente_actual)):
                        ingreso_registrado = True
                reg['ingreso_registrado'] = ingreso_registrado
                registros.append(reg)
        except Exception as e:
            registros = []
            error = str(e)
        return registros, error