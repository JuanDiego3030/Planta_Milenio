from django.db import models

class Prueba(models.Model):
    nombre = models.CharField(max_length=200)
    fecha = models.DateField()
    socio = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

class OrdenDetalle(models.Model):
    fact_num = models.CharField(max_length=50, null=True, blank=True)
    fec_emis = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    co_cli = models.CharField(max_length=50, null=True, blank=True)
    prov_des = models.CharField(max_length=200, null=True, blank=True)
    descrip = models.TextField(null=True, blank=True)
    hcoment = models.TextField(null=True, blank=True)
    rcoment = models.TextField(null=True, blank=True)
    reng_num = models.IntegerField(null=True, blank=True)
    co_art = models.CharField(max_length=50, null=True, blank=True)
    art_des = models.CharField(max_length=200, null=True, blank=True)
    lin_des = models.CharField(max_length=200, null=True, blank=True)
    total_art = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    uni_venta = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    pendiente = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)

    class Meta:
        managed = False  # no crear/migrar esta tabla desde Django
        db_table = 'reng_ord'