---
title: 'Mastering Code Search with JetBrains Scope'
date: 2023-08-13T12:55:29-04:00
tags:
  - JetBrains
ShowToc: true
draft: true
---

## Background

As software engineers, one of the most crucial skills we develop is the ability to search through code efficiently. Whether it's finding a specific function, understanding how a certain feature is implemented, or tracing a bug, being able to quickly navigate and search within a codebase is essential for productivity. However, many codebases can be complex and sprawling, leading to noisy search results that hinder rather than aid our progress. JetBrains provides a few tools to help you refine your code search and focus on what's important.

## JetBrains Excluded Files

JetBrains IDEs provide a feature that allows you to [mark files and folders as permanently excluded](https://www.jetbrains.com/help/idea/content-roots.html#exclude-files-folders). This is intended for files that you don't care about at all, such external dependency files, caches or generated artifacts (e.g. `package-lock.json`, `node_modules/`, `.mypy_cache/` and Python virtual environments). Excluded files are ignored by code completion, navigation, and inspection and can provide a significant boost in IDE performance.

However, this feature has some downsides:

- Excluded files are never searchable.
- Marking an individual file as excluded is overly complex. You can't just right click on a file and select "Mark as Excluded" like you can for folders.

JetBrains Scope provides a better alternative for files that you care about.

## JetBrains Scope

[JetBrains Scope](https://www.jetbrains.com/help/pycharm/scope.html) allows you to define custom search scopes. A scope is a set of files that you want to include or exclude from certain operations, such as code search, refactoring, navigation, and more. By creating a scope, you can tailor your searches to focus only on specific parts of your project, filtering out irrelevant matches and noise.

### Custom Scope

Let's take some practical examples of how you can create a custom JetBrains Scope to refine your code search.

In my Django projects, I commonly want to search Python application code, excluding unit tests and database migrations. I use the following scope, which I name "Python files excluding tests + migrations", to do so:

```
file:*.py&&!file:*/tests//*&&!file:*/migrations//*
```

Another custom scope that I use religiously is "Python files excluding tests + migrations + virtualenvs":

### Predefined Scope

JetBrains also offers a set of [predefined scopes](https://www.jetbrains.com/help/pycharm/scope.html#predefined) that cover common file patterns.

Some of these scopes need to be managed, which make them ineffective because they need to be kept up-to-date. For example, the "Project Test Files" predefined scope is populated by files marked as a "Test Sources Root". I prefer to use a custom scope for test files.

The scopes that don't need to be managed are useful, such as "Open Files" and "All Changed Files".

<!-- ### Associate File Color with a Scope

For visual learners, you can associate a file color with a scope. This allows you to quickly identify files that match a scope.

https://www.jetbrains.com/help/idea/configuring-scopes-and-file-colors.html#associate-file-color-with-a-scope -->
