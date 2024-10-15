import logging

from django.core.management import call_command
from django.db import connection

from zen_queries import fetch

from core.models import *
from mysite.profilers import timer

logger = logging.getLogger(__name__)


def run():
    logger.debug("Done.")
