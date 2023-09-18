---
title: 'Mastering Code Search with JetBrains Scope'
date: 2023-08-13T12:55:29-04:00
tags:
  - JetBrains
  - Django
ShowToc: true
draft: true
---

## Background

As software engineers, one of the most crucial skills we develop is the ability to search through code efficiently. Whether it's finding a specific function, understanding how a certain feature is implemented, or tracing a bug, being able to quickly navigate within a codebase is essential for productivity. However, many codebases can be complex and sprawling, leading to noisy search results that hinder rather than aid our progress. JetBrains provides a few tools to help you refine your code search and focus on what's important.

## JetBrains Excluded Files

JetBrains IDEs allow you to [permanently exclude files and folders](https://www.jetbrains.com/help/idea/content-roots.html#exclude-files-folders) from code search and other operations. This cleans up search results and can even significantly boost IDE performance.

Note, marking an individual file as permanently excluded is complicated. You can't just right click on a file and select "Mark as Excluded" like you can for folders. The best way I've found is to open the Project Structure settings and manually add the file to the "Excluded files" input, which is one long string that can become difficult to manage.

This feature is intended for files that you don't care about at all, such external dependency files, caches or generated artifacts (e.g. `venv/`, `node_modules/`, `package-lock.json`). Do not use this feature for files that you want to exclude only some of the time. Instead, use a JetBrains Scope.

## JetBrains Scope

A [JetBrains Scope](https://www.jetbrains.com/help/pycharm/scope.html) is a set of files that you want to temporarily include or exclude from certain operations, such as code search, refactoring, navigation, and more. By creating a scope, you can tailor your searches to focus only on specific parts of your project, filtering out irrelevant matches and noise.

### Custom Scopes

Let's take some practical examples of how you can create a custom JetBrains Scope to refine your code search.

In my Django projects, I commonly want to search Python application code, excluding unit tests and database migrations. Here is the custom scope:

```
file:*.py&&!file:*/tests//*&&!file:*/migrations//*
```

See the [Scopes Settings](https://www.jetbrains.com/help/pycharm/settings-scopes.html) documentation for syntax details and how to create a scope.

Another custom scope that I employ frequently in Django projects includes only model files:

```
file:*/models.py||file:*/models/*.py
```

This allows me to quickly search model definitions, whether they are in a `models.py` file or a `models/` directory.

### Predefined Scopes

JetBrains also offers a set of [predefined scopes](https://www.jetbrains.com/help/pycharm/scope.html#predefined) that cover common file patterns.

Some of these scopes need to be managed, which make them error-prone and ineffective. For example, the "Project Test Files" predefined scope is populated by files marked as a "Test Sources Root". I prefer to use a custom scope for test files in most cases because I just need to write a single rule, rather than manually marking each test directory.

The scopes that don't need to be managed are useful, such as "All Changed Files" and "Open Files".

### Use a Scope in Code Search

In the search dialog, select the "Scope" tab and choose the scope you want to use in the dropdown. We're searching the [Wagtail](https://github.com/wagtail/wagtail) repository below. Notice the number of matches reduces significantly as the scope gets more specific.

{{< mp4-video src="/videos/jetbrains-scope.mp4" >}}

## Conclusion

Use **JetBrains Excluded Files** to permanently exclude files from code search. Use **JetBrains Scope** to exclude files on a per-search basis. May your code searches be fast and fruitful.
