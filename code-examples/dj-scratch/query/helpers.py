from collections import Counter, deque


def keep_last_instances2(_list):
    result = deque()

    seen = set()
    # for i in range(len(_list) - 1, -1, -1):
    #     x = _list[i]

    for x in reversed(_list):
        if x not in seen:
            seen.add(x)
            result.appendleft(x)

    return list(result)


def keep_last_instances1(_list):
    result = []

    total_counts = Counter(_list)
    current_counts = {}
    for x in _list:
        total_count = total_counts[x]
        current_count = current_counts.get(x, 0) + 1

        if current_count == total_count:
            result.append(x)
        else:
            current_counts[x] = current_count

    return result
