from django.db import connections

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
                    registros.append(dict(zip(cols, row)))
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
        if not kwargs:
            return 0
        set_clause = ', '.join([f"{k} = %s" for k in kwargs.keys()])
        values = list(kwargs.values())
        values.append(registro_id)
        try:
            with connections['ceres_romana'].cursor() as cursor:
                cursor.execute(f"UPDATE orden_profit_transporte SET {set_clause} WHERE transporte_id = %s", values)
                return cursor.rowcount
        except Exception:
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
    def crear_acceso_persona(self, nombre, apellido, cedula, motivo_ingreso, placa_vehiculo=None, empresa=None):
        return AccesoPersona.objects.create(
            nombre=nombre,
            apellido=apellido,
            cedula=cedula,
            empresa=empresa,
            motivo_ingreso=motivo_ingreso,
            placa_vehiculo=placa_vehiculo
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
        """Realiza la consulta principal para obtener registros y les añade campos auxiliares.
        Retorna (registros, error)
        """
        registros = []
        error = None
        try:
            # Obtener orden_id para los fact_num
            orden_id_map = {}
            if vals:
                with connections['ceres_romana'].cursor() as cursor:
                    cursor.execute(
                        f"SELECT orden, orden_id FROM orden_profit WHERE orden IN ({','.join(['%s']*len(vals))})",
                        vals
                    )
                    for row in cursor.fetchall():
                        orden_id_map[str(row[0])] = row[1]

            # Consulta a sqlserver
            placeholders = ','.join(['%s'] * len(vals))
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
            else:
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
                """.replace('{placeholders}', placeholders)
                params = vals

            with connections['sqlserver'].cursor() as cursor:
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
                    # Formateo numérico opcional -- dejarlo sin formato aquí para mantener consistencia con la vista
                    reg['orden_id'] = orden_id_map.get(str(reg.get('fact_num')))
                    placa = reg.get('vehiculo_placa') or ''
                    descripcion = reg.get('art_des') or reg.get('descrip') or ''
                    key = (reg.get('fact_num'), placa, descripcion)
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
                    reg['vehiculo_placa'] = placa
                    reg['descripcion'] = descripcion
                    reg['reng_num'] = reg.get('reng_num')
                    reg['co_art'] = reg.get('co_art')
                    reg['campo8'] = reg.get('campo8', '')

                    producto_id = None
                    campo8 = reg.get('campo8', '').strip() if reg.get('campo8') else ''
                    if campo8:
                        try:
                            with connections['ceres_romana'].cursor() as cursor:
                                cursor.execute("SELECT Producto_Id FROM PRODUCTO WHERE RTRIM(Producto_Codigo) = %s", [campo8])
                                prod_row = cursor.fetchone()
                                if prod_row:
                                    producto_id = prod_row[0]
                        except Exception:
                            producto_id = None
                    reg['producto_id'] = producto_id
                    reg['empresa_rif'] = reg.get('empresa_rif', '')
                    reg['conductor'] = reg.get('conductor', '')
                    reg['vehiculo_remolque_placa'] = reg.get('vehiculo_remolque_placa', '')
                    reg['destino_nombre'] = reg.get('destino_nombre', '')
                    registros.append(reg)
        except Exception as e:
            registros = []
            error = str(e)
        return registros, error