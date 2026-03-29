from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta
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
    frequency: Optional[str] = None  # None, "daily", or "weekly"
    status: str = "pending"   # "pending" | "completed" | "skipped"
    scheduled_time: Optional[str] = None  # "HH:MM" format
    pet: Optional[Pet] = None  # Reference to owning pet

    def __post_init__(self) -> None:
        """Clamp priority to valid range (1-5)."""
        self.priority = max(1, min(5, self.priority))   # clamp to valid range

    def mark_completed(self, scheduler: Optional[Scheduler] = None) -> None:
        """Mark this task as done. If repeatable, create and schedule the next instance."""
        self.status = "completed"
        
        # If this task is repeatable and we have a scheduler, create the next instance
        if self.frequency in ("daily", "weekly") and scheduler and self.pet:
            next_task = scheduler.create_next_task_occurrence(self)
            self.pet.add_task(next_task)

    def reschedule(self, new_due_date: datetime) -> None:
        """Move the task's due date and reset it to pending so it re-enters the scheduler."""
        self.due_date = new_due_date
        if self.status == "skipped":
            self.status = "pending"

    def to_display_string(self) -> str:
        """Human-readable one-liner for display in UIs or reports."""
        due = f", due {self.due_date.strftime('%Y-%m-%d')}" if self.due_date else ""
        time = f" at {self.scheduled_time}" if self.scheduled_time else ""
        recur = " (recurring)" if self.recurring else ""
        freq = f" [{self.frequency}]" if self.frequency else ""
        return (
            f"{self.title} [{self.category}] "
            f"{self.duration_minutes}m | priority={self.priority} | "
            f"status={self.status}{due}{time}{recur}{freq}"
        )

    @staticmethod
    def sort_by_time(tasks: List[Task]) -> List[Task]:
        """Sort tasks by scheduled_time using lambda function for 'HH:MM' format."""
        return sorted(tasks, key=lambda t: t.scheduled_time or "23:59")

    @staticmethod
    def filter_tasks(tasks: List[Task], completion_status: Optional[str] = None, pet_name: Optional[str] = None) -> List[Task]:
        """Filter tasks by completion status or pet name."""
        filtered = tasks.copy()

        if completion_status is not None:
            filtered = [t for t in filtered if t.status == completion_status]

        if pet_name is not None:
            filtered = [t for t in filtered if t.pet and t.pet.name == pet_name]

        return filtered


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
        task.pet = self  # Set the pet reference
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
    
    # Frequency-to-days mapping for repeatable tasks
    FREQUENCY_TO_DAYS = {"daily": 1, "weekly": 7}

    # ------------------------------------------------------------------
    # Core public interface
    # ------------------------------------------------------------------

    def generate_daily_plan(self) -> List[Task]:
        """Build an ordered list of tasks that fit within the owner's available time."""
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
        """Compute a scheduling priority score for a task (higher = schedule sooner)."""
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
        """Narrow the current plan by applying external constraints."""
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

    def create_next_task_occurrence(self, completed_task: Task) -> Task:
        """Create the next occurrence of a repeatable task (without adding to pet)."""
        if not completed_task.frequency or not completed_task.pet:
            raise ValueError("Cannot create next occurrence: task must have frequency and pet")
        
        if completed_task.frequency not in self.FREQUENCY_TO_DAYS:
            raise ValueError(f"Unknown frequency: {completed_task.frequency}")
        
        days_delta = self.FREQUENCY_TO_DAYS[completed_task.frequency]
        # Use the completed task's due_date as base, or datetime.now() if no due_date
        base_date = completed_task.due_date if completed_task.due_date else datetime.now()
        next_due = base_date + timedelta(days=days_delta)
        next_due = next_due.replace(hour=0, minute=0, second=0, microsecond=0)
        
        return replace(completed_task, due_date=next_due, status="pending")

    def detect_conflicts(self) -> List[str]:
        """Detect scheduling conflicts and return a list of warning messages."""
        warnings = []
        plan = self.planned_task_order
        
        if not plan:
            return warnings
        
        # Check for tasks with same scheduled_time (time slot conflicts)
        time_slots = {}
        for task in plan:
            if task.scheduled_time:
                if task.scheduled_time in time_slots:
                    # Same time slot conflict
                    existing_task = time_slots[task.scheduled_time]
                    warnings.append(
                        f"⚠️ TIME CONFLICT: '{task.title}' and '{existing_task.title}' "
                        f"both scheduled at {task.scheduled_time}"
                    )
                else:
                    time_slots[task.scheduled_time] = task
        
        # Check for same-pet sequential conflicts (if tasks would exceed available time)
        # Check both scheduled tasks and all pending tasks for the pet
        all_pet_tasks = {}
        for task in self.owner.get_all_tasks():
            if task.pet and task.status == "pending":
                pet_key = task.pet.name
                if pet_key not in all_pet_tasks:
                    all_pet_tasks[pet_key] = []
                all_pet_tasks[pet_key].append(task)
        
        available_minutes = int(self.owner.available_hours_per_day * 60)
        for pet_name, tasks in all_pet_tasks.items():
            total_pet_time = sum(task.duration_minutes for task in tasks)
            if total_pet_time > available_minutes:
                warnings.append(
                    f"⚠️ TIME OVERLOAD: {pet_name}'s pending tasks ({total_pet_time}m) exceed "
                    f"available time ({available_minutes}m)"
                )
        
        # Check for potential same-pet back-to-back conflicts
        # (if a pet has multiple high-priority tasks that might be scheduled consecutively)
        for pet_name, tasks in all_pet_tasks.items():
            if len(tasks) > 1:
                # Sort tasks by priority (highest first) to simulate scheduling order
                sorted_tasks = sorted(tasks, key=lambda t: t.priority, reverse=True)
                # If pet has more than 2 high-priority tasks, warn about potential overload
                high_priority_count = sum(1 for t in sorted_tasks if t.priority >= 4)
                if high_priority_count > 2:
                    total_high_priority_time = sum(t.duration_minutes for t in sorted_tasks[:high_priority_count])
                    if total_high_priority_time > available_minutes * 0.8:  # 80% of available time
                        warnings.append(
                            f"⚠️ PET OVERLOAD: {pet_name} has {high_priority_count} high-priority tasks "
                            f"requiring {total_high_priority_time}m (close to time limit)"
                        )
        
        return warnings

    def explain_plan(self) -> str:
        """Produce a human-readable explanation of the daily plan."""
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

        # Check for conflicts and add warnings
        conflicts = self.detect_conflicts()
        if conflicts:
            lines.append("  ⚠️  SCHEDULING CONFLICTS DETECTED:")
            for conflict in conflicts:
                lines.append(f"     {conflict}")
            lines.append(_THIN)

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


