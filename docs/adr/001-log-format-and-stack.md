# ADR-001: One log format, standard library only

**Status:** Accepted (supersedes the original multi-format, Click-based design)

## Context

The first version of logscope was built on Click, auto-detected Apache,
nginx and JSON-lines logs, and was going to be published to PyPI. In
practice:

- every server we run is nginx with the same `log_format`; nobody ever ran
  it on Apache or JSON logs, and format detection caused more confusing
  results than it saved typing;
- people run logscope on production boxes and in CI images where installing
  third-party packages is a hassle;
- we never published it. The name `logscope` on PyPI belongs to an
  unrelated project.

## Decision

- Support exactly one format: nginx `combined`, optionally followed by
  `$request_time`:

  ```nginx
  log_format timed '$remote_addr - $remote_user [$time_local] '
                   '"$request" $status $body_bytes_sent '
                   '"$http_referer" "$http_user_agent" $request_time';
  ```

  Lines from before `$request_time` was added still parse; their latency is
  unknown (`None`). A double quote inside a quoted field is written as `\"`.
- Runtime dependencies: none. `argparse` for the CLI, `re` for parsing.
  pytest is the only dev dependency.
- Install from the git repository (`uv sync`, or `pip install -e .`), which
  provides the `logscope` console script. Not published to PyPI.
- The Elasticsearch exporter and the `export` command were dropped. Teams
  that want logs in Elasticsearch already ship them with Filebeat.

## Consequences

- `uv sync && uv run pytest` works on any machine with Python 3.11+.
- Adding another format later means a second parser behind the same
  `LogRecord`, not changes to the commands.
- Anything that isn't a valid line in this format can't be analysed. Users
  need to be able to see how much of their file that was.
