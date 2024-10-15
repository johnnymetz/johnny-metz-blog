# Contributing

How to contribute to this repository.

## Initial setup

```
# setup pre-commit
# install cargo which required for oxipng - https://doc.rust-lang.org/cargo/getting-started/installation.html
brew install pre-commit
pre-commit install

# install theme (pretty sure only the second command is needed)
# https://github.com/adityatelange/hugo-PaperMod/wiki/Installation#method-2
git submodule add https://github.com/adityatelange/hugo-PaperMod.git themes/PaperMod --depth=1
git submodule update --init --recursive # needed when you reclone your repo (submodules may not get cloned automatically)  # .git/modules now exists
```

## Common commands

```
# run / build
make run  # run dev server
hugo -D  # build static pages

# create a new post
hugo new posts/xxx.md

# view/update submodules
git submodule
make updatesubmodules
```

## Resources

- [Hugo Themes Ranked](https://hugoranked.com/)
- [How to effectively delete a git submodule. · GitHub](https://gist.github.com/myusuf3/7f645819ded92bda6677)
