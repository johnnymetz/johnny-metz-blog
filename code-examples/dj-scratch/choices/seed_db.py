from choices.models import Device


def seed_db():
    print(f"Devices before: {Device.objects.count()}")
    Device.objects.get_or_create(name="Laptop 1", size=Device.Size.SMALL)
    Device.objects.get_or_create(name="Laptop 2", size=Device.Size.MEDIUM)
    Device.objects.get_or_create(name="Laptop 3", size=Device.Size.LARGE)
    print(f"Devices after: {Device.objects.count()}")


seed_db()
