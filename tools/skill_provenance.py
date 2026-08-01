"""Skill write-origin provenance — ContextVar for distinguishing agent-sediment skill writes from foreground user-directed writes.

The curator only consolidates/prunes skills it autonomously created via the
background self-improvement review fork. Skills a user asks a foreground
agent to write belong to the user and must never be auto-curated.

This module exposes a ContextVar that run_agent.py sets before each tool
loop so tool handlers (e.g. skill_manage create) can check whether they
are executing inside the background-review fork.

The signal piggybacks on AIAgent._memory_write_origin, which is already
set to "background_review" for review-fork instances (see
_spawn_background_review in run_agent.py) and defaults to "assistant_tool"
for normal (foreground) agents.

Usage:
    from tools.skill_provenance import (
        set_current_write_origin,
        reset_current_write_origin,
        get_current_write_origin,
    )

    token = set_current_write_origin("background_review")
    try:
        ...  # tool runs here
    finally:
        reset_current_write_origin(token)

    # inside a tool:
    if get_current_write_origin() == "background_review":
        mark_agent_created(skill_name)
"""

import contextvars
from typing import Optional


_write_origin: contextvars.ContextVar[str] = contextvars.ContextVar(
    "skill_write_origin",
    default="foreground",
)

# The sentinel value the background review fork uses; mirrors
# run_agent.py's AIAgent._memory_write_origin override in
# _spawn_background_review().
BACKGROUND_REVIEW = "background_review"

# Project skills directory override: when set by the background review fork,
# skill_manage creates/updates skills under this project .hermes/skills/ path
# instead of the global ~/.hermes/skills/.
_project_skills_dir: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "project_skills_dir",
    default=None,
)

# Project memory directory override: when set, the memory tool writes the
# "memory" target to <project>/.hermes/memory/MEMORY.md instead of the global
# ~/.hermes/memories/MEMORY.md. Mirrors _project_skills_dir so project-scoped
# knowledge stays in the project (rule: never pollute global dirs).
_project_memory_dir: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "project_memory_dir",
    default=None,
)


def set_current_write_origin(origin: str) -> contextvars.Token[str]:
    """Bind the active write origin to the current context.

    Returns a Token the caller must pass to reset_current_write_origin
    in a finally block.
    """
    return _write_origin.set(origin or "foreground")


def reset_current_write_origin(token: contextvars.Token[str]) -> None:
    """Restore the prior write origin context."""
    _write_origin.reset(token)


def get_current_write_origin() -> str:
    """Return the active write origin.

    Default: "foreground" — any tool call made by a regular (non-review)
    agent, from the CLI, the gateway, cron, or a subagent.

    "background_review" — the self-improvement review fork; only skills
    created under this origin should be marked agent-created for curator
    management.
    """
    return _write_origin.get()


def is_background_review() -> bool:
    """Convenience: True iff the current write origin is the background
    review fork."""
    return get_current_write_origin() == BACKGROUND_REVIEW


def set_project_skills_dir(path: Optional[str]) -> contextvars.Token[Optional[str]]:
    """Override the target directory for skill writes.

    When set, skill_manage create/edit/patch/write_file will write to
    this path (e.g. /path/to/project/.hermes/skills/) instead of the
    global ~/.hermes/skills/.

    Returns a Token for restoring the previous value.
    """
    return _project_skills_dir.set(path)


def reset_project_skills_dir(token: contextvars.Token[Optional[str]]) -> None:
    """Restore the previous project skills directory override."""
    _project_skills_dir.reset(token)


def get_project_skills_dir() -> Optional[str]:
    """Return the current project skills directory override, or None."""
    return _project_skills_dir.get()


def set_project_memory_dir(path: Optional[str]) -> contextvars.Token[Optional[str]]:
    """Override the target directory for memory-tool writes.

    When set, memory(action=..., target="memory") writes to
    <project>/.hermes/memory/MEMORY.md instead of the global
    ~/.hermes/memories/MEMORY.md. The "user" target is NEVER routed to a
    project — user profile always lives globally.

    Returns a Token for restoring the previous value.
    """
    return _project_memory_dir.set(path)


def reset_project_memory_dir(token: contextvars.Token[Optional[str]]) -> None:
    """Restore the previous project memory directory override."""
    _project_memory_dir.reset(token)


def get_project_memory_dir() -> Optional[str]:
    """Return the current project memory directory override, or None."""
    return _project_memory_dir.get()
