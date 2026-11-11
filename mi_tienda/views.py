from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from facturacion.models import Producto


@require_http_methods(["GET", "POST"])
def home(request):
    nombre = ""
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
    productos = Producto.objects.filter(activo=True).select_related("marca")[:4]
    return render(
        request,
        "home.html",
        {
            "titulo": "Mi Tienda",
            "nombre": nombre,
            "productos": productos,
        },
    )
