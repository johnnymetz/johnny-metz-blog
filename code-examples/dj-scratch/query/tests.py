from django.db.models import OuterRef, Subquery

import pytest
from pytest_django.asserts import assertQuerysetEqual

from query.helpers import keep_last_instances1, keep_last_instances2
from query.models import Tool, Toolbox


@pytest.mark.django_db()
def test_sort_tools_by_latest_toolbox_name():
    tool1 = Tool.objects.create(name="Tool 1")
    tool2 = Tool.objects.create(name="Tool 2")
    toolbox1_v1 = Toolbox.objects.create(name="A", version=1)
    toolbox1_v1.tools.add(tool1)
    toolbox1_v2 = Toolbox.objects.create(name="Z", version=2)
    toolbox1_v2.tools.add(tool1)
    Toolbox.objects.create(name="B", version=3)  # toolbox1_v3
    toolbox2_v1 = Toolbox.objects.create(name="C", version=1)
    toolbox2_v1.tools.add(tool2)

    tools = Tool.objects.all()
    for tool in tools:
        tool.latest_toolbox = tool.toolboxes.order_by("-version").first()
    tools = sorted(tools, key=lambda x: x.latest_toolbox.name)
    assertQuerysetEqual(tools, [tool2, tool1])

    # https://stackoverflow.com/questions/69114026/django-query-to-sort-by-a-field-on-the-latest-version-of-a-many-to-many-relation
    toolbox_subquery = (
        Toolbox.objects.filter(tools=OuterRef("pk"))
        .order_by("-version")
        .values("name")[:1]
    )
    print(Toolbox.objects.order_by("-version").values("name")[:1])
    # tools = Tool.objects.order_by(Subquery(toolbox_subquery))
    tools = Tool.objects.alias(latest_toolbox_name=Subquery(toolbox_subquery)).order_by(
        "latest_toolbox_name"
    )
    # for tool in tools:
    #     print(tool, tool.latest_toolbox_name)
    assertQuerysetEqual(tools, [tool2, tool1])

    # qs = Tool.objects.order_by("toolboxes__name").distinct()
    # print(qs)
    # sorted_tools = []
    # seen = set()
    # for tool in qs:
    #     if tool not in seen:
    #         seen.add(tool)
    #         sorted_tools.append(tool)
    # # assert sorted_tools == [tool2, tool1]
    # print(sorted_tools)


def test_keep_last_instances():
    start = [1, 2, 3, 1, 3, 4, 5, 3, 2]
    assert keep_last_instances1(start) == [1, 4, 5, 3, 2]
    assert keep_last_instances2(start) == [1, 4, 5, 3, 2]
