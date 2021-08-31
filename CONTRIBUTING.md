# Contributing

How to contribute to this repository.

```
# initial setup
hugo new site johnny-metz-blog

git submodule add https://github.com/adityatelange/hugo-PaperMod.git themes/PaperMod --depth=1
git submodule add https://github.com/luizdepra/hugo-coder.git themes/hugo-coder

# after you clone repo
git submodule update --init --recursive
brew install pre-commit
pre-commit install
```

[How effectively delete a git submodule. · GitHub](https://gist.github.com/myusuf3/7f645819ded92bda6677)
