from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional


@dataclass
class Task:
    """Represents a single pet-care activity."""

    title: str
    category: str
    duration_minutes: int
    priority: int          # 1 (lowest) .. 5 (highest)
    due_date: Optional[datetime] = None
    recurring: bool = False
    status: str = "pending"   # "pending" | "completed" | "skipped"

    def __post_init__(self) -> None:
        self.priority = max(1, min(5, self.priority))   # clamp to valid range

    def mark_completed(self) -> None:
        """Mark this task as done."""
        self.status = "completed"

    def reschedule(self, new_due_date: datetime) -> None:
        """Move the task's due date and reset it to pending so it re-enters the scheduler."""
        self.due_date = new_due_date
        if self.status == "skipped":
            self.status = "pending"

    def to_display_string(self) -> str:
        """Human-readable one-liner for display in UIs or reports."""
        due = f", due {self.due_date.strftime('%Y-%m-%d')}" if self.due_date else ""
        recur = " (recurring)" if self.recurring else ""
        return (
            f"{self.title} [{self.category}] "
            f"{self.duration_minutes}m | priority={self.priority} | "
            f"status={self.status}{due}{recur}"
        )


@dataclass
class Pet:
    """Stores a pet's profile and owns its list of care tasks."""

    name: str
    type: str
    age: int
    feeding_schedule: str = ""
    medication_notes: str = ""
    task_list: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a new task to this pet."""
        self.task_list.append(task)

    def remove_task(self, task: Task) -> None:
        """Detach a task from this pet (matched by identity, not value)."""
        self.task_list = [t for t in self.task_list if t is not task]

    def update_care_info(
        self,
        feeding_schedule: Optional[str] = None,
        medication_notes: Optional[str] = None,
    ) -> None:
        """Update feeding or medication details without overwriting fields left as None."""
        if feeding_schedule is not None:
            self.feeding_schedule = feeding_schedule
        if medication_notes is not None:
            self.medication_notes = medication_notes


@dataclass
class Owner:
    """Manages a collection of pets and exposes a unified view of all their tasks."""

    name: str
    email: str
    available_hours_per_day: float = 0.0
    pets: List[Pet] = field(default_factory=list)
    preferences: Dict[str, str] = field(default_factory=dict)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        self.pets.append(pet)

    def remove_pet(self, pet: Pet) -> None:
        """Unregister a pet (matched by identity)."""
        self.pets = [p for p in self.pets if p is not pet]

    def set_preferences(self, preferences: Dict[str, str]) -> None:
        """Merge new key-value preferences into the owner's existing preferences."""
        self.preferences.update(preferences)

    def get_all_tasks(self) -> List[Task]:
        """Return a flat list of every task across all pets."""
        tasks: List[Task] = []
        for pet in self.pets:
            tasks.extend(pet.task_list)
        return tasks


@dataclass
class Scheduler:
    """The scheduling brain: retrieves pending tasks, scores them, and builds a daily plan."""

    owner: Owner
    schedule_date: date = field(default_factory=date.today)
    planned_task_order: List[Task] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Core public interface
    # ------------------------------------------------------------------

    def generate_daily_plan(self) -> List[Task]:
        """
        Build an ordered list of tasks that fit within the owner's available time.

        Tasks are ranked by score (see score_task), then greedily packed into the
        available minutes.  The result is stored in planned_task_order.
        """
        candidates = self.fetch_pending_tasks()
        ranked = sorted(candidates, key=self.score_task, reverse=True)

        remaining_minutes = int(self.owner.available_hours_per_day * 60)
        plan: List[Task] = []

        for task in ranked:
            if task.duration_minutes <= remaining_minutes:
                plan.append(task)
                remaining_minutes -= task.duration_minutes

        self.planned_task_order = plan
        return plan

    def fetch_pending_tasks(self) -> List[Task]:
        """Return all tasks across all pets that have not yet been completed."""
        return [t for t in self.owner.get_all_tasks() if t.status == "pending"]

    def score_task(self, task: Task) -> float:
        """
        Compute a scheduling priority score for a task (higher = schedule sooner).

        Base score: task.priority (1–5).
        Urgency bonuses based on due_date relative to schedule_date:
          • Overdue          → +5
          • Due today        → +3
          • Due within 3 days → +1
          • No due date      →  0
        """
        score = float(task.priority)

        if task.due_date is not None:
            due = task.due_date.date() if isinstance(task.due_date, datetime) else task.due_date
            days_until_due = (due - self.schedule_date).days
            if days_until_due < 0:
                score += 5.0    # overdue — highest urgency
            elif days_until_due == 0:
                score += 3.0    # due today
            elif days_until_due <= 3:
                score += 1.0    # coming up soon

        return score

    def apply_constraints(
        self,
        time_available_hours: float,
        priorities: Optional[List[int]] = None,
        preferences: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Narrow the current plan by applying external constraints.

        • time_available_hours: overrides the owner's available time and regenerates
          the plan so the result actually reflects the new limit.
        • priorities: if provided, keeps only tasks whose priority is in this list.
        • preferences: merged into owner.preferences for future use.
        """
        self.owner.available_hours_per_day = time_available_hours

        if preferences:
            self.owner.set_preferences(preferences)

        all_candidates = self.fetch_pending_tasks()
        remaining_minutes = int(self.owner.available_hours_per_day * 60)
        plan: List[Task] = []

        if priorities:
            # Pass 1: schedule preferred-priority tasks first.
            preferred = sorted(
                [t for t in all_candidates if t.priority in priorities],
                key=self.score_task, reverse=True,
            )
            for task in preferred:
                if task.duration_minutes <= remaining_minutes:
                    plan.append(task)
                    remaining_minutes -= task.duration_minutes

            # Pass 2: fill any remaining time with lower-priority tasks.
            fillers = sorted(
                [t for t in all_candidates if t.priority not in priorities],
                key=self.score_task, reverse=True,
            )
            for task in fillers:
                if task.duration_minutes <= remaining_minutes:
                    plan.append(task)
                    remaining_minutes -= task.duration_minutes
        else:
            # No priority constraint — single greedy pass over all candidates.
            ranked = sorted(all_candidates, key=self.score_task, reverse=True)
            for task in ranked:
                if task.duration_minutes <= remaining_minutes:
                    plan.append(task)
                    remaining_minutes -= task.duration_minutes

        self.planned_task_order = plan

    def explain_plan(self) -> str:
        """
        Produce a human-readable explanation of the daily plan.

        For each scheduled task, states why it was chosen (score, urgency).
        Also reports tasks that were fetched but did not fit in the schedule.
        """
        _THICK = "═" * 70
        _THIN  = "─" * 70
        _COL   = f"  {'TASK':<22} {'CATEGORY':<11} {'TIME':>4}  {'SCORE':>5}  REASON"

        available_minutes = int(self.owner.available_hours_per_day * 60)
        scheduled_minutes = sum(t.duration_minutes for t in self.planned_task_order)
        remaining_minutes = available_minutes - scheduled_minutes

        def _reason(t: Task) -> str:
            parts: List[str] = [f"priority {t.priority}"]
            if t.due_date is not None:
                due = t.due_date.date() if isinstance(t.due_date, datetime) else t.due_date
                days = (due - self.schedule_date).days
                if days < 0:
                    parts.append(f"OVERDUE {-days}d")
                elif days == 0:
                    parts.append("due TODAY")
                elif days <= 3:
                    parts.append(f"due in {days}d")
            return ", ".join(parts)

        def _row(t: Task) -> str:
            return (
                f"  {t.title:<22} {t.category:<11} {t.duration_minutes:>3}m"
                f"  {self.score_task(t):>5.1f}  {_reason(t)}"
            )

        lines = [
            _THICK,
            f"  Plan for {self.owner.name}  ·  {self.schedule_date}"
            f"  ·  {scheduled_minutes}m of {available_minutes}m  ·  {remaining_minutes}m unused",
            _THICK,
        ]

        if self.planned_task_order:
            lines += ["  SCHEDULED", _THIN, _COL, _THIN]
            lines += [_row(t) for t in self.planned_task_order]
        else:
            lines.append("  SCHEDULED  (none — no pending tasks or available time is 0)")

        all_pending = self.fetch_pending_tasks()
        skipped = [t for t in all_pending if t not in self.planned_task_order]

        lines.append(_THIN)
        if skipped:
            lines += [
                f"  NOT SCHEDULED  ({remaining_minutes}m remaining — tasks below did not fit)",
                _THIN, _COL, _THIN,
            ]
            lines += [_row(t) for t in skipped]
        else:
            lines.append(f"  NOT SCHEDULED  (all tasks fit within {available_minutes}m)")

        lines.append(_THICK)
        return "\n".join(lines)


