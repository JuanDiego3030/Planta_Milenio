from django.db import models

class User_admin(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=128)
    bloqueado = models.BooleanField(default=False)
    email = models.EmailField(max_length=150, unique=True, null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)

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
