# Fetch latest objects / values in Django

## Titles

- 5 ways to get the latest record per group in Django

## Notes

Fetch latest object in a queryset:

- Use `latest('field_name')`
- Use `latest()` with `Model.get_latest_by = 'field_name'`
- Use `order_by('-field_name').first()`
- Use `order_by('-field_name')[0]`

Fetch the latest object per group in a queryset:

- Use a subquery

```
latest_browser_client_subquery = (
    models.BrowserClient.objects.filter(user=OuterRef("user"))
    .order_by("-updated_at")
    .values("id")[:1]
)

campaign_users = (
    campaign.users.select_related("user")
    .annotate(latest_browser_client_id=Subquery(latest_browser_client_subquery))
    .order_by("email")
)
```

- In Postgres, use `DISTINCT ON` with `order_by`

```
latest_browser_clients = (
    qs
    .order_by("user", "-updated_at")
    .distinct("user")
)
```

[SQL Query Optimization for Large IN Queries](https://medium.com/@mukul.chaware13/sql-query-optimization-for-large-in-queries-74f58dc524b6)

## ChatGPT Prompts

### Initial Draft

Write a blog post about 5 ways to get the latest record per group in Django

### Discover

Let's say I have the following Django models:

```
class User: base Django User class

class Todo:
    title = models.CharField(max_length=255)
    done = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
```

I want to fetch the latest todo per user.

I know I can do so in Postgres using the following query:

```
Todo.objects.order_by("user", "-updated_at").distinct("user")
```

Give me 3 other ways to do this.
