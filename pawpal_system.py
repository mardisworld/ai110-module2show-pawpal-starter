from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional


@dataclass
class Task:
    title: str
    category: str
    duration_minutes: int
    priority: int  # 1..5
    due_date: Optional[datetime] = None
    recurring: bool = False
    status: str = "pending"

    def mark_completed(self) -> None:
        self.status = "completed"

    def reschedule(self, new_due_date: datetime) -> None:
        self.due_date = new_due_date

    def to_display_string(self) -> str:
        return (f"{self.title} [{self.category}] "
                f"{self.duration_minutes}m, priority={self.priority}, status={self.status}")


@dataclass
class Pet:
    name: str
    type: str
    age: int
    feeding_schedule: str = ""
    medication_notes: str = ""
    task_list: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        self.task_list.append(task)

    def remove_task(self, task: Task) -> None:
        self.task_list = [t for t in self.task_list if t is not task]

    def update_care_info(self, feeding_schedule: Optional[str] = None,
                         medication_notes: Optional[str] = None) -> None:
        if feeding_schedule is not None:
            self.feeding_schedule = feeding_schedule
        if medication_notes is not None:
            self.medication_notes = medication_notes


@dataclass
class Owner:
    name: str
    email: str
    available_hours_per_day: float = 0.0
    pets: List[Pet] = field(default_factory=list)
    preferences: Dict[str, str] = field(default_factory=dict)

    def add_pet(self, pet: Pet) -> None:
        self.pets.append(pet)

    def remove_pet(self, pet: Pet) -> None:
        self.pets = [p for p in self.pets if p is not pet]

    def set_preferences(self, preferences: Dict[str, str]) -> None:
        self.preferences.update(preferences)

    def get_all_tasks(self) -> List[Task]:
        tasks: List[Task] = []
        for pet in self.pets:
            tasks.extend(pet.task_list)
        return tasks


@dataclass
class Scheduler:
    owner: Owner
    schedule_date: date = field(default_factory=date.today)
    planned_task_order: List[Task] = field(default_factory=list)

    def generate_daily_plan(self) -> List[Task]:
        candidates = self.fetch_candidates()
        sorted_tasks = sorted(
            candidates,
            key=lambda t: (t.status != "pending", -t.priority, t.due_date or datetime.max)
        )

        remaining_minutes = int(self.owner.available_hours_per_day * 60)
        plan: List[Task] = []

        for task in sorted_tasks:
            if task.status == "completed":
                continue
            if task.duration_minutes <= remaining_minutes:
                plan.append(task)
                remaining_minutes -= task.duration_minutes

        self.planned_task_order = plan
        return plan

    def fetch_candidates(self) -> List[Task]:
        return [t for t in self.owner.get_all_tasks() if t.status != "completed"]

    def score_task(self, task: Task) -> float:
        return float(task.priority)

    def apply_constraints(self,
                          time_available_hours: float,
                          priorities: Optional[List[int]] = None,
                          preferences: Optional[Dict[str, str]] = None) -> None:
        # Placeholder; can incorporate available time, category preferences, and priority filtering.
        if preferences:
            self.owner.set_preferences(preferences)

    def explain_plan(self) -> str:
        if not self.planned_task_order:
            return "No tasks planned yet; run generate_daily_plan()."
        lines = [f"{t.title} ({t.duration_minutes}m)" for t in self.planned_task_order]
        return "Planned tasks: " + ", ".join(lines)



if __name__ == "__main__":
    # Example initialization for manual test
    owner = Owner(name="Alex", email="alex@example.com", available_hours_per_day=3.0)
    pet = Pet(name="Buddy", type="Dog", age=4)
    owner.add_pet(pet)
    task = Task(title="Walk", category="exercise", duration_minutes=30, priority=5)
    pet.add_task(task)

    scheduler = Scheduler(owner=owner)
    print(scheduler.explain_plan())
