import logging

from django.core.management import call_command
from django.db import connection

from zen_queries import fetch

from core.models import *
from green.models import *
from mysite.profilers import timer

logger = logging.getLogger(__name__)


# qs = Product.objects.all()
# print(qs.query)
# print(qs)

Product.objects.create()


def run():
    logger.debug("Done.")
