from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Categoria(models.Model):
    nombre = models.CharField(max_length=60, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def __str__(self):
        return self.nombre


class Marca(models.Model):
    nombre = models.CharField(max_length=60, unique=True)
    pais_origen = models.CharField("País de origen", max_length=60, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Marca"
        verbose_name_plural = "Marcas"

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField("Descripción", blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    marca = models.ForeignKey(
        Marca,
        on_delete=models.PROTECT,
        related_name="productos",
    )
    categorias = models.ManyToManyField(
        Categoria,
        related_name="productos",
        blank=True,
    )
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self):
        return f"{self.nombre} ({self.marca})"


class Cliente(models.Model):
    cedula = models.CharField("Cédula", max_length=10, unique=True)
    nombres = models.CharField(max_length=80)
    apellidos = models.CharField(max_length=80)
    email = models.EmailField("Correo", blank=True)
    telefono = models.CharField("Teléfono", max_length=15, blank=True)
    direccion = models.CharField("Dirección", max_length=200, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["apellidos", "nombres"]
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

    def __str__(self):
        return f"{self.apellidos} {self.nombres}"


class Venta(models.Model):
    class TipoPago(models.TextChoices):
        CONTADO = "CONTADO", "Contado"
        TARJETA = "TARJETA", "Tarjeta"
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia"
        CREDITO = "CREDITO", "Crédito"

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name="ventas",
    )
    fecha = models.DateTimeField(default=timezone.now)
    tipo_pago = models.CharField(
        "Tipo de pago",
        max_length=15,
        choices=TipoPago.choices,
        default=TipoPago.CONTADO,
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    iva = models.DecimalField("IVA (15%)", max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="ventas_registradas",
        null=True,
        blank=True,
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-pk"]
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"

    def __str__(self):
        return f"Venta #{self.pk}"

    def recalcular_totales(self):
        subtotal = sum(
            (detalle.subtotal for detalle in self.detalles.all()),
            Decimal("0.00"),
        )
        self.subtotal = subtotal
        self.iva = (subtotal * Decimal("0.15")).quantize(Decimal("0.01"))
        self.total = self.subtotal + self.iva
        self.save(update_fields=["subtotal", "iva", "total", "actualizado_en"])


class DetalleVenta(models.Model):
    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="detalles_venta",
    )
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField("Precio", max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["pk"]
        verbose_name = "Detalle de venta"
        verbose_name_plural = "Detalles de venta"
        unique_together = ("venta", "producto")

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return f"{self.producto} x {self.cantidad}"


class Proveedor(models.Model):
    nombre = models.CharField(max_length=100)
    ruc = models.CharField("RUC", max_length=13, unique=True)
    email = models.EmailField("Correo", blank=True)
    telefono = models.CharField("Teléfono", max_length=15, blank=True)
    direccion = models.CharField("Dirección", max_length=200, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"

    def __str__(self):
        return self.nombre


class Compra(models.Model):
    class Estado(models.TextChoices):
        REGISTRADA = "REGISTRADA", "Registrada"
        ANULADA = "ANULADA", "Anulada"

    numero = models.CharField(max_length=30, unique=True)
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name="compras",
    )
    fecha = models.DateField("Fecha", default=timezone.localdate)
    observaciones = models.TextField("Observaciones", blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.CharField(
        max_length=12,
        choices=Estado.choices,
        default=Estado.REGISTRADA,
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="compras",
        null=True,
        blank=True,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-pk"]
        verbose_name = "Compra"
        verbose_name_plural = "Compras"

    def __str__(self):
        return f"Compra {self.numero}"

    def recalcular_total(self):
        total = sum(
            (detalle.subtotal for detalle in self.detalles.all()),
            Decimal("0"),
        )
        self.total = total
        self.save(update_fields=["total"])


class DetalleCompra(models.Model):
    compra = models.ForeignKey(
        Compra,
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="detalles_compra",
    )
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField("Precio unitario", max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["pk"]
        verbose_name = "Detalle de compra"
        verbose_name_plural = "Detalles de compra"
        unique_together = ("compra", "producto")

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return f"{self.producto} x {self.cantidad}"


class Perfil(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil",
    )
    cedula = models.CharField("Cédula", max_length=10, blank=True)
    telefono = models.CharField("Teléfono", max_length=15, blank=True)
    direccion = models.CharField("Dirección", max_length=200, blank=True)
    cargo = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = "Perfil"
        verbose_name_plural = "Perfiles"

    def __str__(self):
        return f"Perfil de {self.usuario}"
