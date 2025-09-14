---
title: '7 Heroku Features Every Developer Should Be Using'
date: 2025-09-13T12:00:00-06:00
tags:
  - Heroku
ShowToc: true
cover:
  image: 'covers/heroku.png'
---

Heroku makes hosting simple, but most developers overlook its advanced capabilities. After years of running apps on the platform, I've found several underrated features that speed up your workflow and make your apps more reliable. Here are seven you shouldn't miss.

## 1. Preboot

[Preboot](https://devcenter.heroku.com/articles/preboot) spins up new dynos and starts routing traffic to them before the old ones are terminated. The result is seamless, zero-downtime deployments.

The tricky part is knowing when the cutover is complete, since the Heroku dashboard doesn't show it. Use this command to confirm when the new dynos are live:

```bash
heroku ps:wait -t web
```

One caveat: your database changes must be backward-compatible, or your app can still break mid-deploy. I've written more about safe multi-step database changes [here]({{< relref "posts/multistep-database-changes.md" >}}).

## 2. `HEROKU_APP` CLI Environment Variable

If you use the Heroku CLI, you've probably typed `-a <app>` thousands of times. Save yourself the keystrokes. Set the `HEROKU_APP` environment variable and the CLI will default to that app (see [docs](https://devcenter.heroku.com/articles/using-the-cli#app-commands)).

Add it to your shell config so it's available in every terminal session:

```bash
export HEROKU_APP=my-app-name
```

## 3. Log Runtime Metrics

Turn on [runtime metrics logging](https://devcenter.heroku.com/articles/log-runtime-metrics) to track CPU and memory usage for your dynos. This gives you visibility into performance and lets you catch issues early.

Set up monitors for CPU usage (reported as _dyno load_). See [this help article](https://help.heroku.com/88G3XLA6/what-is-an-acceptable-amount-of-dyno-load) for acceptable ranges by dyno type.

Skip monitoring memory usage logs directly. Instead, rely on Heroku's automatic error codes and create alerts for these:

- [R14 - Memory quota exceeded](https://devcenter.heroku.com/articles/error-codes#r14-memory-quota-exceeded)
- [R15 - Memory quota vastly exceeded](https://devcenter.heroku.com/articles/error-codes#r15-memory-quota-vastly-exceeded)

## 4. Dyno Metadata

Tired of teammates asking what version is live? [Dyno metadata](https://devcenter.heroku.com/articles/dyno-metadata) adds config vars such as the commit hash and release datetime, so you can surface the deployed version right in your app.

## 5. Postgres Forks

[Postgres forks](https://devcenter.heroku.com/articles/heroku-postgres-fork) provide a fast, reliable way to copy your database — perfect for reproducing bugs, testing migrations, or experimenting safely. No risky dumps or restores required.

If you don't need the data to be perfectly up to date, I recommend adding the [`--fast` option](https://devcenter.heroku.com/articles/heroku-postgres-fork#fork-fast-option). It can significantly speed up the creation of the forked database.

## 6. Postgres Followers

[Postgres followers](https://devcenter.heroku.com/articles/heroku-postgres-follower-databases) are read-only copies of your primary database. They're ideal for scaling out read-heavy workloads or offloading analytics/reporting queries. In my experience, followers are typically just a few milliseconds behind their leaders. They're a simple way to improve both performance and availability without adding much complexity.

## 7. Config Vars in JSON

[Config vars](https://devcenter.heroku.com/articles/config-vars) are central to Heroku, and you can export them in JSON (see [docs](https://devcenter.heroku.com/articles/heroku-cli-commands#heroku-config)):

```bash
heroku config --json -a <app>
```

Great for scripting, backups, and syncing configs across environments.

---

Heroku is simple out of the box, but these features are what make it powerful. Use them, and you'll spend less time fighting ops and more time shipping code.
