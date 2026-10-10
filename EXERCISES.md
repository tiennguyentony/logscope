# Logscope exercises

You are joining the platform team this week. Logscope is the small
command-line tool the team uses to get quick answers from nginx access logs
during incidents. You have never seen this code before. Use AI tools
(Claude, ChatGPT, Copilot, Cursor, anything you like) the way you would at
work.

What we care about is **how** you work with AI, not how fast you finish:

- what context you give the tool,
- whether you check what it tells you before you believe it,
- when you disagree with it,
- and whether you can explain the result in your own words.

Your interviewer will tell you which exercises to do. You probably won't
finish everything. That's expected. Say what you skipped and why.

## Before you start

```bash
git clone https://github.com/tiennguyentony/logscope.git
cd logscope
uv sync                                   # creates .venv, installs pytest and the logscope command
uv run pytest                             # should be green
uv run logscope summary samples/access.log
uv run logscope latency samples/access.log --by-path 5
```

No `uv`? Use plain pip instead:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
logscope summary samples/access.log
```

You need Python 3.11 or newer (`python --version`). Nothing else needs to be
installed: logscope has no runtime dependencies. The sample logs are in
`samples/`.

**Ground rules**

1. Share your screen, including your AI chat window.
2. Keep your AI conversation. At the end, export or copy it into
   `session/ai-transcript.md` (or share a link).
3. For each piece of AI output you use, be ready to say whether you
   **accepted**, **edited** or **rejected** it, and why.
4. You may run anything, add files and change code. Commit to a branch
   named `session/<your-name>`.

---

## Warm-up: explore and explain (10–15 min)

Use AI however you like to understand the codebase. Then write
`session/NOTES.md` answering:

1. In two or three sentences: what does logscope do, and who uses it?
2. You run `logscope summary samples/access.log --status 5xx`. What happens,
   step by step, until the table is printed? Name the files and functions.
   Where is the file read, where are lines parsed, where are they filtered,
   and where are the numbers computed?
3. What happens to a line that doesn't match the expected format?

Then **close the AI window** and walk your interviewer through your notes.

---

# Part 1: When AI gets it wrong

The tasks in this part are areas where AI tools often give confident, wrong
answers: about what the code does, about what the docs say, and about
whether something is a bug at all. Your job is to catch that and **prove**
what's true with a test, a command or a line of code. "The AI said so" is
not proof, and neither is "the README says so".

## 1.1 Support queue (20 min)

Four messages arrived in the team channel this week. For **each** one:

1. Reproduce it (or try to). The sample logs are a good place to start.
2. Decide: **real bug**, **not a bug** (works as designed), or **can't
   reproduce**.
3. Prove your answer with a test or a command. If it's a real bug, leave a
   test that fails now (fixing it is optional unless your interviewer asks).
   If it isn't, write the reply you'd send.

Write your verdicts in `session/tickets.md`.

> **From Sam (SRE on-call)**
>
> Since we turned on browser caching for static files, logscope says our
> error rate went from about 3% to over 20%. Grafana says 4%. Did the
> caching change break something, or is one of the tools wrong?

> **From Lena (product analytics)**
>
> The top-paths table shows `/search` as one row, but people searched for
> dozens of different things. Logscope is throwing away the query strings.
> That's data loss and it makes the report useless for us. Can you fix it?

> **From Marco (backend)**
>
> `logscope latency access.log --p 100` crashes with an `IndexError`. Also,
> I made a tiny test log with 20 requests taking 1 ms, 2 ms, ..., 20 ms and
> p95 came out as 20 ms, which is the slowest request. Is that right?

> **From Ade (SRE)**
>
> `logscope summary samples/access.log` says 2,977 requests.
> `wc -l samples/access.log` says 3,322. Where did the other 345 go?

## 1.2 Incident: the outage window (15 min)

From the postmortem draft for last night's orders-API outage:

> The orders API returned 502/503 for about ten minutes from 07:38 UTC.
> To pull the failing requests I ran
>
> ```
> logscope filter samples/access.log --status 5xx \
>     --since 2025-11-02T07:30:00Z --until 2025-11-02T08:00:00Z
> ```
>
> and got **0 matching requests**, which can't be right: I can see the 502s
> in the file. Then I tried `logscope summary` with the same window to get
> the error rate and it crashed with a traceback.

1. Find the root cause of each problem. Use AI, but don't stop at its first
   answer. Look at the timestamps in the file.
2. **Prove** each one with a failing test.
3. Fix whichever one you think matters more, and say why you chose it.
   Check your fix against the night the clocks went back (01:00–02:00
   local time happens twice in the sample).

## 1.3 Two odd reports from CI (15 min)

We run logscope in two nightly CI jobs. Two complaints:

> **Nightly report job:** We commit `logscope summary --top 10` output to a
> repo every night so we can diff it. The "top IPs" table reorders itself
> almost every night, even on nights we re-ran the job on the *same* file.
> The counts are identical; only the order changes.

> **Static-assets job:** `logscope filter prod.log --path '/static/**/*.css'`
> ran for 40 minutes and was killed by the CI timeout. The same command on
> `samples/access.log` finishes instantly. The prod log is only 300 MB.

For each: is it a real bug? What's the root cause? Prove it (for the second
one, a test that fails by timing out is fine). Explain the fix you'd make,
and whether the AI's first suggestion would have been safe.

## 1.4 Review a saved AI answer (15 min)

A colleague asked an AI assistant whether logscope can handle a big
production log, and pasted the answer into the incident channel. It's in
`review/ai-answer-large-logs.md`. People are about to rely on it.

1. Go through the answer claim by claim. For each claim say **true**,
   **false** or **partly true**, and how you checked (file + function, a
   command you ran, or a test).
2. Write the corrected reply you'd post in the channel, in at most ten
   lines.
3. Pick the false claim with the worst consequence and prove it with a test
   or a measurement.

## 1.5 Make the README true (10 min)

Ask your AI tool to check `README.md` against the code and fix it.

1. Review its edit before accepting it. List every change it made and say
   whether each one is correct.
2. List anything still wrong that it missed, and anything it made worse.
3. How did you decide what's true? Name your sources.

---

# Part 2: Build a new feature with AI

Before your first prompt, write `session/context.md`: what you will tell the
AI about this codebase (conventions, invariants it must respect, things it
should not trust, and your definition of done), plus a short plan. Then use
it. Keep commits small. You will be asked how you verified each part.

## 2.1 Small feature: `--exclude-bots` (15 min)

Add an `--exclude-bots` option to every command.

- Requests from bots and crawlers are left out of the results.
- `summary` says how many requests were excluded (table and `--json`).
- It combines with the other filters (`--since`, `--status`, `--path`).
- Tests cover at least one bot, one real browser, and the combination with
  another filter.
- Ask your interviewer what should count as a bot before you decide.

## 2.2 Medium feature: `logscope spikes` (25 min)

Add a command that finds the minutes where errors spike:

```bash
logscope spikes samples/access.log --factor 3 --window 15 --min-requests 5
```

- Group requests into one-minute buckets.
- For each minute, the baseline is the error rate over the previous
  `--window` minutes (default 15).
- Report a minute as a spike when its error rate is more than `--factor`
  times the baseline (default 3) and it has at least `--min-requests`
  requests (default 5).
- Output: one row per spike minute with the time, requests, errors, error
  rate and baseline. `--json` supported. The shared filters
  (`--since`/`--until`/`--path`) work.
- On `samples/access.log` it should find the orders-API outage, and
  nothing in the quiet hours.
- Tests, including a log that spans the night the clocks go back.

## 2.3 Larger feature: many files and `.gz` (40 min, or design-only in 15 min)

Rotated logs look like `access.log`, `access.log.1`, `access.log.2.gz`, ...
Make every command accept one or more files:

```bash
logscope summary access.log access.log.1 access.log.2.gz
logscope filter /var/log/nginx/access.log* --status 5xx
```

- `.gz` files are read transparently.
- `filter` prints matching lines from all files in time order, even if the
  files are given in any order and come from servers with different UTC
  offsets.
- Memory use must not grow with the size of the files (they can be tens of
  GB). Say how you checked.
- A missing or unreadable file is reported clearly; say what you decided
  should happen to the other files.
- Tests.

**Design-only option:** in `session/design.md`, describe how you would
build it (or a `--follow` mode that keeps reading a log as it grows and
survives log rotation): which modules change, what the data flow is, what
could go wrong, and how you'd test it. Then ask the AI to critique your
design and say which of its points you'd accept.

## 2.4 Teach the next AI (10 min)

Write an `AGENTS.md` (or `CLAUDE.md`) at the repo root, so the next
engineer's AI tool doesn't repeat the mistakes you saw today. Keep it under
40 lines. Only include things that are true and useful.

## 2.5 Pull request description (5 min)

Write the PR description for your branch, for a busy senior engineer who has
five minutes:

- what changed,
- how you verified it (exactly what you ran),
- what you did **not** verify,
- which part of the diff they should review most carefully,
- which parts were AI-written.
