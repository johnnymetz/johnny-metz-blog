# Contributing

How to contribute to this repository.

## Initial setup

```
# initial setup
hugo new site johnny-metz-blog

# add theme
git submodule add https://github.com/adityatelange/hugo-PaperMod.git themes/PaperMod --depth=1

# setup pre-commit
brew install pre-commit
pre-commit install
```

## Common commands

```
# run / build
hugo server --gc -D  # run dev server on http://localhost:1313
hugo -D  # build static pages

# create a new post
hugo new posts/xxx.md

# view/update submodules
git submodule
git submodule update --remote --merge
```

## Resources

- [Hugo Themes Ranked](https://hugoranked.com/)
- [How to effectively delete a git submodule. · GitHub](https://gist.github.com/myusuf3/7f645819ded92bda6677)
