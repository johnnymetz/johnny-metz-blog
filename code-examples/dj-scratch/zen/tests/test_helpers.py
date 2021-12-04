from django.db import connection, reset_queries
from django.db.models import Exists, OuterRef, Prefetch

import pytest
from pytest_django.asserts import assertQuerysetEqual
from zen.helpers import get_toolbox_to_small_tools_mappings
from zen.models import Tool, Toolbox
from zen_queries import fetch


@pytest.mark.django_db()
def test_x():
    toolbox1 = Toolbox.objects.create(name="Toolbox 1")
    toolbox2 = Toolbox.objects.create(name="Toolbox 2")
    toolbox3 = Toolbox.objects.create(name="Toolbox 3")

    hammer_sm = Tool.objects.create(name="Hammer", size=Tool.Size.SMALL)
    hammer_md = Tool.objects.create(name="Hammer", size=Tool.Size.MEDIUM)
    wrench_sm = Tool.objects.create(name="Wrench", size=Tool.Size.SMALL)
    wrench_lg = Tool.objects.create(name="Wrench", size=Tool.Size.LARGE)

    toolbox1.tools.add(hammer_sm, wrench_sm)
    toolbox2.tools.add(hammer_md, wrench_sm, wrench_lg)
    toolbox3.tools.add(hammer_md, wrench_lg)

    expected_result = {
        toolbox1: [hammer_sm, wrench_sm],
        toolbox2: [wrench_sm],
        toolbox3: [],
    }

    # sanity check
    assertQuerysetEqual(
        hammer_md.toolbox_set.all(), [toolbox2, toolbox3], ordered=False
    )

    # BLOCK: bulk fetch only tools
    reset_queries()
    toolboxes_with_small_tools = Toolbox.objects.filter(
        Exists(Tool.objects.filter(size=Tool.Size.SMALL, toolbox=OuterRef("pk")))
    )
    assertQuerysetEqual(toolboxes_with_small_tools, [toolbox1, toolbox2], ordered=False)
    assert len(connection.queries) == 1

    # BLOCK: prefetch and override tools field
    reset_queries()
    toolbox_to_small_tools_mappings = {}
    toolboxes = fetch(
        Toolbox.objects.prefetch_related(
            Prefetch("tools", queryset=Tool.objects.filter(size=Tool.Size.SMALL))
        )
    )
    for toolbox in toolboxes:
        # prefetch overrides toolbox.tools based on filter
        # do NOT do toolbox.tools.filter(size=Tool.Size.SMALL) b/c it doesn't use the prefetch
        toolbox_to_small_tools_mappings[toolbox] = list(toolbox.tools.all())
    assert toolbox_to_small_tools_mappings == expected_result
    assert len(connection.queries) == 2

    # BLOCK: same as above but separate func
    toolboxes = fetch(
        Toolbox.objects.prefetch_related(
            Prefetch(
                "tools",
                queryset=Tool.objects.filter(size=Tool.Size.SMALL),
                to_attr="small_tools",
            )
        )
    )
    toolbox_to_small_tools_mappings = get_toolbox_to_small_tools_mappings(toolboxes)
    assert toolbox_to_small_tools_mappings == expected_result

    with pytest.raises(AttributeError):
        get_toolbox_to_small_tools_mappings(fetch(Toolbox.objects.all()))
