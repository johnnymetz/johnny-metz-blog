import logging

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connection

from zen_queries import fetch

from core.models import *
from core.tests.factories import *
from mysite.profilers import timer

logger = logging.getLogger(__name__)


# print(User.objects.all().delete())
# for user in UserFactory.create_batch(100):
#     for priority in Todo.Priority:
#         todos = TodoFactory.build_batch(100, user=user, priority=priority)
#         Todo.objects.bulk_create(todos)


def run():
    logger.debug("Done.")
