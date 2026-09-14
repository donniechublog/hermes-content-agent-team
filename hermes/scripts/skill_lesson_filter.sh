#!/bin/bash
# Layer 2 of the skill-lesson gate (LOW-119): judge the staged skill writes of
# both brand homes and send the flagged ones to the boss (topic ada).
#
# Runs in BOTH containers. The lock and verdict files in state/skill_lessons/
# keep it to one Telegram message per staged record. Exits non-zero when the
# Telegram send fails, so hermes counts the failure and the next run retries.
set -uo pipefail
cd "$HOME/content-team" || exit 1
exec venv/bin/python skill_lesson_filter.py
