import logging

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connection

import requests
from zen_queries import fetch

from core.models import *
from core.tests.factories import *
from mysite.profilers import timer

logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"
user = User.objects.get(username="johnny")
token = user.auth_token.key
TOKEN = "581cbda152d81877130dc1c33738e3d22f6a7765"
assert token == TOKEN

response = requests.post(
    f"{BASE_URL}/files/",
    headers={"Authorization": f"Token {TOKEN}"},
    json={"filename": "dexter.png"},
)
response.raise_for_status()
response_data = response.json()
print(response_data)


def run():
    logger.debug("Done.")
