---
type: llm
weight: 2
---
The workspace holds a FastMCP notes server (`server.py`). The eval sandbox may stop the mcpscore CLI from running.

Pass only if the final response does ONE of these:
- (audit ran) shows the score before and after the fixes as points with percentages, and the after score is not lower;
- (audit did not run) says so plainly, states no score, and says the fixes are unverified by a re-audit.

In both cases it lists what it changed in `server.py`.
