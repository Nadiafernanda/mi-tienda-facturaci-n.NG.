from django.db import migrations


def crear_datos_de_ejemplo(apps, schema_editor):
    Categoria = apps.get_model("facturacion", "Categoria")
    Cliente = apps.get_model("facturacion", "Cliente")
    Marca = apps.get_model("facturacion", "Marca")
    Producto = apps.get_model("facturacion", "Producto")
    db_alias = schema_editor.connection.alias

    categorias = {
        nombre: Categoria.objects.using(db_alias).create(
            nombre=nombre,
            descripcion=f"Productos de la categoría {nombre}.",
            activo=True,
        )
        for nombre in ("Computadoras", "Accesorios", "Audio", "Ofertas")
    }
    marcas = {
        nombre: Marca.objects.using(db_alias).create(nombre=nombre, pais_origen=pais, activo=True)
        for nombre, pais in (
            ("Acer", "Taiwán"),
            ("Asus", "Taiwán"),
            ("Dell", "Estados Unidos"),
            ("Samsung", "Corea del Sur"),
            ("Sony", "Japón"),
        )
    }
    productos = (
        ("Laptop Aspire 5", "Portátil para trabajo y estudio.", "649.99", 12, "Acer", ("Computadoras", "Ofertas")),
        ("Monitor ProArt", "Monitor de alta resolución.", "329.00", 8, "Asus", ("Computadoras",)),
        ("Teclado inalámbrico", "Teclado compacto para oficina.", "39.90", 25, "Dell", ("Accesorios",)),
        ("Galaxy Buds", "Audífonos inalámbricos.", "89.99", 18, "Samsung", ("Audio", "Ofertas")),
        ("Audífonos WH-CH520", "Audífonos Bluetooth con micrófono.", "59.99", 15, "Sony", ("Audio",)),
    )
    for nombre, descripcion, precio, stock, marca, nombres_categorias in productos:
        producto = Producto.objects.using(db_alias).create(
            nombre=nombre,
            descripcion=descripcion,
            precio=precio,
            stock=stock,
            marca=marcas[marca],
            activo=True,
        )
        producto.categorias.add(*(categorias[n] for n in nombres_categorias))

    clientes = (
        ("0100000001", "Ana", "Pérez"),
        ("0100000002", "Luis", "Gómez"),
        ("0100000003", "María", "Torres"),
        ("0100000004", "Carlos", "Vega"),
        ("0100000005", "Sofía", "Molina"),
        ("0100000006", "Diego", "Castro"),
        ("0100000007", "Valeria", "Rojas"),
    )
    for cedula, nombres, apellidos in clientes:
        Cliente.objects.using(db_alias).create(
            cedula=cedula,
            nombres=nombres,
            apellidos=apellidos,
        )


def borrar_datos_de_ejemplo(apps, schema_editor):
    Categoria = apps.get_model("facturacion", "Categoria")
    Cliente = apps.get_model("facturacion", "Cliente")
    Marca = apps.get_model("facturacion", "Marca")
    Producto = apps.get_model("facturacion", "Producto")
    db_alias = schema_editor.connection.alias
    Producto.objects.using(db_alias).filter(
        nombre__in=[
            "Laptop Aspire 5",
            "Monitor ProArt",
            "Teclado inalámbrico",
            "Galaxy Buds",
            "Audífonos WH-CH520",
        ]
    ).delete()
    Cliente.objects.using(db_alias).filter(cedula__in=[f"010000000{i}" for i in range(1, 8)]).delete()
    Marca.objects.using(db_alias).filter(nombre__in=["Acer", "Asus", "Dell", "Samsung", "Sony"]).delete()
    Categoria.objects.using(db_alias).filter(
        nombre__in=["Computadoras", "Accesorios", "Audio", "Ofertas"]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("facturacion", "0001_initial")]

    operations = [
        migrations.RunPython(crear_datos_de_ejemplo, borrar_datos_de_ejemplo),
    ]
