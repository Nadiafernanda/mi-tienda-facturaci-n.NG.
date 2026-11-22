"""
Mixins para las Vistas Basadas en Clases (VBC) de la aplicación Facturación.
Un mixin es una clase con una responsabilidad única diseñada para reutilizarse mediante herencia múltiple.
"""

from django.contrib.auth.mixins import LoginRequiredMixin


class UsuarioRegistroMixin:
    """
    Mixin que asigna de forma automática el usuario autenticado (request.user)
    al campo de auditoría del modelo al guardar el formulario válido.
    
    Compatible tanto con 'user', 'usuario' o 'registrado_por' según el modelo.
    """

    def form_valid(self, form):
        # 1. Asignamos el usuario en sesión al campo correspondiente
        if hasattr(form.instance, "user"):
            form.instance.user = self.request.user
        elif hasattr(form.instance, "usuario"):
            form.instance.usuario = self.request.user
        elif hasattr(form.instance, "registrado_por"):
            form.instance.registrado_por = self.request.user

        # 2. Continuamos la cadena de ejecución de los demás mixins y la vista genérica
        return super().form_valid(form)
