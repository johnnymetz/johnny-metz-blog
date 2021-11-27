from django.db.utils import IntegrityError

import pytest
from pytest_django.asserts import assertQuerysetEqual

from choices.models import Device


@pytest.mark.django_db()
class TestChoices:
    def test_create_device(self):
        sm_device = Device.objects.create(name="Laptop 1", size=Device.Size.SMALL)
        md_device = Device.objects.create(name="Laptop 2", size=Device.Size.MEDIUM)
        lg_device = Device.objects.create(name="Laptop 3", size=Device.Size.LARGE)
        assertQuerysetEqual(
            Device.objects.all(), [sm_device, md_device, lg_device], ordered=False
        )

    def test_create_device_with_null_size_raises_exception(self):
        with pytest.raises(IntegrityError):
            Device.objects.create(name="Laptop", size=None)

    def test_create_device_with_no_size_defaults_to_empty_string(self):
        device = Device.objects.create(name="Laptop")
        assert device.size == ""

    # def test_xxx(self):
    #     print(Device.Size.choices)
