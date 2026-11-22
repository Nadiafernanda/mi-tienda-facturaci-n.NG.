from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import Count, F, Q
from django.db.models.deletion import ProtectedError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import (
    CategoriaForm,
    ClienteForm,
    CompraForm,
    DetalleCompraFormSet,
    MarcaForm,
    PerfilForm,
    ProductoForm,
    ProveedorForm,
    RegistroForm,
    VentaDetalleFormSet,
    VentaForm,
)
from .mixins import UsuarioRegistroMixin
from .models import (
    Categoria,
    Cliente,
    Compra,
    DetalleCompra,
    DetalleVenta,
    Marca,
    Perfil,
    Producto,
    Proveedor,
    Venta,
)


# ==============================================================================
# AUTENTICACIÓN (Vistas basadas en funciones requeridas por la guía)
# ==============================================================================

@require_http_methods(["GET", "POST"])
def iniciar_sesion(request):
    """Permite el inicio de sesión del usuario mediante credenciales estándar."""
    if request.user.is_authenticated:
        return redirect("home")
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        auth_login(request, form.get_user())
        messages.success(request, "Sesión iniciada correctamente.")
        return redirect("home")
    return render(request, "registration/login.html", {"form": form})


@require_http_methods(["GET", "POST"])
def registrarse(request):
    """Crea una nueva cuenta de usuario y le asocia su perfil inicial."""
    if request.user.is_authenticated:
        return redirect("home")
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        Perfil.objects.create(usuario=user)
        auth_login(request, user)
        messages.success(request, "Tu cuenta fue creada correctamente.")
        return redirect("home")
    return render(request, "registration/register.html", {"form": form})


@require_POST
def cerrar_sesion(request):
    """Cierra la sesión del usuario activo (protegido contra peticiones GET)."""
    auth_logout(request)
    messages.success(request, "Sesión cerrada.")
    return redirect("home")


# ==============================================================================
# RETO: MI PERFIL (UpdateView sin PK en URL)
# ==============================================================================

class MiPerfilView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """
    Reto (+1 pt): Edita el perfil del usuario autenticado sin requerir un ID en la URL.
    Sobrescribe get_object para obtener o crear el perfil del usuario en sesión.
    """
    model = Perfil
    form_class = PerfilForm
    template_name = "facturacion/perfil_form.html"
    success_url = reverse_lazy("facturacion:mi_perfil")
    success_message = "Tu perfil se actualizó correctamente."
    extra_context = {
        "titulo": "Mi perfil",
        "boton": "Guardar cambios",
        "volver_url": reverse_lazy("home"),
    }

    def get_object(self, queryset=None):
        # Obtiene el perfil del usuario en sesión o lo crea si no existe aún
        perfil, _ = Perfil.objects.get_or_create(usuario=self.request.user)
        return perfil


# ==============================================================================
# CRUD MARCAS (Vistas Basadas en Clases con control de ProtectedError)
# ==============================================================================

class MarcaListView(LoginRequiredMixin, ListView):
    """Muestra el catálogo de marcas con filtro de búsqueda por nombre o país."""
    model = Marca
    template_name = "facturacion/marca_lista.html"
    context_object_name = "marcas"
    paginate_by = 10
    extra_context = {"titulo": "Marcas"}

    def get_queryset(self):
        # Permite filtrar por nombre o país de origen desde la caja de búsqueda (?q=)
        queryset = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            queryset = queryset.filter(Q(nombre__icontains=q) | Q(pais_origen__icontains=q))
        return queryset

    def get_context_data(self, **kwargs):
        # Pasa el parámetro de búsqueda para persistirlo en el input HTML
        contexto = super().get_context_data(**kwargs)
        contexto["q"] = self.request.GET.get("q", "").strip()
        contexto["pagina"] = contexto.get("page_obj")
        return contexto


class MarcaCreateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, CreateView):
    """Crea una nueva marca y asigna el usuario registrador."""
    model = Marca
    form_class = MarcaForm
    template_name = "facturacion/marca_form.html"
    success_url = reverse_lazy("facturacion:marca_lista")
    success_message = "Marca creada correctamente."
    extra_context = {
        "titulo": "Nueva marca",
        "boton": "Guardar",
        "volver_url": reverse_lazy("facturacion:marca_lista"),
    }


class MarcaUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Permite editar los datos de una marca existente."""
    model = Marca
    form_class = MarcaForm
    template_name = "facturacion/marca_form.html"
    success_url = reverse_lazy("facturacion:marca_lista")
    success_message = "Marca actualizada correctamente."

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["titulo"] = f"Editar marca: {self.object.nombre}"
        contexto["boton"] = "Actualizar"
        contexto["volver_url"] = reverse_lazy("facturacion:marca_lista")
        return contexto


class MarcaDeleteView(LoginRequiredMixin, DeleteView):
    """Elimina una marca capturando ProtectedError si posee productos asociados."""
    model = Marca
    template_name = "facturacion/marca_eliminar.html"
    context_object_name = "marca"
    success_url = reverse_lazy("facturacion:marca_lista")
    extra_context = {"titulo": "Eliminar marca"}

    def form_valid(self, form):
        # Control de integridad referencial: no permitir borrar marcas con productos
        nombre = self.object.nombre
        try:
            return super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                f"No se puede eliminar la marca «{nombre}» porque tiene productos asociados. Desactívala en su lugar.",
            )
            return redirect(self.success_url)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        nombre = self.object.nombre
        try:
            respuesta = super().post(request, *args, **kwargs)
            messages.success(request, f"Marca «{nombre}» eliminada.")
            return respuesta
        except ProtectedError:
            messages.error(
                request,
                f"No se puede eliminar la marca «{nombre}» porque tiene productos asociados. Desactívala en su lugar.",
            )
            return redirect(self.success_url)


# ==============================================================================
# CRUD CATEGORÍAS (VBC con conteo de productos asociados)
# ==============================================================================

class CategoriaListView(LoginRequiredMixin, ListView):
    """Lista las categorías con el conteo de productos asignados mediante annotate."""
    model = Categoria
    template_name = "facturacion/categoria_lista.html"
    context_object_name = "categorias"
    paginate_by = 10
    extra_context = {"titulo": "Categorías"}

    def get_queryset(self):
        # Optimización con Count para mostrar cuántos productos tiene cada categoría
        queryset = Categoria.objects.annotate(cantidad_productos=Count("productos", distinct=True)).order_by("nombre")
        q = self.request.GET.get("q", "").strip()
        if q:
            queryset = queryset.filter(nombre__icontains=q)
        return queryset

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["q"] = self.request.GET.get("q", "").strip()
        contexto["pagina"] = contexto.get("page_obj")
        return contexto


class CategoriaCreateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, CreateView):
    """Crea una categoría en el sistema."""
    model = Categoria
    form_class = CategoriaForm
    template_name = "facturacion/categoria_form.html"
    success_url = reverse_lazy("facturacion:categoria_lista")
    success_message = "Categoría creada correctamente."
    extra_context = {
        "titulo": "Nueva categoría",
        "boton": "Guardar",
        "volver_url": reverse_lazy("facturacion:categoria_lista"),
    }


class CategoriaUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Actualiza la información de una categoría."""
    model = Categoria
    form_class = CategoriaForm
    template_name = "facturacion/categoria_form.html"
    success_url = reverse_lazy("facturacion:categoria_lista")
    success_message = "Categoría actualizada correctamente."

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["titulo"] = f"Editar categoría: {self.object.nombre}"
        contexto["boton"] = "Actualizar"
        contexto["volver_url"] = reverse_lazy("facturacion:categoria_lista")
        return contexto


class CategoriaDeleteView(LoginRequiredMixin, DeleteView):
    """Elimina una categoría del sistema (relación N:M, se desvinculan productos)."""
    model = Categoria
    template_name = "facturacion/categoria_eliminar.html"
    context_object_name = "categoria"
    success_url = reverse_lazy("facturacion:categoria_lista")
    extra_context = {"titulo": "Eliminar categoría"}

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        nombre = self.object.nombre
        respuesta = super().post(request, *args, **kwargs)
        messages.success(request, f"Categoría «{nombre}» eliminada.")
        return respuesta


# ==============================================================================
# CRUD CLIENTES (VBC con validación de cédula, búsqueda Q y vista Detalle)
# ==============================================================================

class ClienteListView(LoginRequiredMixin, ListView):
    """Lista paginada de clientes con buscador por apellido, nombre o cédula usando Q."""
    model = Cliente
    template_name = "facturacion/cliente_lista.html"
    context_object_name = "clientes"
    paginate_by = 5
    extra_context = {"titulo": "Clientes"}

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            queryset = queryset.filter(
                Q(apellidos__icontains=q) | Q(nombres__icontains=q) | Q(cedula__icontains=q)
            )
        return queryset

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["q"] = self.request.GET.get("q", "").strip()
        contexto["pagina"] = contexto.get("page_obj")
        return contexto


class ClienteDetailView(LoginRequiredMixin, DetailView):
    """Muestra la ficha del cliente y el historial completo de sus compras/ventas."""
    model = Cliente
    template_name = "facturacion/cliente_detalle.html"
    context_object_name = "cliente"

    def get_queryset(self):
        # Prefetch de las ventas para optimizar consultas en la plantilla
        return super().get_queryset().prefetch_related("ventas")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["titulo"] = f"Cliente: {self.object}"
        return contexto


class ClienteCreateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, CreateView):
    """Registra un nuevo cliente validando cédula de 10 dígitos."""
    model = Cliente
    form_class = ClienteForm
    template_name = "facturacion/cliente_form.html"
    success_url = reverse_lazy("facturacion:cliente_lista")
    success_message = "Cliente registrado correctamente."
    extra_context = {
        "titulo": "Nuevo cliente",
        "boton": "Guardar",
        "volver_url": reverse_lazy("facturacion:cliente_lista"),
    }


class ClienteUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Actualiza la información de un cliente existente."""
    model = Cliente
    form_class = ClienteForm
    template_name = "facturacion/cliente_form.html"
    success_url = reverse_lazy("facturacion:cliente_lista")
    success_message = "Datos del cliente actualizados."

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["titulo"] = f"Editar cliente: {self.object}"
        contexto["boton"] = "Actualizar"
        contexto["volver_url"] = reverse_lazy("facturacion:cliente_lista")
        return contexto


class ClienteDeleteView(LoginRequiredMixin, DeleteView):
    """Elimina un cliente verificando que no posea ventas mediante ProtectedError."""
    model = Cliente
    template_name = "facturacion/cliente_eliminar.html"
    context_object_name = "cliente"
    success_url = reverse_lazy("facturacion:cliente_lista")
    extra_context = {"titulo": "Eliminar cliente"}

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        nombre = str(self.object)
        try:
            respuesta = super().post(request, *args, **kwargs)
            messages.success(request, f"Cliente «{nombre}» eliminado.")
            return respuesta
        except ProtectedError:
            messages.error(
                request,
                f"No se puede eliminar a «{nombre}» porque tiene ventas registradas.",
            )
            return redirect(self.success_url)


# ==============================================================================
# CRUD PROVEEDORES (VBC con subida de Logo y validación de RUC)
# ==============================================================================

class ProveedorListView(LoginRequiredMixin, ListView):
    """Lista proveedores con miniaturas de logo y buscador por nombre o RUC."""
    model = Proveedor
    template_name = "facturacion/proveedor_lista.html"
    context_object_name = "proveedores"
    paginate_by = 10
    extra_context = {"titulo": "Proveedores"}

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            queryset = queryset.filter(Q(nombre__icontains=q) | Q(ruc__icontains=q))
        return queryset

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["q"] = self.request.GET.get("q", "").strip()
        contexto["pagina"] = contexto.get("page_obj")
        return contexto


class ProveedorCreateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, CreateView):
    """Registra un proveedor con logo opcional y RUC terminado en 001."""
    model = Proveedor
    form_class = ProveedorForm
    template_name = "facturacion/proveedor_form.html"
    success_url = reverse_lazy("facturacion:proveedor_lista")
    success_message = "Proveedor registrado correctamente."
    extra_context = {
        "titulo": "Nuevo proveedor",
        "boton": "Guardar",
        "volver_url": reverse_lazy("facturacion:proveedor_lista"),
    }


class ProveedorUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Permite editar datos o cambiar el logo de un proveedor."""
    model = Proveedor
    form_class = ProveedorForm
    template_name = "facturacion/proveedor_form.html"
    success_url = reverse_lazy("facturacion:proveedor_lista")
    success_message = "Proveedor actualizado correctamente."

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["titulo"] = f"Editar proveedor: {self.object.nombre}"
        contexto["boton"] = "Actualizar"
        contexto["volver_url"] = reverse_lazy("facturacion:proveedor_lista")
        return contexto


class ProveedorDeleteView(LoginRequiredMixin, DeleteView):
    """Elimina un proveedor controlando ProtectedError si tiene compras registradas."""
    model = Proveedor
    template_name = "facturacion/proveedor_eliminar.html"
    context_object_name = "proveedor"
    success_url = reverse_lazy("facturacion:proveedor_lista")
    extra_context = {"titulo": "Eliminar proveedor"}

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        nombre = self.object.nombre
        try:
            respuesta = super().post(request, *args, **kwargs)
            messages.success(request, f"Proveedor «{nombre}» eliminado.")
            return respuesta
        except ProtectedError:
            messages.error(
                request,
                f"No se puede eliminar «{nombre}» porque tiene compras asociadas.",
            )
            return redirect(self.success_url)


# ==============================================================================
# CRUD PRODUCTOS (VBC con foto, filtros Q y control de ProtectedError)
# ==============================================================================

class ProductoListView(LoginRequiredMixin, ListView):
    """Catálogo paginado de productos con búsqueda multicriterio (marca, nombre, categoría)."""
    model = Producto
    template_name = "facturacion/producto_lista.html"
    context_object_name = "productos"
    paginate_by = 5
    extra_context = {"titulo": "Productos"}

    def get_queryset(self):
        queryset = Producto.objects.select_related("marca").prefetch_related("categorias")
        q = self.request.GET.get("q", "").strip()
        if q:
            queryset = queryset.filter(
                Q(nombre__icontains=q)
                | Q(descripcion__icontains=q)
                | Q(marca__nombre__icontains=q)
                | Q(categorias__nombre__icontains=q)
            ).distinct()
        return queryset

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["q"] = self.request.GET.get("q", "").strip()
        contexto["pagina"] = contexto.get("page_obj")
        return contexto


class ProductoDetailView(LoginRequiredMixin, DetailView):
    """Muestra la ficha técnica detallada del producto con su fotografía."""
    model = Producto
    template_name = "facturacion/producto_detalle.html"
    context_object_name = "producto"

    def get_queryset(self):
        return super().get_queryset().select_related("marca").prefetch_related("categorias")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["titulo"] = self.object.nombre
        return contexto


class ProductoCreateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, CreateView):
    """Crea un nuevo producto soportando la carga de imagen en multipart/form-data."""
    model = Producto
    form_class = ProductoForm
    template_name = "facturacion/producto_form.html"
    success_url = reverse_lazy("facturacion:producto_lista")
    success_message = "Producto creado correctamente."
    extra_context = {
        "titulo": "Nuevo producto",
        "boton": "Guardar",
        "volver_url": reverse_lazy("facturacion:producto_lista"),
    }


class ProductoUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Actualiza producto permitiendo reemplazar o limpiar la foto."""
    model = Producto
    form_class = ProductoForm
    template_name = "facturacion/producto_form.html"
    success_url = reverse_lazy("facturacion:producto_lista")
    success_message = "Producto actualizado correctamente."

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["titulo"] = f"Editar producto: {self.object.nombre}"
        contexto["boton"] = "Actualizar"
        contexto["volver_url"] = reverse_lazy("facturacion:producto_lista")
        return contexto


class ProductoDeleteView(LoginRequiredMixin, DeleteView):
    """Elimina producto atrapando ProtectedError si existe en compras o ventas."""
    model = Producto
    template_name = "facturacion/producto_eliminar.html"
    context_object_name = "producto"
    success_url = reverse_lazy("facturacion:producto_lista")
    extra_context = {"titulo": "Eliminar producto"}

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        nombre = self.object.nombre
        try:
            respuesta = super().post(request, *args, **kwargs)
            messages.success(request, f"Producto «{nombre}» eliminado.")
            return respuesta
        except ProtectedError:
            messages.error(
                request,
                f"No se puede eliminar «{nombre}» porque aparece en compras o ventas registradas.",
            )
            return redirect(self.success_url)


# ==============================================================================
# MÓDULO VENTAS (Maestro-Detalle con Formset, Stock e IVA)
# ==============================================================================

class VentaListView(LoginRequiredMixin, ListView):
    """Listado de ventas paginado con filtro de búsqueda por cliente o tipo de pago."""
    model = Venta
    template_name = "facturacion/venta_lista.html"
    context_object_name = "ventas"
    paginate_by = 5
    extra_context = {"titulo": "Ventas"}

    def get_queryset(self):
        queryset = Venta.objects.select_related("cliente")
        q = self.request.GET.get("q", "").strip()
        tipo_pago = self.request.GET.get("tipo_pago", "").strip()
        if q:
            queryset = queryset.filter(
                Q(cliente__nombres__icontains=q)
                | Q(cliente__apellidos__icontains=q)
                | Q(cliente__cedula__icontains=q)
            )
        if tipo_pago:
            queryset = queryset.filter(tipo_pago=tipo_pago)
        return queryset

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["q"] = self.request.GET.get("q", "").strip()
        contexto["tipo_pago"] = self.request.GET.get("tipo_pago", "").strip()
        contexto["pagina"] = contexto.get("page_obj")
        return contexto


class VentaDetallesMixin:
    """Mixin que administra la lógica compartida de crear y editar ventas con formset."""
    model = Venta
    form_class = VentaForm
    template_name = "facturacion/venta_form.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        if "formset" not in contexto:
            fs = VentaDetalleFormSet(instance=self.object)
            contexto["formset"] = fs
            contexto["detalles"] = fs
        contexto["volver_url"] = reverse_lazy("facturacion:venta_lista")
        return contexto

    def post(self, request, *args, **kwargs):
        # Determina si estamos en edición o creación fijando self.object
        self.object = self.get_object() if hasattr(self, "get_object") and "pk" in self.kwargs else None
        form = self.get_form()
        detalles = VentaDetalleFormSet(request.POST, instance=self.object)
        if form.is_valid() and detalles.is_valid():
            return self.form_valid(form, detalles)
        return self.form_invalid(form, detalles)

    def form_valid(self, form, detalles):
        # Transacción atómica: se ejecuta todo o se revierte todo
        with transaction.atomic():
            if self.object:
                # Al editar, primero devolvemos las unidades al stock para recalcular
                self.object.devolver_stock()
            form.instance.registrado_por = self.request.user
            self.object = form.save()
            detalles.instance = self.object
            filas = detalles.save(commit=False)
            for fila in detalles.deleted_objects:
                fila.delete()
            for fila in filas:
                if not fila.precio_unitario:
                    fila.precio_unitario = fila.producto.precio
                fila.save()
            detalles.save_m2m()
            # Descontamos las nuevas unidades vendidas y recalculamos totales
            self.object.descontar_stock()
            self.object.recalcular_totales()

        messages.success(self.request, f"{self.object} guardada con éxito. Total: ${self.object.total}")
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form, detalles):
        messages.error(self.request, "Por favor corrige los errores en el formulario de venta.")
        return self.render_to_response(self.get_context_data(form=form, formset=detalles, detalles=detalles))

    def get_success_url(self):
        return reverse("facturacion:venta_detalle", kwargs={"pk": self.object.pk})


class VentaCreateView(LoginRequiredMixin, VentaDetallesMixin, CreateView):
    """Crea una nueva factura de venta con sus líneas de detalle."""
    extra_context = {"titulo": "Nueva venta", "boton": "Guardar venta"}


class VentaUpdateView(LoginRequiredMixin, VentaDetallesMixin, UpdateView):
    """Edita una venta existente ajustando las filas y el stock."""
    extra_context = {"titulo": "Editar venta", "boton": "Actualizar venta"}


class VentaDetailView(LoginRequiredMixin, DetailView):
    """Visualización e impresión de la factura comercial con desglose de IVA 15%."""
    model = Venta
    template_name = "facturacion/venta_detalle.html"
    context_object_name = "venta"

    def get_queryset(self):
        return super().get_queryset().select_related("cliente", "registrado_por").prefetch_related("detalles__producto")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["titulo"] = f"Factura {self.object}"
        contexto["iva_porcentaje"] = 15
        return contexto


class VentaDeleteView(LoginRequiredMixin, DeleteView):
    """Elimina una venta y regresa automáticamente el stock de los productos vendidos."""
    model = Venta
    template_name = "facturacion/venta_eliminar.html"
    context_object_name = "venta"
    success_url = reverse_lazy("facturacion:venta_lista")
    extra_context = {"titulo": "Eliminar venta"}

    def form_valid(self, form):
        with transaction.atomic():
            self.object.devolver_stock()
            respuesta = super().form_valid(form)
        messages.success(self.request, "Venta eliminada y stock restituido.")
        return respuesta


# ==============================================================================
# MÓDULO COMPRAS (Maestro-Detalle con Formset, Aumento y Reversión de Stock)
# ==============================================================================

class CompraListView(LoginRequiredMixin, ListView):
    """Lista de compras realizadas a proveedores con filtro por número o proveedor."""
    model = Compra
    template_name = "facturacion/compra_lista.html"
    context_object_name = "compras"
    paginate_by = 5
    extra_context = {"titulo": "Compras"}

    def get_queryset(self):
        queryset = Compra.objects.select_related("proveedor", "usuario")
        q = self.request.GET.get("q", "").strip()
        if q:
            queryset = queryset.filter(
                Q(numero__icontains=q)
                | Q(proveedor__nombre__icontains=q)
                | Q(proveedor__ruc__icontains=q)
            )
        return queryset

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["q"] = self.request.GET.get("q", "").strip()
        contexto["pagina"] = contexto.get("page_obj")
        return contexto


class CompraDetallesMixin:
    """Mixin que gestiona el maestro-detalle de Compras con incremento de stock."""
    model = Compra
    form_class = CompraForm
    template_name = "facturacion/compra_form.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        if "formset" not in contexto:
            fs = DetalleCompraFormSet(instance=self.object)
            contexto["formset"] = fs
            contexto["detalles"] = fs
        contexto["volver_url"] = reverse_lazy("facturacion:compra_lista")
        return contexto

    def post(self, request, *args, **kwargs):
        self.object = self.get_object() if hasattr(self, "get_object") and "pk" in self.kwargs else None
        form = self.get_form()
        detalles = DetalleCompraFormSet(request.POST, instance=self.object)
        if form.is_valid() and detalles.is_valid():
            return self.form_valid(form, detalles)
        return self.form_invalid(form, detalles)

    def form_valid(self, form, detalles):
        # Transacción atómica: ingreso de mercadería a bodega
        with transaction.atomic():
            if self.object:
                # Al editar, revertimos el stock anterior antes de aplicar las nuevas cantidades
                self.object.revertir_stock()
            form.instance.usuario = self.request.user
            self.object = form.save()
            detalles.instance = self.object
            detalles.save()
            # El stock SUBE con las unidades compradas
            self.object.ingresar_stock()
            self.object.recalcular_total()

        messages.success(self.request, f"Compra {self.object.numero} guardada. Total: ${self.object.total}")
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form, detalles):
        messages.error(self.request, "Por favor corrige los datos del formulario de compra.")
        return self.render_to_response(self.get_context_data(form=form, formset=detalles, detalles=detalles))

    def get_success_url(self):
        return reverse("facturacion:compra_detalle", kwargs={"pk": self.object.pk})


class CompraCreateView(LoginRequiredMixin, CompraDetallesMixin, CreateView):
    """Registra una compra ingresando productos e incrementando stock."""
    extra_context = {"titulo": "Nueva compra", "boton": "Guardar compra"}


class CompraUpdateView(LoginRequiredMixin, CompraDetallesMixin, UpdateView):
    """Permite editar una compra existente recalculando stock y totales."""
    extra_context = {"titulo": "Editar compra", "boton": "Actualizar compra"}


class CompraDetailView(LoginRequiredMixin, DetailView):
    """Muestra el comprobante detallado de la orden de compra a proveedor."""
    model = Compra
    template_name = "facturacion/compra_detalle.html"
    context_object_name = "compra"

    def get_queryset(self):
        return super().get_queryset().select_related("proveedor", "usuario").prefetch_related("detalles__producto")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["titulo"] = f"Comprobante {self.object.numero}"
        return contexto


class CompraDeleteView(LoginRequiredMixin, DeleteView):
    """Elimina una compra y revierte (resta) del inventario las unidades compradas."""
    model = Compra
    template_name = "facturacion/compra_eliminar.html"
    context_object_name = "compra"
    success_url = reverse_lazy("facturacion:compra_lista")
    extra_context = {"titulo": "Eliminar compra"}

    def form_valid(self, form):
        with transaction.atomic():
            self.object.revertir_stock()
            respuesta = super().form_valid(form)
        messages.success(self.request, "Compra eliminada y stock revertido correctamente.")
        return respuesta
