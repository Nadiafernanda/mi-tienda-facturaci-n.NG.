from django.contrib import admin

from .models import (
    Categoria,
    Cliente,
    Compra,
    DetalleCompra,
    Marca,
    Perfil,
    Producto,
    Proveedor,
    DetalleVenta,
    Venta,
)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo")
    search_fields = ("nombre",)
    list_filter = ("activo",)


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "pais_origen", "activo")
    search_fields = ("nombre", "pais_origen")
    list_filter = ("activo",)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "marca", "precio", "stock", "activo")
    search_fields = ("nombre", "marca__nombre")
    list_filter = ("marca", "categorias", "activo")
    filter_horizontal = ("categorias",)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("cedula", "apellidos", "nombres", "email", "telefono")
    search_fields = ("cedula", "apellidos", "nombres")


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("usuario", "cedula", "telefono", "cargo")
    search_fields = ("usuario__username", "cedula")


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "ruc", "email", "telefono", "activo")
    search_fields = ("nombre", "ruc")
    list_filter = ("activo",)


class DetalleCompraInline(admin.TabularInline):
    model = DetalleCompra
    extra = 1


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ("numero", "proveedor", "fecha", "total", "estado")
    search_fields = ("numero", "proveedor__nombre")
    list_filter = ("estado", "fecha", "proveedor")
    inlines = (DetalleCompraInline,)


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "fecha", "tipo_pago", "total", "registrado_por")
    search_fields = ("cliente__cedula", "cliente__nombres", "cliente__apellidos")
    list_filter = ("tipo_pago", "fecha")
    inlines = (DetalleVentaInline,)
