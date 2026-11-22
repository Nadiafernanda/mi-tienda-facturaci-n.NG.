from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .forms import ProveedorForm, RegistroForm
from .models import Categoria, Cliente, Compra, DetalleCompra, DetalleVenta, Marca, Perfil, Producto, Proveedor, Venta


class TiendaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="prueba", password="ClaveSegura123")
        cls.marca = Marca.objects.create(nombre="Marca Prueba")
        cls.categoria = Categoria.objects.create(nombre="Tecnología")
        cls.producto = Producto.objects.create(
            nombre="Producto de prueba",
            descripcion="Descripción",
            precio="25.00",
            stock=4,
            marca=cls.marca,
        )
        cls.producto.categorias.add(cls.categoria)

    def setUp(self):
        self.client.force_login(self.user)

    def test_pagina_inicial_muestra_productos(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mi Tienda")

    def test_vistas_de_gestion_requieren_autenticacion(self):
        self.client.logout()
        response = self.client.get(reverse("facturacion:marca_lista"))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('facturacion:marca_lista')}",
        )

    def test_crear_marca_valida_nombre_y_redirige(self):
        response = self.client.post(
            reverse("facturacion:marca_crear"),
            {"nombre": "  logitech ", "pais_origen": "Suiza", "activo": "on"},
        )
        self.assertRedirects(response, reverse("facturacion:marca_lista"))
        self.assertTrue(Marca.objects.filter(nombre="Logitech").exists())

    def test_producto_se_puede_crear_y_listar(self):
        response = self.client.post(
            reverse("facturacion:producto_crear"),
            {
                "nombre": "Producto sin precio",
                "precio": "0",
                "stock": "1",
                "marca": self.marca.pk,
                "activo": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "El precio debe ser mayor que 0.")

        response = self.client.post(
            reverse("facturacion:producto_crear"),
            {
                "nombre": "Mouse de prueba",
                "descripcion": "Inalámbrico",
                "precio": "18.50",
                "stock": "6",
                "marca": self.marca.pk,
                "categorias": [self.categoria.pk],
                "activo": "on",
            },
        )
        self.assertRedirects(response, reverse("facturacion:producto_lista"))
        producto = Producto.objects.get(nombre="Mouse de prueba")
        self.assertEqual(list(producto.categorias.all()), [self.categoria])
        self.assertContains(self.client.get(reverse("facturacion:producto_lista")), "Mouse de prueba")

    def test_eliminar_categoria_no_elimina_producto(self):
        response = self.client.post(
            reverse("facturacion:categoria_eliminar", args=[self.categoria.pk])
        )
        self.assertRedirects(response, reverse("facturacion:categoria_lista"))
        self.assertTrue(Producto.objects.filter(pk=self.producto.pk).exists())
        self.assertFalse(self.producto.categorias.filter(pk=self.categoria.pk).exists())

    def test_formulario_cliente_valida_cedula_y_busca(self):
        response = self.client.post(
            reverse("facturacion:cliente_crear"),
            {
                "cedula": "12345abcde",
                "nombres": "María",
                "apellidos": "López",
                "email": "",
                "telefono": "",
                "direccion": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "solo números")

        cliente = Cliente.objects.create(
            cedula="1790000001",
            nombres="Elena",
            apellidos="López",
        )
        response = self.client.get(reverse("facturacion:cliente_lista"), {"q": "1790000001"})
        self.assertContains(response, cliente.cedula)
        self.assertEqual(response.context["pagina"].paginator.per_page, 5)

    def test_proveedor_se_puede_crear_desde_el_formulario(self):
        response = self.client.get(reverse("facturacion:proveedor_crear"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nuevo proveedor")
        self.assertContains(response, 'name="ruc"')
        self.assertContains(response, 'type="submit"')

        response = self.client.post(
            reverse("facturacion:proveedor_crear"),
            {
                "nombre": "Distribuidora Andina",
                "ruc": "1790000000001",
                "email": "ventas@example.com",
                "telefono": "0991234567",
                "direccion": "Quito",
                "activo": "on",
            },
        )
        self.assertRedirects(response, reverse("facturacion:proveedor_lista"))
        self.assertTrue(Proveedor.objects.filter(ruc="1790000000001").exists())

    def test_crear_venta_calcula_iva_y_descuenta_inventario(self):
        response = self.client.post(
            reverse("facturacion:venta_crear"),
            {
                "cliente": Cliente.objects.create(
                    cedula="1790000011",
                    nombres="Ana",
                    apellidos="Pérez",
                ).pk,
                "fecha": "2026-11-18T12:14",
                "tipo_pago": Venta.TipoPago.CONTADO,
                "detalles-TOTAL_FORMS": "1",
                "detalles-INITIAL_FORMS": "0",
                "detalles-MIN_NUM_FORMS": "0",
                "detalles-MAX_NUM_FORMS": "1000",
                "detalles-0-producto": self.producto.pk,
                "detalles-0-cantidad": "2",
            },
        )
        venta = Venta.objects.get()
        self.assertRedirects(response, reverse("facturacion:venta_detalle", args=[venta.pk]))
        self.assertEqual(venta.subtotal, 50)
        self.assertEqual(venta.iva, 7.5)
        self.assertEqual(venta.total, 57.5)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 2)

    def test_editar_venta_recalcula_stock_y_eliminar_lo_devuelve(self):
        cliente = Cliente.objects.create(
            cedula="1790000012",
            nombres="Luis",
            apellidos="Mora",
        )
        venta = Venta.objects.create(
            cliente=cliente,
            registrado_por=self.user,
            tipo_pago=Venta.TipoPago.CONTADO,
        )
        DetalleVenta.objects.create(
            venta=venta,
            producto=self.producto,
            cantidad=2,
            precio_unitario=self.producto.precio,
        )
        self.producto.stock = 2
        self.producto.save(update_fields=["stock"])
        venta.recalcular_totales()

        response = self.client.post(
            reverse("facturacion:venta_editar", args=[venta.pk]),
            {
                "cliente": cliente.pk,
                "fecha": "2026-11-18T12:14",
                "tipo_pago": Venta.TipoPago.TARJETA,
                "detalles-TOTAL_FORMS": "2",
                "detalles-INITIAL_FORMS": "1",
                "detalles-MIN_NUM_FORMS": "0",
                "detalles-MAX_NUM_FORMS": "1000",
                "detalles-0-id": venta.detalles.get().pk,
                "detalles-0-producto": self.producto.pk,
                "detalles-0-cantidad": "3",
                "detalles-1-producto": "",
                "detalles-1-cantidad": "",
            },
        )
        self.assertRedirects(response, reverse("facturacion:venta_detalle", args=[venta.pk]))
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 1)
        venta.refresh_from_db()
        self.assertEqual(venta.tipo_pago, Venta.TipoPago.TARJETA)
        self.assertEqual(venta.total, 86.25)

        response = self.client.post(reverse("facturacion:venta_eliminar", args=[venta.pk]))
        self.assertRedirects(response, reverse("facturacion:venta_lista"))
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 4)
        self.assertFalse(Venta.objects.filter(pk=venta.pk).exists())

    def test_venta_no_permite_vender_mas_stock_del_disponible(self):
        cliente = Cliente.objects.create(
            cedula="1790000013",
            nombres="Eva",
            apellidos="Luna",
        )
        response = self.client.post(
            reverse("facturacion:venta_crear"),
            {
                "cliente": cliente.pk,
                "fecha": "2026-11-18T12:14",
                "tipo_pago": Venta.TipoPago.CONTADO,
                "detalles-TOTAL_FORMS": "1",
                "detalles-INITIAL_FORMS": "0",
                "detalles-MIN_NUM_FORMS": "0",
                "detalles-MAX_NUM_FORMS": "1000",
                "detalles-0-producto": self.producto.pk,
                "detalles-0-cantidad": "5",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Stock insuficiente")
        self.assertFalse(Venta.objects.exists())
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 4)

    def test_paginas_de_ventas_y_factura_cargan(self):
        cliente = Cliente.objects.create(
            cedula="1790000014",
            nombres="Nora",
            apellidos="Díaz",
        )
        venta = Venta.objects.create(cliente=cliente, registrado_por=self.user)
        DetalleVenta.objects.create(
            venta=venta,
            producto=self.producto,
            cantidad=1,
            precio_unitario=self.producto.precio,
        )
        urls = [
            reverse("facturacion:venta_lista"),
            reverse("facturacion:venta_crear"),
            reverse("facturacion:venta_detalle", args=[venta.pk]),
            reverse("facturacion:venta_editar", args=[venta.pk]),
            reverse("facturacion:venta_eliminar", args=[venta.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_registro_inicia_sesion_y_crea_perfil(self):
        self.client.logout()
        response = self.client.post(
            reverse("registro"),
            {
                "username": "usuario_nuevo",
                "email": "nuevo@example.com",
                "password1": "48271639",
                "password2": "48271639",
            },
        )
        self.assertRedirects(response, reverse("home"))
        self.assertTrue(User.objects.filter(username="usuario_nuevo").exists())
        self.assertTrue(Perfil.objects.filter(usuario__username="usuario_nuevo").exists())

    def test_registro_acepta_usuario_y_contrasena_sin_restricciones_de_formato(self):
        self.client.logout()
        datos = {
            "username": "usuario libre! ñ",
            "email": "otro@example.com",
            "password1": "abc",
            "password2": "abc",
        }
        response = self.client.post(reverse("registro"), datos)
        self.assertRedirects(response, reverse("home"))
        user = User.objects.get(username=datos["username"])
        self.assertTrue(user.check_password(datos["password1"]))
        self.client.logout()
        response = self.client.post(
            reverse("login"),
            {"username": datos["username"], "password": datos["password1"]},
        )
        self.assertRedirects(response, reverse("home"))

    def test_perfil_actualiza_solo_usuario_autenticado(self):
        response = self.client.post(
            reverse("facturacion:mi_perfil"),
            {
                "cedula": "1234567890",
                "telefono": "0991234567",
                "direccion": "Centro",
                "cargo": "Vendedora",
            },
        )
        self.assertRedirects(response, reverse("facturacion:mi_perfil"))
        self.assertEqual(self.user.perfil.cargo, "Vendedora")

    def test_paginas_de_gestion_y_confirmacion_cargan(self):
        urls = [
            reverse("facturacion:marca_lista"),
            reverse("facturacion:marca_crear"),
            reverse("facturacion:marca_editar", args=[self.marca.pk]),
            reverse("facturacion:marca_eliminar", args=[self.marca.pk]),
            reverse("facturacion:producto_lista"),
            reverse("facturacion:producto_crear"),
            reverse("facturacion:producto_editar", args=[self.producto.pk]),
            reverse("facturacion:producto_detalle", args=[self.producto.pk]),
            reverse("facturacion:producto_eliminar", args=[self.producto.pk]),
            reverse("facturacion:categoria_lista"),
            reverse("facturacion:categoria_crear"),
            reverse("facturacion:categoria_editar", args=[self.categoria.pk]),
            reverse("facturacion:categoria_eliminar", args=[self.categoria.pk]),
            reverse("facturacion:cliente_lista"),
            reverse("facturacion:cliente_crear"),
            reverse("facturacion:mi_perfil"),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        pagina_productos = self.client.get(reverse("facturacion:producto_lista")).context["pagina"]
        self.assertEqual(pagina_productos.paginator.per_page, 5)
        self.assertTrue(pagina_productos.has_next())

        cliente = Cliente.objects.create(
            cedula="1790000099",
            nombres="Cliente",
            apellidos="Ejemplo",
        )
        for url in (
            reverse("facturacion:cliente_detalle", args=[cliente.pk]),
            reverse("facturacion:cliente_editar", args=[cliente.pk]),
            reverse("facturacion:cliente_eliminar", args=[cliente.pk]),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_compra_con_formset_incrementa_stock_y_eliminar_lo_revierte(self):
        proveedor = Proveedor.objects.create(nombre="Prov Test", ruc="1790011122001")
        stock_inicial = self.producto.stock
        response = self.client.post(
            reverse("facturacion:compra_crear"),
            {
                "numero": "COMP-TEST-001",
                "proveedor": proveedor.pk,
                "fecha": "2026-11-21",
                "estado": "REGISTRADA",
                "detalles-TOTAL_FORMS": "1",
                "detalles-INITIAL_FORMS": "0",
                "detalles-MIN_NUM_FORMS": "0",
                "detalles-MAX_NUM_FORMS": "1000",
                "detalles-0-producto": self.producto.pk,
                "detalles-0-cantidad": "10",
                "detalles-0-precio_unitario": "15.00",
            },
        )
        compra = Compra.objects.get(numero="COMP-TEST-001")
        self.assertRedirects(response, reverse("facturacion:compra_detalle", args=[compra.pk]))
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, stock_inicial + 10)
        self.assertEqual(compra.total, Decimal("150.00"))

        response_delete = self.client.post(reverse("facturacion:compra_eliminar", args=[compra.pk]))
        self.assertRedirects(response_delete, reverse("facturacion:compra_lista"))
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, stock_inicial)

    def test_proveedor_valida_ruc_13_digitos_y_terminacion_001(self):
        form_invalido = ProveedorForm(data={"nombre": "Invalido", "ruc": "1790011122002"})
        self.assertFalse(form_invalido.is_valid())
        self.assertIn("ruc", form_invalido.errors)

        form_valido = ProveedorForm(data={"nombre": "Valido", "ruc": "1790011122001"})
        self.assertTrue(form_valido.is_valid())
