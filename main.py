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

    # ------------------------------------------------------------------
    # SECTION 7 — Task sorting and filtering
    # ------------------------------------------------------------------
    section("7. Task sorting and filtering")

    # Create tasks with different scheduled times (out of order)
    task1 = Task(title="Early morning walk", category="exercise", duration_minutes=30, priority=5, scheduled_time="06:00")
    task2 = Task(title="Afternoon play", category="exercise", duration_minutes=20, priority=4, scheduled_time="14:30")
    task3 = Task(title="Evening feeding", category="feeding", duration_minutes=15, priority=3, scheduled_time="18:00")
    task4 = Task(title="Late night grooming", category="grooming", duration_minutes=25, priority=2, scheduled_time="21:00")
    task5 = Task(title="Midday check", category="health", duration_minutes=10, priority=4, scheduled_time="12:00")

    # Add tasks to pets (out of order)
    buddy.add_task(task4)  # Late night first
    buddy.add_task(task2)  # Afternoon
    buddy.add_task(task1)  # Early morning
    buddy.add_task(task5)  # Midday
    buddy.add_task(task3)  # Evening last

    # Mark some tasks as completed for filtering demo
    task1.mark_completed()
    task3.status = "skipped"

    print("\n  Original task order (as added):")
    for i, task in enumerate(buddy.task_list, 1):
        print(f"    {i}. {task.title} at {task.scheduled_time} - {task.status}")

    # Sort tasks by time
    sorted_tasks = Task.sort_by_time(buddy.task_list)
    print("\n  Tasks sorted by time (using sort_by_time()):")
    for i, task in enumerate(sorted_tasks, 1):
        print(f"    {i}. {task.title} at {task.scheduled_time} - {task.status}")

    # Filter by completion status
    pending_tasks = Task.filter_tasks(buddy.task_list, completion_status="pending")
    print(f"\n  Pending tasks only (filter_tasks with completion_status='pending'):")
    for i, task in enumerate(pending_tasks, 1):
        print(f"    {i}. {task.title} at {task.scheduled_time} - {task.status}")

    completed_tasks = Task.filter_tasks(buddy.task_list, completion_status="completed")
    print(f"\n  Completed tasks only (filter_tasks with completion_status='completed'):")
    for i, task in enumerate(completed_tasks, 1):
        print(f"    {i}. {task.title} at {task.scheduled_time} - {task.status}")

    # Filter by pet name
    buddy_tasks = Task.filter_tasks(owner.get_all_tasks(), pet_name="Buddy")
    print(f"\n  Tasks for Buddy only (filter_tasks with pet_name='Buddy'):")
    for i, task in enumerate(buddy_tasks, 1):
        print(f"    {i}. {task.title} at {task.scheduled_time} - {task.status}")

    # Combined filtering: pending tasks for Buddy
    pending_buddy_tasks = Task.filter_tasks(buddy.task_list, completion_status="pending", pet_name="Buddy")
    print(f"\n  Pending tasks for Buddy (combined filtering):")
    for i, task in enumerate(pending_buddy_tasks, 1):
        print(f"    {i}. {task.title} at {task.scheduled_time} - {task.status}")

    # ------------------------------------------------------------------
    # SECTION 8 — Repeatable tasks
    # ------------------------------------------------------------------
    section("8. Repeatable tasks")

    # Create repeatable tasks
    daily_feeding = Task(title="Daily feeding", category="feeding", duration_minutes=15, priority=4, frequency="daily")
    weekly_bath = Task(title="Weekly bath", category="grooming", duration_minutes=45, priority=3, frequency="weekly")
    one_time_vet = Task(title="Vet checkup", category="health", duration_minutes=60, priority=5)  # No frequency = one-time

    # Add tasks to Luna (since Buddy already has many tasks)
    luna = Pet(name="Luna", type="Cat", age=2)
    owner.add_pet(luna)
    luna.add_task(daily_feeding)
    luna.add_task(weekly_bath)
    luna.add_task(one_time_vet)

    print("\n  Initial repeatable tasks for Luna:")
    for task in luna.task_list:
        print(f"    {task.to_display_string()}")

    # Create scheduler for Luna's owner
    luna_scheduler = Scheduler(owner=owner)

    # Mark daily feeding as completed - should create new instance
    print("\n  Marking 'Daily feeding' as completed...")
    daily_feeding.mark_completed(scheduler=luna_scheduler)

    print("  After marking daily feeding complete:")
    for i, task in enumerate(luna.task_list, 1):
        print(f"    {i}. {task.to_display_string()}")

    # Mark weekly bath as completed - should create new instance
    print("\n  Marking 'Weekly bath' as completed...")
    weekly_bath.mark_completed(scheduler=luna_scheduler)

    print("  After marking weekly bath complete:")
    for i, task in enumerate(luna.task_list, 1):
        print(f"    {i}. {task.to_display_string()}")

    # Mark one-time vet checkup as completed - should NOT create new instance
    print("\n  Marking 'Vet checkup' (one-time) as completed...")
    one_time_vet.mark_completed(scheduler=luna_scheduler)

    print("  After marking vet checkup complete:")
    for i, task in enumerate(luna.task_list, 1):
        print(f"    {i}. {task.to_display_string()}")

    print(f"\n  Luna now has {len(luna.task_list)} total tasks (original 3 + 2 new recurring instances)")

    # ------------------------------------------------------------------
    # SECTION 9 — Conflict detection
    # ------------------------------------------------------------------
    section("9. Conflict detection")

    #Create a new owner and pets for conflict testing
    conflict_owner = Owner(name="Conflict Test", email="conflict@example.com", available_hours_per_day=1.0)  # Only 60 minutes
    max_pet = Pet(name="Max", type="Dog", age=5)
    bella_pet = Pet(name="Bella", type="Cat", age=3)
    conflict_owner.add_pet(max_pet)
    conflict_owner.add_pet(bella_pet)

    # Create tasks with time slot conflicts (same scheduled_time)
    max_walk_morning = Task(title="Morning walk", category="exercise", duration_minutes=30, priority=5, scheduled_time="08:00")
    max_feed_morning = Task(title="Morning feeding", category="feeding", duration_minutes=15, priority=4, scheduled_time="08:00")  # Same time!
    bella_groom = Task(title="Grooming", category="grooming", duration_minutes=45, priority=3, scheduled_time="10:00")
    bella_play = Task(title="Playtime", category="exercise", duration_minutes=30, priority=4, scheduled_time="14:00")

    max_pet.add_task(max_walk_morning)
    max_pet.add_task(max_feed_morning)
    bella_pet.add_task(bella_groom)
    bella_pet.add_task(bella_play)

    # Create scheduler and generate plan
    conflict_scheduler = Scheduler(owner=conflict_owner)
    conflict_plan = conflict_scheduler.generate_daily_plan()

    print("\n  Generated schedule with potential conflicts:")
    print(format_schedule(conflict_scheduler))

    #Check for conflicts explicitly
    conflicts = conflict_scheduler.detect_conflicts()
    if conflicts:
        print("\n  🚨 DETECTED CONFLICTS:")
        for conflict in conflicts:
            print(f"     {conflict}")
    else:
        print("\n  ✅ No conflicts detected")

    # Test overload scenario - add more tasks to exceed time limit
    print("\n  Adding more tasks to test overload detection...")
    max_brush = Task(title="Teeth brushing", category="grooming", duration_minutes=20, priority=3)
    bella_nap = Task(title="Nap time", category="health", duration_minutes=25, priority=2)
    max_pet.add_task(max_brush)
    bella_pet.add_task(bella_nap)

    # Regenerate plan with overload
    overload_plan = conflict_scheduler.generate_daily_plan()
    print("\n  Schedule after adding overload tasks:")
    print(format_schedule(conflict_scheduler))

    overload_conflicts = conflict_scheduler.detect_conflicts()
    if overload_conflicts:
        print("\n  🚨 OVERLOAD CONFLICTS DETECTED:")
        for conflict in overload_conflicts:
            print(f"     {conflict}")
    else:
        print("\n  ✅ No overload conflicts detected")
