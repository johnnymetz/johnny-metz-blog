# Django ORM Gotcha

```
docker compose exec db psql -U postgres
```

```
# w/o .values_list("pk", flat=True)
SELECT * FROM "core_book"
WHERE (
	"core_book"."id" IN (
		SELECT DISTINCT ON ("core_book"."name") "core_book"."id"
		FROM "core_book"
		ORDER BY "core_book"."name" ASC, "core_book"."edition" DESC
	)
	AND "core_book"."release_year" IS NOT NULL
)

# w/ .values_list("pk", flat=True)
SELECT * FROM "core_book"
WHERE (
	"core_book"."id" IN (
		SELECT DISTINCT ON (U0."name") U0."id"
		FROM "core_book" U0
		ORDER BY U0."name" ASC, U0."edition" DESC
	)
	AND "core_book"."release_year" IS NOT NULL
)
```

## Understanding psql DISTINCT ON

[Docs](https://www.postgresqltutorial.com/postgresql-select-distinct/)

> Order by name/edition, keep the first row for each group of duplicates, and return id + name columns

```
SELECT DISTINCT ON (name) id, name
FROM core_book
ORDER BY name ASC, edition DESC;
```
