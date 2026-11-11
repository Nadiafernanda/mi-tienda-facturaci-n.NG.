from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import (
    CategoriaForm,
    ClienteForm,
    MarcaForm,
    PerfilForm,
    ProductoForm,
    RegistroForm,
)
from .models import Categoria, Cliente, Marca, Perfil, Producto


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
        producto.delete()
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
        cliente.delete()
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
