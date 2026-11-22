from django.contrib import messages
from django import forms
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, F, Q
from django.db.models.deletion import ProtectedError
from django.db import transaction
from django.forms import inlineformset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import (
    CategoriaForm,
    ClienteForm,
    CompraForm,
    DetalleCompraForm,
    MarcaForm,
    PerfilForm,
    ProductoForm,
    ProveedorForm,
    RegistroForm,
    VentaDetalleFormSet,
    VentaForm,
)
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


@require_http_methods(["GET", "POST"])
def iniciar_sesion(request):
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
    auth_logout(request)
    messages.success(request, "Sesión cerrada.")
    return redirect("home")


@login_required
@require_http_methods(["GET", "POST"])
def mi_perfil(request):
    perfil, _ = Perfil.objects.get_or_create(usuario=request.user)
    form = PerfilForm(request.POST or None, instance=perfil)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Tu perfil se actualizó correctamente.")
        return redirect("facturacion:mi_perfil")
    return render(
        request,
        "facturacion/perfil_form.html",
        {"form": form, "titulo": "Mi perfil", "boton": "Guardar", "volver_url": reverse("home")},
    )


@login_required
@require_GET
def marca_lista(request):
    q = request.GET.get("q", "").strip()
    marcas = Marca.objects.all()
    if q:
        marcas = marcas.filter(Q(nombre__icontains=q) | Q(pais_origen__icontains=q))
    return render(
        request,
        "facturacion/marca_lista.html",
        {"marcas": marcas, "q": q, "titulo": "Marcas"},
    )


@login_required
@require_http_methods(["GET", "POST"])
def marca_crear(request):
    form = MarcaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        marca = form.save()
        messages.success(request, f"Marca «{marca.nombre}» creada correctamente.")
        return redirect("facturacion:marca_lista")
    return render(
        request,
        "facturacion/marca_form.html",
        {"form": form, "titulo": "Nueva marca", "boton": "Guardar", "volver_url": reverse("facturacion:marca_lista")},
    )


@login_required
@require_http_methods(["GET", "POST"])
def marca_editar(request, pk):
    marca = get_object_or_404(Marca, pk=pk)
    form = MarcaForm(request.POST or None, instance=marca)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Marca «{marca.nombre}» actualizada.")
        return redirect("facturacion:marca_lista")
    return render(
        request,
        "facturacion/marca_form.html",
        {"form": form, "titulo": f"Editar marca: {marca.nombre}", "boton": "Actualizar", "volver_url": reverse("facturacion:marca_lista")},
    )


@login_required
@require_http_methods(["GET", "POST"])
def marca_eliminar(request, pk):
    marca = get_object_or_404(Marca, pk=pk)
    if request.method == "POST":
        nombre = marca.nombre
        try:
            marca.delete()
        except ProtectedError:
            messages.error(
                request,
                f"No se puede eliminar «{nombre}» porque tiene productos. Desactívala en su lugar.",
            )
        else:
            messages.success(request, f"Marca «{nombre}» eliminada.")
        return redirect("facturacion:marca_lista")
    return render(
        request,
        "facturacion/marca_eliminar.html",
        {"marca": marca, "titulo": "Eliminar marca"},
    )


@login_required
@require_GET
def producto_lista(request):
    q = request.GET.get("q", "").strip()
    productos = Producto.objects.select_related("marca").prefetch_related("categorias")
    if q:
        productos = productos.filter(
            Q(nombre__icontains=q)
            | Q(descripcion__icontains=q)
            | Q(marca__nombre__icontains=q)
            | Q(categorias__nombre__icontains=q)
        ).distinct()
    pagina = Paginator(productos, 5).get_page(request.GET.get("page"))
    return render(
        request,
        "facturacion/producto_lista.html",
        {"pagina": pagina, "productos": pagina.object_list, "q": q, "titulo": "Productos"},
    )


@login_required
@require_http_methods(["GET", "POST"])
def producto_crear(request):
    form = ProductoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        producto = form.save()
        messages.success(request, f"Producto «{producto.nombre}» creado correctamente.")
        return redirect("facturacion:producto_lista")
    return render(
        request,
        "facturacion/producto_form.html",
        {"form": form, "titulo": "Nuevo producto", "boton": "Guardar", "volver_url": reverse("facturacion:producto_lista")},
    )


@login_required
@require_http_methods(["GET", "POST"])
def producto_editar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    form = ProductoForm(request.POST or None, instance=producto)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Producto «{producto.nombre}» actualizado.")
        return redirect("facturacion:producto_lista")
    return render(
        request,
        "facturacion/producto_form.html",
        {"form": form, "titulo": f"Editar producto: {producto.nombre}", "boton": "Actualizar", "volver_url": reverse("facturacion:producto_lista")},
    )


@login_required
@require_GET
def producto_detalle(request, pk):
    producto = get_object_or_404(
        Producto.objects.select_related("marca").prefetch_related("categorias"),
        pk=pk,
    )
    return render(
        request,
        "facturacion/producto_detalle.html",
        {"producto": producto, "titulo": producto.nombre},
    )


@login_required
@require_http_methods(["GET", "POST"])
def producto_eliminar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == "POST":
        nombre = producto.nombre
        try:
            producto.delete()
        except ProtectedError:
            messages.error(
                request,
                f"No se puede eliminar «{nombre}» porque aparece en compras o ventas.",
            )
        else:
            messages.success(request, f"Producto «{nombre}» eliminado.")
        return redirect("facturacion:producto_lista")
    return render(
        request,
        "facturacion/producto_eliminar.html",
        {"producto": producto, "titulo": "Eliminar producto"},
    )


@login_required
@require_GET
def categoria_lista(request):
    q = request.GET.get("q", "").strip()
    categorias = Categoria.objects.annotate(cantidad_productos=Count("productos", distinct=True))
    if q:
        categorias = categorias.filter(nombre__icontains=q)
    return render(
        request,
        "facturacion/categoria_lista.html",
        {"categorias": categorias, "q": q, "titulo": "Categorías"},
    )


@login_required
@require_http_methods(["GET", "POST"])
def categoria_crear(request):
    form = CategoriaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        categoria = form.save()
        messages.success(request, f"Categoría «{categoria.nombre}» creada correctamente.")
        return redirect("facturacion:categoria_lista")
    return render(
        request,
        "facturacion/categoria_form.html",
        {"form": form, "titulo": "Nueva categoría", "boton": "Guardar", "volver_url": reverse("facturacion:categoria_lista")},
    )


@login_required
@require_http_methods(["GET", "POST"])
def categoria_editar(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    form = CategoriaForm(request.POST or None, instance=categoria)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Categoría «{categoria.nombre}» actualizada.")
        return redirect("facturacion:categoria_lista")
    return render(
        request,
        "facturacion/categoria_form.html",
        {"form": form, "titulo": f"Editar categoría: {categoria.nombre}", "boton": "Actualizar", "volver_url": reverse("facturacion:categoria_lista")},
    )


@login_required
@require_http_methods(["GET", "POST"])
def categoria_eliminar(request, pk):
    categoria = get_object_or_404(
        Categoria.objects.annotate(cantidad_productos=Count("productos", distinct=True)),
        pk=pk,
    )
    if request.method == "POST":
        nombre = categoria.nombre
        categoria.delete()
        messages.success(request, f"Categoría «{nombre}» eliminada.")
        return redirect("facturacion:categoria_lista")
    return render(
        request,
        "facturacion/categoria_eliminar.html",
        {"categoria": categoria, "titulo": "Eliminar categoría"},
    )


@login_required
@require_GET
def cliente_lista(request):
    q = request.GET.get("q", "").strip()
    clientes = Cliente.objects.all()
    if q:
        clientes = clientes.filter(Q(apellidos__icontains=q) | Q(cedula__icontains=q))
    pagina = Paginator(clientes, 5).get_page(request.GET.get("page"))
    return render(
        request,
        "facturacion/cliente_lista.html",
        {"pagina": pagina, "clientes": pagina.object_list, "q": q, "titulo": "Clientes"},
    )


@login_required
@require_http_methods(["GET", "POST"])
def cliente_crear(request):
    form = ClienteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        cliente = form.save()
        messages.success(request, f"Cliente «{cliente}» creado correctamente.")
        return redirect("facturacion:cliente_lista")
    return render(
        request,
        "facturacion/cliente_form.html",
        {"form": form, "titulo": "Nuevo cliente", "boton": "Guardar", "volver_url": reverse("facturacion:cliente_lista")},
    )


@login_required
@require_http_methods(["GET", "POST"])
def cliente_editar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    form = ClienteForm(request.POST or None, instance=cliente)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Cliente «{cliente}» actualizado.")
        return redirect("facturacion:cliente_lista")
    return render(
        request,
        "facturacion/cliente_form.html",
        {"form": form, "titulo": f"Editar cliente: {cliente}", "boton": "Actualizar", "volver_url": reverse("facturacion:cliente_lista")},
    )


@login_required
@require_http_methods(["GET", "POST"])
def cliente_eliminar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == "POST":
        nombre = str(cliente)
        try:
            cliente.delete()
        except ProtectedError:
            messages.error(
                request,
                f"No se puede eliminar a «{nombre}» porque tiene ventas asociadas.",
            )
        else:
            messages.success(request, f"Cliente «{nombre}» eliminado.")
        return redirect("facturacion:cliente_lista")
    return render(
        request,
        "facturacion/cliente_eliminar.html",
        {"cliente": cliente, "titulo": "Eliminar cliente"},
    )


@login_required
@require_GET
def cliente_detalle(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    return render(
        request,
        "facturacion/cliente_detalle.html",
        {"cliente": cliente, "titulo": str(cliente)},
    )


@login_required
@require_GET
def proveedor_lista(request):
    q = request.GET.get("q", "").strip()
    proveedores = Proveedor.objects.all()
    if q:
        proveedores = proveedores.filter(
            Q(nombre__icontains=q) | Q(ruc__icontains=q)
        )
    return render(
        request,
        "facturacion/proveedor_lista.html",
        {"proveedores": proveedores, "q": q, "titulo": "Proveedores"},
    )


@login_required
@require_http_methods(["GET", "POST"])
def proveedor_crear(request):
    form = ProveedorForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        proveedor = form.save()
        messages.success(request, f"Proveedor «{proveedor.nombre}» creado correctamente.")
        return redirect("facturacion:proveedor_lista")
    return render(
        request,
        "facturacion/proveedor_form.html",
        {"form": form, "titulo": "Nuevo proveedor", "boton": "Guardar", "volver_url": reverse("facturacion:proveedor_lista")},
    )


@login_required
@require_http_methods(["GET", "POST"])
def proveedor_editar(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    form = ProveedorForm(request.POST or None, instance=proveedor)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Proveedor «{proveedor.nombre}» actualizado.")
        return redirect("facturacion:proveedor_lista")
    return render(
        request,
        "facturacion/proveedor_form.html",
        {"form": form, "titulo": f"Editar proveedor: {proveedor.nombre}", "boton": "Actualizar", "volver_url": reverse("facturacion:proveedor_lista")},
    )


@login_required
@require_http_methods(["GET", "POST"])
def proveedor_eliminar(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    if request.method == "POST":
        nombre = proveedor.nombre
        try:
            proveedor.delete()
        except ProtectedError:
            messages.error(request, f"No se puede eliminar «{nombre}» porque tiene compras.")
        else:
            messages.success(request, f"Proveedor «{nombre}» eliminado.")
        return redirect("facturacion:proveedor_lista")
    return render(
        request,
        "facturacion/proveedor_eliminar.html",
        {"proveedor": proveedor, "titulo": "Eliminar proveedor"},
    )


DetalleCompraFormSet = inlineformset_factory(
    Compra,
    DetalleCompra,
    form=DetalleCompraForm,
    extra=1,
    can_delete=True,
)


@login_required
@require_GET
def compra_lista(request):
    compras = Compra.objects.select_related("proveedor", "usuario").prefetch_related("detalles")
    q = request.GET.get("q", "").strip()
    if q:
        compras = compras.filter(
            Q(numero__icontains=q) | Q(proveedor__nombre__icontains=q)
        )
    pagina = Paginator(compras, 5).get_page(request.GET.get("page"))
    return render(
        request,
        "facturacion/compra_lista.html",
        {"pagina": pagina, "compras": pagina.object_list, "q": q, "titulo": "Compras"},
    )


@login_required
@require_http_methods(["GET", "POST"])
def compra_crear(request):
    form = CompraForm(request.POST or None)
    formset = DetalleCompraFormSet(request.POST or None)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            compra = form.save(commit=False)
            compra.usuario = request.user
            compra.save()
            detalles = formset.save(commit=False)
            if not detalles:
                transaction.set_rollback(True)
            else:
                for detalle in detalles:
                    if detalle.pk is None:
                        detalle.compra = compra
                        detalle.save()
                        Producto.objects.filter(pk=detalle.producto_id).update(
                            stock=detalle.producto.stock + detalle.cantidad
                        )
                compra.recalcular_total()
        if detalles:
            messages.success(request, f"Compra «{compra.numero}» registrada.")
            return redirect("facturacion:compra_detalle", pk=compra.pk)
        formset._non_form_errors.append(forms.ValidationError("Agrega al menos un producto."))
    return render(
        request,
        "facturacion/compra_form.html",
        {
            "form": form,
            "formset": formset,
            "titulo": "Nueva compra",
            "boton": "Registrar",
            "volver_url": reverse("facturacion:compra_lista"),
        },
    )


@login_required
@require_GET
def compra_detalle(request, pk):
    compra = get_object_or_404(
        Compra.objects.select_related("proveedor", "usuario").prefetch_related("detalles__producto"),
        pk=pk,
    )
    return render(
        request,
        "facturacion/compra_detalle.html",
        {"compra": compra, "titulo": str(compra)},
    )


def _guardar_detalles_venta(venta, formset, restaurar_existentes=False):
    productos_existentes = set()
    if restaurar_existentes:
        detalles_anteriores = list(venta.detalles.all())
        productos_existentes = {detalle.producto_id for detalle in detalles_anteriores}
        for detalle in detalles_anteriores:
            Producto.objects.filter(pk=detalle.producto_id).update(
                stock=F("stock") + detalle.cantidad
            )
        venta.detalles.all().delete()

    for form in formset.forms:
        datos = getattr(form, "cleaned_data", {})
        producto_seleccionado = datos.get("producto")
        cantidad = datos.get("cantidad")
        if not producto_seleccionado or not cantidad or datos.get("DELETE"):
            continue

        producto = Producto.objects.select_for_update().get(pk=producto_seleccionado.pk)
        if not producto.activo and producto.pk not in productos_existentes:
            raise ValidationError(f"El producto «{producto.nombre}» ya no está activo.")
        if cantidad > producto.stock:
            raise ValidationError(
                f"Stock insuficiente para «{producto.nombre}». Disponible: {producto.stock}."
            )

        DetalleVenta.objects.create(
            venta=venta,
            producto=producto,
            cantidad=cantidad,
            precio_unitario=producto.precio,
        )
        Producto.objects.filter(pk=producto.pk).update(stock=F("stock") - cantidad)

    venta.recalcular_totales()


@login_required
@require_GET
def venta_lista(request):
    ventas = Venta.objects.select_related("cliente", "registrado_por")
    q = request.GET.get("q", "").strip()
    tipo_pago = request.GET.get("tipo_pago", "")
    if q:
        ventas = ventas.filter(
            Q(cliente__apellidos__icontains=q)
            | Q(cliente__nombres__icontains=q)
            | Q(cliente__cedula__icontains=q)
        )
    opciones_pago = dict(Venta.TipoPago.choices)
    if tipo_pago in opciones_pago:
        ventas = ventas.filter(tipo_pago=tipo_pago)
    pagina = Paginator(ventas, 10).get_page(request.GET.get("page"))
    return render(
        request,
        "facturacion/venta_lista.html",
        {
            "pagina": pagina,
            "ventas": pagina.object_list,
            "q": q,
            "tipo_pago": tipo_pago,
            "opciones_pago": Venta.TipoPago.choices,
            "titulo": "Ventas",
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def venta_crear(request):
    form = VentaForm(request.POST or None)
    formset = VentaDetalleFormSet(request.POST or None, prefix="detalles")
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        try:
            with transaction.atomic():
                venta = form.save(commit=False)
                venta.registrado_por = request.user
                venta.save()
                _guardar_detalles_venta(venta, formset)
        except ValidationError as error:
            formset.forms[0].add_error(None, error.messages[0])
        else:
            messages.success(request, f"Venta #{venta.pk} registrada correctamente.")
            return redirect("facturacion:venta_detalle", pk=venta.pk)
    return render(
        request,
        "facturacion/venta_form.html",
        {
            "form": form,
            "formset": formset,
            "titulo": "Nueva venta",
            "boton": "Guardar venta",
            "volver_url": reverse("facturacion:venta_lista"),
        },
    )


@login_required
@require_GET
def venta_detalle(request, pk):
    venta = get_object_or_404(
        Venta.objects.select_related("cliente", "registrado_por").prefetch_related(
            "detalles__producto"
        ),
        pk=pk,
    )
    return render(
        request,
        "facturacion/venta_detalle.html",
        {"venta": venta, "titulo": f"Factura · Venta #{venta.pk}"},
    )


@login_required
@require_http_methods(["GET", "POST"])
def venta_editar(request, pk):
    venta = get_object_or_404(
        Venta.objects.select_related("cliente").prefetch_related("detalles__producto"),
        pk=pk,
    )
    form = VentaForm(request.POST or None, instance=venta)
    formset = VentaDetalleFormSet(request.POST or None, instance=venta, prefix="detalles")
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        try:
            with transaction.atomic():
                venta = Venta.objects.select_for_update().get(pk=pk)
                venta = form.save(commit=False)
                venta.save()
                _guardar_detalles_venta(venta, formset, restaurar_existentes=True)
        except ValidationError as error:
            formset.forms[0].add_error(None, error.messages[0])
        else:
            messages.success(request, f"Venta #{venta.pk} actualizada correctamente.")
            return redirect("facturacion:venta_detalle", pk=venta.pk)
    return render(
        request,
        "facturacion/venta_form.html",
        {
            "form": form,
            "formset": formset,
            "titulo": f"Editar venta #{venta.pk}",
            "boton": "Guardar cambios",
            "volver_url": reverse("facturacion:venta_detalle", args=[venta.pk]),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def venta_eliminar(request, pk):
    venta = get_object_or_404(
        Venta.objects.select_related("cliente").prefetch_related("detalles__producto"),
        pk=pk,
    )
    if request.method == "POST":
        with transaction.atomic():
            venta = Venta.objects.select_for_update().get(pk=pk)
            detalles = list(venta.detalles.all())
            for detalle in detalles:
                Producto.objects.filter(pk=detalle.producto_id).update(
                    stock=F("stock") + detalle.cantidad
                )
            numero = venta.pk
            venta.delete()
        messages.success(request, f"Venta #{numero} eliminada y productos devueltos al inventario.")
        return redirect("facturacion:venta_lista")
    return render(
        request,
        "facturacion/venta_eliminar.html",
        {"venta": venta, "titulo": f"Eliminar venta #{venta.pk}"},
    )
