from datetime import datetime

from pawpal_system import Owner, Pet, Scheduler, Task

_WIDTH = 66   # inner width of the box


def _row(text: str = "") -> str:
    return f"│  {text:<{_WIDTH - 2}}│"


def _priority_bar(priority: int) -> str:
    return "●" * priority + "○" * (5 - priority)


def _due_label(task: Task, schedule_date) -> str:
    if task.due_date is None:
        return ""
    due = task.due_date.date() if isinstance(task.due_date, datetime) else task.due_date
    days = (due - schedule_date).days
    if days < 0:
        return f"  [OVERDUE {-days}d]"
    if days == 0:
        return "  [DUE TODAY]"
    if days <= 3:
        return f"  [due in {days}d]"
    return ""


def format_schedule(scheduler: Scheduler) -> str:
    """Render the scheduler's current plan as a formatted terminal table."""
    owner = scheduler.owner
    plan = scheduler.planned_task_order
    available_min = int(owner.available_hours_per_day * 60)
    used_min = sum(t.duration_minutes for t in plan)
    remaining_min = available_min - used_min

    bar = "─" * _WIDTH
    lines = [
        f"┌{bar}┐",
        _row("PawPal+  Daily Care Plan"),
        _row(f"{owner.name}  ·  {scheduler.schedule_date}  ·  {available_min}m available"),
        f"├{bar}┤",
        _row(f"{'TASK':<22}{'CATEGORY':<13}{'TIME':>4}   PRIORITY"),
        f"├{bar}┤",
    ]

    if plan:
        for i, t in enumerate(plan, 1):
            label = _due_label(t, scheduler.schedule_date)
            lines.append(_row(
                f"{i}. {t.title:<20} {t.category:<12} {t.duration_minutes:>3}m"
                f"   {_priority_bar(t.priority)}{label}"
            ))
    else:
        lines.append(_row("  (no tasks fit the available time)"))

    skipped = [t for t in scheduler.fetch_pending_tasks() if t not in plan]
    if skipped:
        lines += [
            f"├{bar}┤",
            _row("NOT SCHEDULED"),
            f"├{bar}┤",
        ]
        for t in skipped:
            reason = f"  [needs {t.duration_minutes}m, {remaining_min}m left]"
            lines.append(_row(
                f"   {t.title:<21} {t.category:<12} {t.duration_minutes:>3}m"
                f"   {_priority_bar(t.priority)}{reason}"
            ))

    lines += [
        f"├{bar}┤",
        _row(f"Scheduled {used_min}m of {available_min}m  ·  {remaining_min}m unused"),
        f"└{bar}┘",
    ]
    return "\n".join(lines)


def section(title: str) -> None:
    print(f"\n{'=' * 66}")
    print(f"  {title}")
    print(f"{'=' * 66}")


def show_change(label: str, before, after) -> None:
    """Print a single before → after line for a value that just changed."""
    print(f"  {label:<22}  {str(before)!r:<28}  →  {str(after)!r}")


def show_fields(heading: str, fields: dict) -> None:
    """Print a labeled block of key: value pairs, aligned by key width."""
    print(f"\n  {heading}")
    width = max(len(k) for k in fields)
    for key, val in fields.items():
        print(f"    {key:<{width}}  {val!r}")


def show_tasks(heading: str, tasks: list) -> None:
    """Print a compact, column-aligned task table with a heading."""
    print(f"\n  {heading} ({len(tasks)})")
    if not tasks:
        print("    (none)")
        return
    print(f"    {'TASK':<22} {'CATEGORY':<12} {'TIME':>4}   {'PRIORITY':<10} STATUS")
    print(f"    {'─' * 62}")
    for t in tasks:
        due = f"  due {t.due_date.strftime('%m-%d')}" if t.due_date else ""
        print(
            f"    {t.title:<22} {t.category:<12} {t.duration_minutes:>3}m"
            f"   {_priority_bar(t.priority):<10} {t.status}{due}"
        )


if __name__ == "__main__":

    # ------------------------------------------------------------------
    # SECTION 1 — Basic schedule (same as before)
    # ------------------------------------------------------------------
    section("1. Generate daily plan")

    owner = Owner(name="Alex", email="alex@example.com", available_hours_per_day=2.0)
    buddy = Pet(name="Buddy", type="Dog", age=4)
    owner.add_pet(buddy)

    walk_am  = Task(title="Morning walk",   category="exercise", duration_minutes=30, priority=5)
    walk_pm  = Task(title="Evening walk",   category="exercise", duration_minutes=30, priority=4)
    brush    = Task(title="Teeth brushing", category="grooming", duration_minutes=10, priority=3)
    nail     = Task(title="Nail trim",      category="grooming", duration_minutes=20, priority=2,
                    due_date=datetime.today())
    bath     = Task(title="Bath",           category="grooming", duration_minutes=45, priority=2)

    for t in (walk_am, walk_pm, brush, nail, bath):
        buddy.add_task(t)

    scheduler = Scheduler(owner=owner)
    scheduler.generate_daily_plan()
    print(format_schedule(scheduler))

    # ------------------------------------------------------------------
    # SECTION 2 — Task state: mark_completed, reschedule, to_display_string
    # ------------------------------------------------------------------
    section("2. Task state changes")

    print("\n  mark_completed()")
    show_change("walk_am.status", walk_am.status, "completed")
    walk_am.mark_completed()

    scheduler.generate_daily_plan()
    show_tasks("Pending tasks after mark_completed (walk_am dropped out)",
               scheduler.planned_task_order)

    tomorrow = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = tomorrow.replace(day=tomorrow.day + 1)

    print("\n  reschedule()  —  sets a new due date")
    show_change("bath.due_date", bath.due_date, tomorrow.date())
    bath.reschedule(tomorrow)

    print("\n  reschedule()  —  also resets 'skipped' back to 'pending'")
    brush.status = "skipped"
    show_change("brush.status", brush.status, "pending")
    brush.reschedule(tomorrow)

    # ------------------------------------------------------------------
    # SECTION 3 — Priority clamping in __post_init__
    # ------------------------------------------------------------------
    section("3. Priority clamping (Task.__post_init__)")

    too_low  = Task(title="Tiny task",  category="misc", duration_minutes=5, priority=0)
    too_high = Task(title="Super task", category="misc", duration_minutes=5, priority=99)
    print()
    show_change("priority=0  clamped to", 0,  too_low.priority)
    show_change("priority=99 clamped to", 99, too_high.priority)

    # ------------------------------------------------------------------
    # SECTION 4 — Pet management: update_care_info, remove_task
    # ------------------------------------------------------------------
    section("4. Pet management")

    print("\n  update_care_info()")
    show_change("feeding_schedule", buddy.feeding_schedule, "7am and 6pm")
    show_change("medication_notes", buddy.medication_notes, "Flea tablet every 30 days")
    buddy.update_care_info(
        feeding_schedule="7am and 6pm",
        medication_notes="Flea tablet every 30 days",
    )
    show_fields("Buddy after update_care_info()", {
        "feeding_schedule": buddy.feeding_schedule,
        "medication_notes": buddy.medication_notes,
    })

    print("\n  remove_task(nail)")
    show_change("len(buddy.task_list)", len(buddy.task_list), len(buddy.task_list) - 1)
    buddy.remove_task(nail)
    show_tasks("Buddy's remaining tasks", buddy.task_list)

    # ------------------------------------------------------------------
    # SECTION 5 — Owner management: set_preferences, remove_pet, get_all_tasks
    # ------------------------------------------------------------------
    section("5. Owner management")

    luna = Pet(name="Luna", type="Cat", age=2)
    luna.add_task(Task(title="Litter box", category="hygiene",  duration_minutes=10, priority=4))
    luna.add_task(Task(title="Playtime",   category="exercise", duration_minutes=15, priority=3))

    print("\n  add_pet(luna)")
    show_change("owner.pets", [p.name for p in owner.pets],
                [p.name for p in owner.pets] + ["Luna"])
    owner.add_pet(luna)
    show_tasks("get_all_tasks() — flattened across Buddy + Luna", owner.get_all_tasks())

    print("\n  set_preferences()")
    prefs = {"preferred_walk_time": "morning", "avoid_category": "grooming"}
    owner.set_preferences(prefs)
    show_fields("owner.preferences after set_preferences()", owner.preferences)

    print("\n  remove_pet(luna)")
    show_change("owner.pets", [p.name for p in owner.pets],
                [p.name for p in owner.pets if p is not luna])
    owner.remove_pet(luna)
    show_tasks("get_all_tasks() after remove_pet — Luna's tasks gone", owner.get_all_tasks())

    # ------------------------------------------------------------------
    # SECTION 6 — Scheduler: apply_constraints and explain_plan
    # ------------------------------------------------------------------
    section("6. Scheduler: apply_constraints and explain_plan")

    # Reset walk_am so it re-enters the pool
    walk_am.status = "pending"
    scheduler.generate_daily_plan()
    print("Plan before apply_constraints:")
    print(format_schedule(scheduler))

    # Tighten time to 45 minutes — only the highest-scored tasks should fit
    print("\nAfter apply_constraints(time_available_hours=0.75):")
    scheduler.apply_constraints(time_available_hours=0.75)
    print(format_schedule(scheduler))

    # Restore time and filter to high-priority tasks only (4 and 5)
    scheduler.apply_constraints(time_available_hours=2.0, priorities=[4, 5])
    print("\nAfter apply_constraints(time_available_hours=2.0, priorities=[4, 5]):")
    print(format_schedule(scheduler))

    # explain_plan gives the plain-text narrative version
    print("\nexplain_plan() output:")
    print(scheduler.explain_plan())
