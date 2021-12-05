# from typing import TypedDict

# from django.db.models import QuerySet

# from django_stubs_ext import WithAnnotations
from zen_queries import queries_disabled

from zen.models import Tool, Toolbox

# NOTE: none of these options raise a mypy error if the incoming queryset is NOT annotated


# no argument type hint but works
@queries_disabled()
def get_toolbox_to_small_tools_mappings(toolboxes) -> dict[Toolbox, list[Tool]]:
    return {toolbox: toolbox.small_tools for toolbox in toolboxes}


# # raises mypy error: Item "Toolbox" of "Union[Any, Toolbox]" has no attribute "small_tools"
# @queries_disabled()
# def get_toolbox_to_small_tools_mappings(
#     toolboxes: QuerySet | list[Toolbox],
# ) -> dict[Toolbox, list[Tool]]:
#     return {toolbox: toolbox.small_tools for toolbox in toolboxes}


# # better error message but mypy still raises an error
# @queries_disabled()
# def get_toolbox_to_small_tools_mappings(
#     toolboxes: QuerySet | list[Toolbox],
# ) -> dict[Toolbox, list[Tool]]:
#     if not toolboxes:
#         return {}
#     if not hasattr(toolboxes[0], "small_tools"):
#         raise AttributeError("Must prefetch small_tools")
#     return {toolbox: toolbox.small_tools for toolbox in toolboxes}


# # works but requires us to make an extra abstract model
# class AnnotatedToolbox(Toolbox):
#     small_tools: list[Tool]
#
#     class Meta:
#         abstract = True
#
#
# @queries_disabled()
# def get_toolbox_to_small_tools_mappings(
#     toolboxes: QuerySet | list[AnnotatedToolbox],
# ) -> dict[Toolbox, list[Tool]]:
#     return {toolbox: toolbox.small_tools for toolbox in toolboxes}


###################
# DJANGO-STUBS
###################

# # good mypy code and works at runtime but doesn't say what the annotated key name is
# @queries_disabled()
# def get_toolbox_to_small_tools_mappings(
#     toolboxes: QuerySet[WithAnnotations[Toolbox]],
# ) -> dict[Toolbox, list[Tool]]:
#     return {toolbox: toolbox.small_tools for toolbox in toolboxes}


# # best mypy code but breaks at runtime
# class AnnotatedToolbox(TypedDict):
#     small_tools: list[Tool]
#
#
# @queries_disabled()
# def get_toolbox_to_small_tools_mappings(
#     toolboxes: QuerySet[WithAnnotations[Toolbox, AnnotatedToolbox]],
# ) -> dict[Toolbox, list[Tool]]:
#     return {toolbox: toolbox.small_tools for toolbox in toolboxes}
