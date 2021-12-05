from django.core.exceptions import ValidationError

import pytest
from pytest_django.asserts import assertQuerysetEqual
from rest_framework import status

from choices.models import Device


@pytest.mark.django_db()
class TestDeviceModel:
    def test_create_device(self):
        sm_device = Device.objects.create(name="Laptop 1", size=Device.Size.SMALL)
        md_device = Device.objects.create(name="Laptop 2", size=Device.Size.MEDIUM)
        lg_device = Device.objects.create(name="Laptop 3", size=Device.Size.LARGE)
        assertQuerysetEqual(
            Device.objects.all(), [sm_device, md_device, lg_device], ordered=False
        )

    def test_create_device_with_no_size_raises_exception(self):
        with pytest.raises(ValidationError):
            Device.objects.create(name="Laptop")

    def test_create_device_with_null_size_raises_exception(self):
        with pytest.raises(ValidationError):
            Device.objects.create(name="Laptop", size=None)

    def test_create_device_with_invalid_size_raises_exception(self):
        with pytest.raises(ValidationError):
            Device.objects.create(name="Laptop", size="xxx")


class TestViews:
    def test_options_view(self, client):
        r = client.options("/api/devices/")
        assert r.status_code == status.HTTP_200_OK
        data = r.data
        assert data["name"] == "Device List"
        keys = data["actions"]["POST"].keys()
        assert "name" in keys
        assert "size" in keys
