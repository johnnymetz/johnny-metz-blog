# CLAUDE.md

Hugo blog (PaperMod theme) at johnnymetz.com. Posts live in `content/posts/*.md`. `demo/` is a Django app with code backing older posts. New posts don't need demo code: verify snippets ad hoc (e.g. a throwaway script in the scratchpad) instead of adding to `demo/`, unless asked.

## Commands

```
make run                 # hugo server with drafts + future posts
hugo new posts/xxx.md    # new post from archetypes/default.md (starts as draft: true)
pre-commit run --all-files
make updatesubmodules    # bump PaperMod theme
```

Demo app: `cd demo`, `docker compose up` (Postgres on 5433), `pytest`. Ruff/mypy config is in `pyproject.toml`.

## Branches and deploys

- `dev` is the default branch and deploys to https://dev.johnnymetz.com (drafts and future posts are built).
- `prod` deploys to https://johnnymetz.com.
- Netlify builds on every push; config is in `netlify.toml`.
- Promote dev to prod by rebasing `prod` onto `dev` (no merge commits), then push `prod`.
- Hugo version is pinned in `netlify.toml` (`HUGO_VERSION`); bump it there.

## Conventions

- Posts use front matter like existing posts: quoted `title`, `date` with offset, `tags`, `ShowToc: true`, `cover.image` under `static/covers/`.
- Don't commit `public/` or `resources/_gen/`; both are build output.
- `themes/PaperMod` is a git submodule. Run `git submodule update --init --recursive` after a fresh clone.
- Post ideas go in `ideas/README.md`.
- Target the latest release of Django, Python, and every other package in posts, doc links, and verification scripts (e.g. a fresh `uv venv` in the scratchpad with the newest Python the package supports), unless told otherwise.
