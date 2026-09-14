#!/bin/bash
# Layer 3 of the skill-lesson gate (LOW-120): turn accepted skill lessons
# (layer 2, skill_lesson_filter.py) into a real commit, PR and auto-merge —
# via a worktree off github/main, never the production checkout. Never
# pushes origin (deploy stays a deliberate manual step).
#
# Run AFTER skill_lesson_filter.sh has had time to judge new lessons.
set -uo pipefail
cd "$HOME/content-team" || exit 1
exec venv/bin/python skill_lesson_commit.py
