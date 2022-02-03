---
title: 'Set Django Model Field Choices in your Frontend the Right Way'
date: 2021-12-01T10:31:13-08:00
tags:
  - Python
  - Django
  - Django Rest Framework
cover:
  image: 'covers/django-drf.png'
---

In Django, you can define a set of [choices](https://docs.djangoproject.com/en/3.2/ref/models/fields/#choices) for any field.
If you're using a SPA frontend, such as React or Vue, then you'll need to access these choices in a form. Let's look at two ways to do this.

As an example, we'll use the following `Device` model:

```python
class Device(models.Model):
    class Size(models.TextChoices):
        SMALL = "S"
        MEDIUM = "M"
        LARGE = "L"

    name = models.CharField(max_length=255)
    size = models.CharField(max_length=255, choices=Size.choices)
```

## Hardcode choices in frontend

The fastest approach is to harcode these choices in the frontend.

```html
<select name="size">
  <option value="S">Small</option>
  <option value="M">Medium</option>
  <option value="L">Large</option>
</select>
```

This breaks the [DRY principle](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself), which isn't ideal. If we want to add a new choice, then we'd have to add it in both the backend and frontend.

## Use an API to send choices to frontend

A better approach is to manage these choices only on the backend and pass them around via an API.

Django Rest Framework, the most popular tool for building API's with Django, makes this very easy using `OPTIONS` requests.

Let's start by building our CRUD endpoints:

```python
# serializers.py
class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = "__all__"

# views.py
class DeviceViewSet(ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer

# urls.py
router = DefaultRouter()
router.register("devices", DeviceViewSet)
urlpatterns = [path("api/", include(router.urls))]
```

Now, make an `OPTIONS` request to the devices list endpoint. I'm using the [httpie](https://httpie.io/cli/) cli tool below, which I enjoy more than curl:

```json
// http OPTIONS http://localhost:8000/api/devices/
{
  "name": "Device List",
  "actions": {
    "POST": {
      ...
      "size": {
        "choices": [
          {"display_name": "Small", "value": "S"},
          {"display_name": "Medium", "value": "M"},
          {"display_name": "Large", "value": "L"}
        ],
        "label": "Size",
        "read_only": false,
        "required": true,
        "type": "choice"
      }
    }
  },
  ...
}
```

See all of our `size` choices listed in a clean and strctured format. Our frontend can fetch these choices on page load and dynamically render them.

DRF builds `OPTIONS` requests for all endpoints out of the box. It includes the `actions` object for `POST` and `PUT` endpoints ([source code](https://github.com/encode/django-rest-framework/blob/335054a5d36b352a58286b303b608b6bf48152f8/rest_framework/metadata.py#L79)). Notice we get the same data for our device instance endpoint:

```json
// http OPTIONS http://localhost:8000/api/devices/1/
{
  "name": "Device Instance",
  "actions": {
    "PUT": {
      "size": {
        "choices": [
          {"display_name": "Small", "value": "S"},
          {"display_name": "Medium", "value": "M"},
          {"display_name": "Large", "value": "L"}
        ]
      }
    }
  },
  ...
}
```

You can also view these `OPTIONS` responses in DRF's browsable API. Just navigate to the target endpoint and click the blue "OPTIONS" button.

![options button](/options-button.png)

Read more about this feature in DRF's [Metadata documentation](https://www.django-rest-framework.org/api-guide/metadata/).
