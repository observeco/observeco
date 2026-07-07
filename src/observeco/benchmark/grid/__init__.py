"""Grid evaluation: separate model from harness by varying one component at a time.

Models (Axis A): deepseek-v4-flash, deepseek-v4-pro, ornith:latest
Harness configs (Axis B): timeout/retry, tool feedback, context management
Tasks: tau-bench (retail, airline), SWE-bench Verified (subset)
"""
