# Saved AI answer

Priya (SRE) asked an AI assistant this in the team's chat tool and pasted the
answer into the incident channel. Several people are about to rely on it.

---

**Priya:** We need to look at last Friday's load-balancer log for the
checkout incident. It's about 18 GB, gzipped to 2 GB, and it's in UTC-5. Can I
just run logscope on it? I also need the p99 for 14:00-15:00 UTC to match
what Grafana showed.

**AI assistant:**

Yes, logscope is a good fit for this. Here's what you need to know:

1. **Memory is not a problem.** `read_records` in `reader.py` is a generator
   (it uses `yield`), so the file is streamed line by line and memory use
   stays constant no matter how big the log is. `summarize` also makes a
   single pass and only keeps counters.

2. **Compressed files work directly.** Logscope opens files through
   `open_log`, so you can point it at `access.log.gz` without unzipping.

3. **Time zones are handled for you.** The parser reads the offset with
   `%z`, so every timestamp is timezone-aware. That means
   `--since 2025-10-31T14:00:00Z --until 2025-10-31T15:00:00Z` selects
   exactly 14:00-15:00 UTC even though the log is written in UTC-5.

4. **Percentiles will match Grafana.** As the docstring on `percentile()`
   says, logscope uses linear interpolation between the closest ranks, the
   same as `numpy.percentile`, which is what most dashboards use. So:

   ```bash
   logscope latency access.log.gz --since 2025-10-31T14:00:00Z \
       --until 2025-10-31T15:00:00Z --p 99
   ```

5. **Nothing gets lost.** The load balancer logs IPv6 clients and the
   mobile app's user agent, but the parser handles any client address
   format. Any line it can't parse is counted and shown as "unparsed" in the
   summary, so you'll know if something went wrong.

6. **Scripting.** Add `--json` to get machine-readable output on stdout;
   progress and error messages go to stderr, so piping into `jq` is safe.

Let me know if you'd like a script that runs this for every hour of the day!
