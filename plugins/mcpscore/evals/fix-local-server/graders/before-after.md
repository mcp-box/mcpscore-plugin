---
type: llm
weight: 2
---
The workspace holds a FastMCP notes server (`server.py`). The user asked for an mcpscore audit and for safe fixes.

Pass only if the final response shows the mcpscore score before and after the fixes, each as points (`score/max_score`) with a percentage, the after score is not lower, and it lists what it changed in `server.py`.

Fail if it says the audit did not run, or gives no score from an audit.
