---
title: 'Disable a direct push to GitHub main branch'
date: 2022-06-20T10:36:08-08:00
tags:
  - Git
  - GitHub
  - Pre-commit
draft: true
---

On a development team, you never want to push directly to the `main` branch. Instead, you want to require changes to be made through pull requests so they can be properly reviewed by other developers.

Some developers, including myself, occasionally forget to stuff their changes into a branch so I like to have an automated check to prevent this mistake. Here are two methods to block direct pushes to the GitHub main branch.

## Pre-commit hook

The [pre-commit framework](https://pre-commit.com/) includes a [`no-commit-to-branch`](https://github.com/pre-commit/pre-commit-hooks#no-commit-to-branch) hook which blocks direct commits to specific branches. By default, it blocks the `master` and `main` branches.

You can implement this by adding the following `.pre-commit-config.yaml` file to the repository root:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.1.0
    hooks:
      - id: no-commit-to-branch
```

Then run `pre-commit install`. Now commits to `main` will result in an error:

```bash
$ git commit -m "Update again"
don't commit to branch...................................................Failed
- hook id: no-commit-to-branch
- exit code: 1
```

Note, you can work around this check by uninstalling the pre-commit hook so it's not foolproof.

## Branch protection rule

GitHub has [branch protection rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/managing-a-branch-protection-rule) which allow you to enforce workflows for a one or more branches.

To create a branch protection rule, navigate to your repository's settings. Click **Branches** and then **Add rule** under the "Branch protection rules" section.

Enter "main" under **Branch name pattern**. Then check **Require a pull request before merging**.

You'll notice some additional features pop up. I generally check **Require approvals** so developers can't sneak a change through without a proper sign-off.

Lastly, you may want to check **Include administrators** so the rule applies to repository admins. Keep in mind, however, that some git tools, such as [Flux](https://fluxcd.io/), need this access or they won't work. So be cognizant of the tools you're using and the privileges they need.

When you're done, your rule should look like this:

![main branch protection rule](/posts/main-branch-protection-rule.png)

Now direct pushes to `main` will result in an error:

```bash
$ git push
...
remote: error: GH006: Protected branch update failed for refs/heads/main.
remote: error: Changes must be made through a pull request.
To github.com:johnnymetz/my-repo.git
 ! [remote rejected] main -> main (protected branch hook declined)
error: failed to push some refs to 'github.com:johnnymetz/my-repo.git'
```

I prefer the second method because it's foolproof and includes additional features.
