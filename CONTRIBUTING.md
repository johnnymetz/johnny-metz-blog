# Contributing

How to contribute to this repository.

```
# initial setup
hugo new site johnny-metz-blog

git submodule add https://github.com/luizdepra/hugo-coder.git themes/hugo-coder
git submodule add https://github.com/uPagge/uBlogger.git themes/uBlogger
git submodule add https://github.com/adityatelange/hugo-PaperMod.git themes/PaperMod --depth=1

# after you clone repo
git submodule update --init --recursive
brew install pre-commit
pre-commit install
```
