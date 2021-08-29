"""
./manage.py shell_plus < checkmembers/script.py
"""

from django.contrib.auth.models import Group, User

group1 = Group.objects.create(name="Group 1")
group2 = Group.objects.create(name="Group 2")

user1 = User.objects.create_user(username="user1")
user2 = User.objects.create_user(username="user2")
user3 = User.objects.create_user(username="user3")
user4 = User.objects.create_user(username="user4")

user1.groups.add(group1, group2)
user2.groups.add(group1)

print("DONE.")
