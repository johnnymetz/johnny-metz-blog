import logging
from pprint import pp

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connection

import requests
from zen_queries import fetch

from core.models import *
from core.tests.factories import *
from files.models import *
from mysite.profilers import timer

logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"
user = User.objects.get(username="johnny")
token = user.auth_token.key
print("token", token)

print(File.objects.all().delete())

# Create a file
filename = "masters.jpeg"
response = requests.post(
    f"{BASE_URL}/files/",
    headers={"Authorization": f"Token {token}"},
    json={"filename": filename},
)
response.raise_for_status()
response_data = response.json()
print(response.status_code)
pp(response_data)

# Upload file to S3
with open(f"./{filename}", "rb") as f:
    data = f.read()
response = requests.post(
    url=response_data["upload_url"],
    data=response_data["fields"],
    files={"file": data},
)
response.raise_for_status()
print(response.status_code)

# Mark file as uploaded
response = requests.patch(
    response_data["file"]["download_url"],
    headers={"Authorization": f"Token {token}"},
    json={"is_uploaded": True},
)
response.raise_for_status()
print(response.status_code)


def run():
    logger.debug("Done.")
