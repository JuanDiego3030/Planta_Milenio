from django.db import models

class User_admin(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=128)
    bloqueado = models.BooleanField(default=False)
    email = models.EmailField(max_length=150, unique=True, null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    solo_consulta = models.BooleanField(default=False, help_text="Si está activo, el usuario solo puede consultar y descargar el historial, no registrar ingresos.")

    # Permisos por vista (ahora booleanos)
    permiso_control = models.BooleanField(default=False, help_text="Acceso a Control de entradas")
    permiso_control_personas = models.BooleanField(default=False, help_text="Acceso a Control de personas")
    permiso_reportes = models.BooleanField(default=False, help_text="Acceso a Reportes")
    permiso_auditoria = models.BooleanField(default=False, help_text="Acceso a Auditoría")
    permiso_usuarios = models.BooleanField(default=False, help_text="Acceso a Usuarios")

    def __str__(self):
        return self.nombre

class Historial(models.Model):
    placa_vehiculo = models.CharField(max_length=20)
    numero_orden = models.CharField(max_length=20)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    descripcion = models.TextField(blank=True, null=True)  # Nuevo campo para descripción
    pendiente = models.FloatField(null=True, blank=True)   # Nuevo campo para cantidad pendiente

    def __str__(self):
        return f"{self.numero_orden} - {self.placa_vehiculo} - {self.fecha_hora}"



class AccesoPersona(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100, blank=True)
    cedula = models.CharField(max_length=50)
    empresa = models.CharField(max_length=255, blank=True, null=True)  # Nuevo campo empresa
    motivo_ingreso = models.CharField(max_length=255, blank=True, null=True)  # Nuevo campo
    hora_entrada = models.DateTimeField(auto_now_add=True)
    hora_salida = models.DateTimeField(null=True, blank=True)  # Nuevo campo para salida
    placa_vehiculo = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        verbose_name = 'Acceso Persona'
        verbose_name_plural = 'Accesos Personas'

    def __str__(self):
        return f"{self.nombre} {self.apellido} - {self.cedula} @ {self.hora_entrada}"
