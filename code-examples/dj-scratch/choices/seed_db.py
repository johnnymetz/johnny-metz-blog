from choices.models import Device


def seed_db():
    # Device.objects.get_or_create(name="Laptop 1", size=Device.Size.SMALL)
    # Device.objects.get_or_create(name="Laptop 2", size=Device.Size.MEDIUM)
    # Device.objects.get_or_create(name="Laptop 3", size=Device.Size.LARGE)
    Device.objects.get_or_create(name="Laptop", size=Device.Size.LARGE)
    Device.objects.get_or_create(name="iPhone", size=Device.Size.MEDIUM)


print(f"Devices before: {Device.objects.count()}")
seed_db()
# Device.objects.all().delete()
print(f"Devices after: {Device.objects.count()}")
