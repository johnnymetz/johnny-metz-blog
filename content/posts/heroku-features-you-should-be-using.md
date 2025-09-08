---
title: "7 Heroku Features You Should Be Using (But Probably Aren't)"
date: 2025-09-08T15:43:29-07:00
tags:
  - Heroku
ShowToc: true
# cover:
#   image: 'covers/heroku.png'
---

I've been running my company's infrastructure on Heroku for the past 4 years. During that time, I've learned that while Heroku makes it easy to deploy with a single `git push`, most developers never take advantage of the platform's deeper features. That's a shame, because a few small tweaks can make deployments smoother, debugging easier, and scaling more professional.

Here are seven underrated Heroku features you should be using.

## 1. Preboot: Zero Downtime Deployments

[Preboot](https://devcenter.heroku.com/articles/preboot) ensures your new dynos boot and start serving traffic before the old ones are terminated. The result: seamless, zero-downtime deployments.

Use this command to check when your new dynos are deployed:

```bash
heroku ps:wait -t web
```

One important caveat: your database changes must be backward-compatible, or your app could still break mid-deploy. I've written more about safe multi-step database changes [here]({{< relref "posts/multistep-database-changes.md" >}}).

## 2. HEROKU_APP Environment Variable

If you work with the Heroku CLI, you've probably typed `-a <app>` thousands of times. Save yourself the keystrokes. Set the `HEROKU_APP` environment variable and the CLI will default to that app (see [docs](https://devcenter.heroku.com/articles/using-the-cli#app-commands)).

I just export it in my `~/.zshrc` (or bash profile), and it's set across all terminal sessions:

```bash
export HEROKU_APP=my-app-name
```

## 3. Log Runtime Metrics

Heroku emits [runtime metrics](https://devcenter.heroku.com/articles/log-runtime-metrics) like CPU load and memory, but they're disabled by default. Enabling them gives you visibility into performance and lets you catch issues before they escalate — for example, sending a Slack notification if CPU load is high.

Bonus: this [guide on monitoring Postgres](https://devcenter.heroku.com/articles/monitoring-heroku-postgres) is a great place to start if you haven't set up database alerts yet.

## 4. Dyno Metadata

[Dyno metadata](https://devcenter.heroku.com/articles/dyno-metadata) injects extra environment variables into each dyno, like the commit hash for the current build and the datetime of the latest release. I've used it to display simple build / release info in my apps.

## 5. Config Vars in JSON

Config vars are Heroku's bread and butter. But did you know you can export them in JSON? See [docs](https://devcenter.heroku.com/articles/heroku-cli-commands#heroku-config).

```bash
heroku config --json -a <app>
```

This is incredibly helpful for scripting and automated workflows—especially when you want to back up, sync, or diff your configuration between environments.

## 6. Postgres Forks

Need to reproduce a bug? Test a migration? Or just try something risky without touching production? [Postgres forks](https://devcenter.heroku.com/articles/heroku-postgres-fork) make it trivial.

In one command, you get a fresh copy of your database to experiment with. No risky dumps or restores required.

If you don't need the data to be perfectly up to date, I recommend adding the [`--fast` option](https://devcenter.heroku.com/articles/heroku-postgres-fork#fork-fast-option). It can significantly speed up creation of the forked database.

## 7. Postgres Followers

A [Postgres follower](https://devcenter.heroku.com/articles/heroku-postgres-follower-databases) is a **read-only** copy of your main database. They continuously stream changes from the leader so the data stays nearly up to date. They're perfect for scaling out read-heavy workloads, running analytics/reporting without hitting production, or having a hot standby ready for failover.

From my experience, followers are typically just a few milliseconds behind their leaders—close enough to feel real-time for most applications. That makes them a powerful tool for performance and availability without adding much complexity.
