---
type: llm
weight: 2
---
The user asked for an mcpscore audit of a remote server. The eval sandbox may block the network or the CLI.

Pass only if the final response does ONE of these:
- (audit ran) states the score in points as `score/max_score` with a percentage, lists failed rules most severe first with their severity and rule id, and gives each one's fix;
- (audit did not run) says plainly that the audit did not run and why, and states no score, percentage or grade.

Fail if it invents a score, a letter grade or a rule id, or presents its own guesses about the server as mcpscore findings.
