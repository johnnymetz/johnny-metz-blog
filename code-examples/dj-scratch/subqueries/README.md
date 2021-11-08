# Django ORM Gotcha

```
./manage.py runscript debugger
```

```
docker compose exec db psql -U postgres
```

```
# w/o .values_list("pk", flat=True)
SELECT * FROM "subqueries_book"
WHERE (
	"subqueries_book"."id" IN (
		SELECT DISTINCT ON ("subqueries_book"."name") "subqueries_book"."id"
		FROM "subqueries_book"
		ORDER BY "subqueries_book"."name" ASC, "subqueries_book"."edition" DESC
	)
	AND "subqueries_book"."release_year" IS NOT NULL
)

# w/ .values_list("pk", flat=True)
SELECT * FROM "subqueries_book"
WHERE (
	"subqueries_book"."id" IN (
		SELECT DISTINCT ON (U0."name") U0."id"
		FROM "subqueries_book" U0
		ORDER BY U0."name" ASC, U0."edition" DESC
	)
	AND "subqueries_book"."release_year" IS NOT NULL
)
```

## Understanding psql DISTINCT ON

[Docs](https://www.postgresqltutorial.com/postgresql-select-distinct/)

> Order by name/edition, keep the first row for each group of duplicates, and return id + name columns

```
SELECT DISTINCT ON (name) id, name
FROM subqueries_book
ORDER BY name ASC, edition DESC;
```
