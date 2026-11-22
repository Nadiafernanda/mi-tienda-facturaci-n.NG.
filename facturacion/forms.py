from django import forms
from django.contrib.auth.models import User
from django.db.models import Q
from django.forms import BaseInlineFormSet, inlineformset_factory

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


class MarcaForm(forms.ModelForm):
    """Formulario para creación y edición de Marcas."""
    class Meta:
        model = Marca
        fields = ["nombre", "pais_origen", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej.: Samsung"}),
            "pais_origen": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej.: Corea del Sur"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        if len(nombre) < 2:
            raise forms.ValidationError("El nombre debe tener al menos 2 letras.")
        return nombre.title()


class CategoriaForm(forms.ModelForm):
    """Formulario para creación y edición de Categorías."""
    class Meta:
        model = Categoria
        fields = ["nombre", "descripcion", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej.: Electrónica"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        if len(nombre) < 3:
            raise forms.ValidationError("El nombre debe tener al menos 3 letras.")
        return nombre.title()


class ProductoForm(forms.ModelForm):
    """Formulario para Producto con soporte para carga de imagen."""
    class Meta:
        model = Producto
        fields = [
            "nombre",
            "descripcion",
            "marca",
            "categorias",
            "precio",
            "stock",
            "imagen",
            "activo",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej.: Laptop Pro 14"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "marca": forms.Select(attrs={"class": "form-select"}),
            "categorias": forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
            "precio": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "stock": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "imagen": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["marca"].queryset = Marca.objects.filter(activo=True)
        self.fields["marca"].empty_label = "— Elige una marca —"

    def clean_precio(self):
        precio = self.cleaned_data["precio"]
        if precio <= 0:
            raise forms.ValidationError("El precio debe ser mayor que 0.")
        return precio


class ClienteForm(forms.ModelForm):
    """Formulario para Cliente con validación estricta de cédula (10 dígitos)."""
    class Meta:
        model = Cliente
        fields = ["cedula", "nombres", "apellidos", "email", "telefono", "direccion"]
        widgets = {
            "cedula": forms.TextInput(attrs={"class": "form-control", "placeholder": "10 dígitos numéricos"}),
            "nombres": forms.TextInput(attrs={"class": "form-control"}),
            "apellidos": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "direccion": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def clean_cedula(self):
        cedula = self.cleaned_data["cedula"].strip()
        if len(cedula) != 10:
            raise forms.ValidationError("La cédula debe tener exactamente 10 dígitos.")
        if not cedula.isdigit():
            raise forms.ValidationError("La cédula debe contener solo números.")
        return cedula


class ProveedorForm(forms.ModelForm):
    """Formulario para Proveedor con validación de RUC ecuatoriano y logo."""
    class Meta:
        model = Proveedor
        fields = ["nombre", "ruc", "email", "telefono", "direccion", "logo", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej.: Distribuidora Andina"}),
            "ruc": forms.TextInput(attrs={"class": "form-control", "placeholder": "13 dígitos terminados en 001"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "direccion": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "logo": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_ruc(self):
        ruc = self.cleaned_data["ruc"].strip()
        if not ruc.isdigit():
            raise forms.ValidationError("El RUC debe contener solo números.")
        if len(ruc) != 13:
            raise forms.ValidationError("El RUC debe tener exactamente 13 dígitos.")
        if not ruc.endswith("001"):
            raise forms.ValidationError("El RUC debe terminar en 001.")
        return ruc


class CompraForm(forms.ModelForm):
    """Cabecera del maestro-detalle de Compra."""
    class Meta:
        model = Compra
        fields = ["numero", "proveedor", "fecha", "observaciones", "estado"]
        widgets = {
            "numero": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej.: COMP-0001"}),
            "proveedor": forms.Select(attrs={"class": "form-select"}),
            "fecha": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "estado": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["proveedor"].queryset = Proveedor.objects.filter(activo=True)
        self.fields["proveedor"].empty_label = "— Elige un proveedor —"


class DetalleCompraForm(forms.ModelForm):
    """Línea de detalle para compras."""
    class Meta:
        model = DetalleCompra
        fields = ["producto", "cantidad", "precio_unitario"]
        widgets = {
            "producto": forms.Select(attrs={"class": "form-select"}),
            "cantidad": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "precio_unitario": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
        }

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get("cantidad")
        if cantidad and cantidad < 1:
            raise forms.ValidationError("La cantidad debe ser al menos 1.")
        return cantidad

    def clean_precio_unitario(self):
        precio = self.cleaned_data.get("precio_unitario")
        if precio and precio <= 0:
            raise forms.ValidationError("El precio unitario debe ser mayor que 0.")
        return precio


DetalleCompraFormSet = inlineformset_factory(
    Compra,
    DetalleCompra,
    form=DetalleCompraForm,
    fields=["producto", "cantidad", "precio_unitario"],
    extra=1,
    can_delete=True,
)


class VentaForm(forms.ModelForm):
    """Cabecera de la factura de Venta."""
    class Meta:
        model = Venta
        fields = ["cliente", "fecha", "tipo_pago"]
        widgets = {
            "cliente": forms.Select(attrs={"class": "form-select"}),
            "fecha": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "tipo_pago": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fecha"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["cliente"].empty_label = "— Selecciona un cliente —"


class DetalleVentaForm(forms.ModelForm):
    """Línea de detalle para ventas."""
    class Meta:
        model = DetalleVenta
        fields = ["producto", "cantidad"]
        widgets = {
            "producto": forms.Select(attrs={"class": "form-select"}),
            "cantidad": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        productos = Producto.objects.filter(activo=True)
        self.fields["producto"].queryset = productos.order_by("nombre")
        self.fields["producto"].empty_label = "— Elige un producto —"

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get("cantidad")
        if cantidad and cantidad < 1:
            raise forms.ValidationError("La cantidad debe ser al menos 1.")
        return cantidad


class BaseDetalleVentaFormSet(BaseInlineFormSet):
    """Validación del conjunto de filas de venta: unicidad de producto y stock."""
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        productos = []
        cantidades = {}
        for form in self.forms:
            datos = getattr(form, "cleaned_data", {})
            producto = datos.get("producto")
            cantidad = datos.get("cantidad")
            if not producto or not cantidad or datos.get("DELETE"):
                continue
            productos.append(producto)
            cantidades[producto.pk] = cantidades.get(producto.pk, 0) + cantidad

        if not productos:
            raise forms.ValidationError("Agrega al menos un producto a la venta.")
        if len({producto.pk for producto in productos}) != len(productos):
            raise forms.ValidationError("Agrega cada producto una sola vez y ajusta la cantidad.")

        cantidades_anteriores = {}
        if self.instance.pk:
            cantidades_anteriores = dict(
                self.instance.detalles.values_list("producto_id", "cantidad")
            )
        for producto in productos:
            disponible = producto.stock + cantidades_anteriores.get(producto.pk, 0)
            if cantidades[producto.pk] > disponible:
                raise forms.ValidationError(
                    f"Stock insuficiente para «{producto.nombre}». Disponible: {disponible}."
                )


VentaDetalleFormSet = inlineformset_factory(
    Venta,
    DetalleVenta,
    form=DetalleVentaForm,
    formset=BaseDetalleVentaFormSet,
    extra=1,
    can_delete=True,
)


class PerfilForm(forms.ModelForm):
    """Formulario para el perfil del usuario."""
    class Meta:
        model = Perfil
        fields = ["cedula", "telefono", "direccion", "cargo"]
        widgets = {
            "cedula": forms.TextInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "direccion": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "cargo": forms.TextInput(attrs={"class": "form-control"}),
        }


class RegistroForm(forms.Form):
    username = forms.CharField(max_length=150, strip=False, label="Nombre de usuario", widget=forms.TextInput(attrs={"class": "form-control"}))
    email = forms.EmailField(required=True, label="Correo electrónico", widget=forms.EmailInput(attrs={"class": "form-control"}))
    password1 = forms.CharField(
        required=True,
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Ese nombre de usuario ya está registrado.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Las contraseñas no coinciden.")
        return cleaned_data

    def save(self, commit=True):
        if self.errors:
            raise ValueError("No se puede guardar el formulario con errores.")
        user = User(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["email"],
        )
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user
