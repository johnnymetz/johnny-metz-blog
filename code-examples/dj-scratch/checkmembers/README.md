# Check membership

2 queries when using prefetch.

```
SELECT * FROM "auth_user;
SELECT ("auth_user_groups"."user_id") AS "_prefetch_related_val_user_id", "auth_group"."id", "auth_group"."name" FROM "auth_group" INNER JOIN "auth_user_groups" ON ("auth_group"."id" = "auth_user_groups"."group_id") WHERE "auth_user_groups"."user_id" IN (1, 2, 3, 4);
```

Using `manyfield__isnull` will return duplicate instances because we're fetching from the M2M table.

```
# users = User.objects.filter(groups__isnull=False)
SELECT *
FROM "auth_user"
INNER JOIN "auth_user_groups" ON ("auth_user"."id" = "auth_user_groups"."user_id")
WHERE "auth_user_groups"."group_id" IS NOT NULL;
```

Using the Exists directly in the querset is better.

```
# User.objects.annotate(has_group=Exists(groups)).filter(has_group=True)
SELECT "auth_user"."id", EXISTS(
	SELECT (1) AS "a" FROM "auth_group" U0 INNER JOIN "auth_user_groups" U1 ON (U0."id" = U1."group_id") WHERE U1."user_id" = "auth_user"."id" LIMIT 1
) AS "has_group"
FROM "auth_user"
WHERE EXISTS(
	SELECT (1) AS "a" FROM "auth_group" U0 INNER JOIN "auth_user_groups" U1 ON (U0."id" = U1."group_id") WHERE U1."user_id" = "auth_user"."id" LIMIT 1
);

# User.objects.filter(Exists(groups))
SELECT "auth_user"."id"
FROM "auth_user"
WHERE EXISTS(
	SELECT (1) AS "a" FROM "auth_group" U0 INNER JOIN "auth_user_groups" U1 ON (U0."id" = U1."group_id") WHERE U1."user_id" = "auth_user"."id" LIMIT 1
);
```
