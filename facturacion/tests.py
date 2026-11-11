from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .forms import RegistroForm
from .models import Categoria, Cliente, Marca, Perfil, Producto


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

    def test_registro_rechaza_contrasenas_comunes_o_no_numericas(self):
        datos = {
            "username": "otro_usuario",
            "email": "otro@example.com",
            "password1": "4827abc9",
            "password2": "4827abc9",
        }
        form = RegistroForm(data=datos)
        self.assertFalse(form.is_valid())
        self.assertIn("únicamente números", str(form.errors))

        datos["password1"] = "12345678"
        datos["password2"] = "12345678"
        form = RegistroForm(data=datos)
        self.assertFalse(form.is_valid())
        self.assertIn("demasiado común", str(form.errors).lower())

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
