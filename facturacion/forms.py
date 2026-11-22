from django import forms
from django.contrib.auth.models import User
from django.db.models import Q
from django.forms import BaseInlineFormSet, inlineformset_factory

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


class MarcaForm(forms.ModelForm):
    class Meta:
        model = Marca
        fields = ["nombre", "pais_origen", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"placeholder": "Ej.: Samsung"}),
            "pais_origen": forms.TextInput(attrs={"placeholder": "Ej.: Corea del Sur"}),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        if len(nombre) < 2:
            raise forms.ValidationError("El nombre debe tener al menos 2 letras.")
        return nombre.title()


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            "nombre",
            "descripcion",
            "marca",
            "categorias",
            "precio",
            "stock",
            "activo",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"placeholder": "Ej.: Laptop Pro 14"}),
            "descripcion": forms.Textarea(attrs={"rows": 3}),
            "marca": forms.Select(),
            "categorias": forms.CheckboxSelectMultiple(),
            "precio": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "stock": forms.NumberInput(attrs={"min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["marca"].queryset = Marca.objects.filter(activo=True)
        self.fields["marca"].empty_label = "— Elige una marca —"

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        if len(nombre) < 2:
            raise forms.ValidationError("El nombre debe tener al menos 2 letras.")
        return nombre

    def clean_precio(self):
        precio = self.cleaned_data["precio"]
        if precio <= 0:
            raise forms.ValidationError("El precio debe ser mayor que 0.")
        return precio


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nombre", "descripcion", "activo"]
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3})}

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        if len(nombre) < 3:
            raise forms.ValidationError("El nombre debe tener al menos 3 letras.")
        return nombre.title()


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ["nombre", "ruc", "email", "telefono", "direccion", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"placeholder": "Ej.: Distribuidora Andina"}),
            "ruc": forms.TextInput(attrs={"placeholder": "Ej.: 1790000000001"}),
            "direccion": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        if len(nombre) < 3:
            raise forms.ValidationError("El nombre debe tener al menos 3 letras.")
        return nombre

    def clean_ruc(self):
        ruc = self.cleaned_data["ruc"].strip()
        if not ruc.isdigit():
            raise forms.ValidationError("El RUC debe contener solo números.")
        if len(ruc) not in (10, 13):
            raise forms.ValidationError("El RUC debe tener 10 o 13 dígitos.")
        return ruc


class CompraForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ["numero", "proveedor", "fecha", "observaciones", "estado"]
        widgets = {
            "numero": forms.TextInput(attrs={"placeholder": "Ej.: COMP-0001"}),
            "fecha": forms.DateInput(attrs={"type": "date"}),
            "observaciones": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["proveedor"].queryset = Proveedor.objects.filter(activo=True)
        self.fields["proveedor"].empty_label = "— Elige un proveedor —"


class DetalleCompraForm(forms.ModelForm):
    class Meta:
        model = DetalleCompra
        fields = ["producto", "cantidad", "precio_unitario"]
        widgets = {
            "cantidad": forms.NumberInput(attrs={"min": "1"}),
            "precio_unitario": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def clean_cantidad(self):
        cantidad = self.cleaned_data["cantidad"]
        if cantidad < 1:
            raise forms.ValidationError("La cantidad debe ser al menos 1.")
        return cantidad

    def clean_precio_unitario(self):
        precio = self.cleaned_data["precio_unitario"]
        if precio <= 0:
            raise forms.ValidationError("El precio debe ser mayor que 0.")
        return precio


class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = ["cliente", "fecha", "tipo_pago"]
        widgets = {
            "fecha": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fecha"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["cliente"].empty_label = "— Selecciona un cliente —"


class DetalleVentaForm(forms.ModelForm):
    class Meta:
        model = DetalleVenta
        fields = ["producto", "cantidad"]
        widgets = {"cantidad": forms.NumberInput(attrs={"min": "1"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        productos = Producto.objects.filter(activo=True, stock__gt=0)
        if self.instance.pk and self.instance.producto_id:
            productos = Producto.objects.filter(
                Q(activo=True, stock__gt=0) | Q(pk=self.instance.producto_id)
            )
        self.fields["producto"].queryset = productos.order_by("nombre")
        self.fields["producto"].empty_label = "— Elige un producto —"

    def clean_cantidad(self):
        cantidad = self.cleaned_data["cantidad"]
        if cantidad < 1:
            raise forms.ValidationError("La cantidad debe ser al menos 1.")
        return cantidad


class BaseDetalleVentaFormSet(BaseInlineFormSet):
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


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ["cedula", "nombres", "apellidos", "email", "telefono", "direccion"]
        widgets = {"direccion": forms.Textarea(attrs={"rows": 2})}

    def clean_cedula(self):
        cedula = self.cleaned_data["cedula"].strip()
        if len(cedula) != 10:
            raise forms.ValidationError("La cédula debe tener exactamente 10 dígitos.")
        if not cedula.isdigit():
            raise forms.ValidationError("La cédula debe contener solo números.")
        return cedula


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ["cedula", "telefono", "direccion", "cargo"]
        widgets = {"direccion": forms.Textarea(attrs={"rows": 2})}


class RegistroForm(forms.Form):
    username = forms.CharField(max_length=150, strip=False, label="Nombre de usuario")
    email = forms.EmailField(required=True, label="Correo electrónico")
    password1 = forms.CharField(
        required=True,
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
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
