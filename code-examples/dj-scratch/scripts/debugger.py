import logging

from django.core.management import call_command
from django.db import connection

from zen_queries import fetch

from mysite.profilers import timer

logger = logging.getLogger(__name__)


with connection.cursor() as cursor:
    cursor.execute("select pg_sleep(3)")


def run():
    logger.debug("Done.")
