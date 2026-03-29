import unittest
from datetime import datetime, timedelta
from pawpal_system import Task, Pet, Owner, Scheduler


class TestPawPal(unittest.TestCase):

    def test_mark_completed_changes_status(self):
        """Test that mark_completed() changes the task's status to 'completed'."""
        task = Task(title="Walk", category="exercise", duration_minutes=30, priority=5)
        self.assertEqual(task.status, "pending")  # Initial status should be pending

        task.mark_completed()
        self.assertEqual(task.status, "completed")  # Status should change to completed

    def test_add_task_increases_pet_task_count(self):
        """Test that adding a task to a Pet increases that pet's task count."""
        pet = Pet(name="Buddy", type="Dog", age=4)
        initial_task_count = len(pet.task_list)
        self.assertEqual(initial_task_count, 0)  # Pet should start with no tasks

        task = Task(title="Walk", category="exercise", duration_minutes=30, priority=5)
        pet.add_task(task)
        self.assertEqual(len(pet.task_list), 1)  # Task count should increase by 1


class TestSchedulerHappyPaths(unittest.TestCase):
    """Happy path tests for normal scheduler operation."""

    def test_basic_scheduling_single_pet(self):
        """Test: Single pet with multiple tasks of varying priorities."""
        owner = Owner("Test", "test@example.com", 2.0)  # 2 hours = 120 minutes
        pet = Pet("Buddy", "dog", 3)
        owner.add_pet(pet)

        # Add tasks: 30min priority 5, 20min priority 3, 45min priority 2
        task1 = Task("Walk", "exercise", 30, 5)
        task2 = Task("Brush", "grooming", 20, 3)
        task3 = Task("Nail trim", "grooming", 45, 2)
        pet.add_task(task1)
        pet.add_task(task2)
        pet.add_task(task3)

        scheduler = Scheduler(owner)
        plan = scheduler.generate_daily_plan()

        # All tasks should fit (30+20+45=95 < 120)
        self.assertEqual(len(plan), 3)
        # Should be sorted by priority score (highest first)
        self.assertEqual(plan[0], task1)  # priority 5
        self.assertEqual(plan[1], task2)  # priority 3
        self.assertEqual(plan[2], task3)  # priority 2

    def test_recurring_task_daily_creation(self):
        """Test: Daily task completion creates next occurrence."""
        owner = Owner("Test", "test@example.com", 2.0)
        pet = Pet("Buddy", "dog", 3)
        owner.add_pet(pet)

        task = Task("Feed", "feeding", 15, 4, frequency="daily")
        pet.add_task(task)

        scheduler = Scheduler(owner)
        initial_task_count = len(pet.task_list)

        # Mark completed - should create next occurrence
        task.mark_completed(scheduler)

        # Task list should have increased by 1
        self.assertEqual(len(pet.task_list), initial_task_count + 1)

        # New task should have next due date (tomorrow at midnight)
        new_task = pet.task_list[-1]  # Last added task
        expected_due = datetime.now() + timedelta(days=1)
        expected_due = expected_due.replace(hour=0, minute=0, second=0, microsecond=0)
        self.assertEqual(new_task.due_date, expected_due)
        self.assertEqual(new_task.status, "pending")

    def test_recurring_task_weekly_creation(self):
        """Test: Weekly task completion creates next occurrence 7 days later."""
        owner = Owner("Test", "test@example.com", 2.0)
        pet = Pet("Buddy", "dog", 3)
        owner.add_pet(pet)

        task = Task("Bath", "grooming", 45, 3, frequency="weekly")
        pet.add_task(task)

        scheduler = Scheduler(owner)

        # Mark completed - should create next occurrence
        task.mark_completed(scheduler)

        # New task should have due date 7 days from now
        new_task = pet.task_list[-1]
        expected_due = datetime.now() + timedelta(days=7)
        expected_due = expected_due.replace(hour=0, minute=0, second=0, microsecond=0)
        self.assertEqual(new_task.due_date, expected_due)

    def test_task_sorting_by_scheduled_time(self):
        """Test: Tasks with different scheduled_time values sort correctly."""
        tasks = [
            Task("Late night", "misc", 10, 1, scheduled_time="21:00"),
            Task("Early morning", "misc", 10, 1, scheduled_time="06:00"),
            Task("Afternoon", "misc", 10, 1, scheduled_time="14:30"),
            Task("Evening", "misc", 10, 1, scheduled_time="18:00"),
            Task("No time", "misc", 10, 1),  # No scheduled_time
        ]

        sorted_tasks = Task.sort_by_time(tasks)

        # Should be sorted chronologically, no-time tasks last
        self.assertEqual(sorted_tasks[0].scheduled_time, "06:00")
        self.assertEqual(sorted_tasks[1].scheduled_time, "14:30")
        self.assertEqual(sorted_tasks[2].scheduled_time, "18:00")
        self.assertEqual(sorted_tasks[3].scheduled_time, "21:00")
        self.assertIsNone(sorted_tasks[4].scheduled_time)

    def test_priority_based_filtering(self):
        """Test: apply_constraints() with priority filter."""
        owner = Owner("Test", "test@example.com", 2.0)
        pet = Pet("Buddy", "dog", 3)
        owner.add_pet(pet)

        # Add tasks with priorities 1,2,3,4,5
        tasks = []
        for i in range(1, 6):
            task = Task(f"Task {i}", "misc", 10, i)
            tasks.append(task)
            pet.add_task(task)

        scheduler = Scheduler(owner)
        # Filter to prefer priorities 4 and 5, but allow lower priorities to fill time
        scheduler.apply_constraints(time_available_hours=2.0, priorities=[4, 5])

        # Plan should prioritize 4 and 5 tasks first, then fill with lower priorities
        # All tasks should be from the original set
        for task in scheduler.planned_task_order:
            self.assertIn(task, tasks)

        # Total time should not exceed available time
        total_time = sum(t.duration_minutes for t in scheduler.planned_task_order)
        self.assertLessEqual(total_time, 120)  # 2.0 hours = 120 minutes


class TestSchedulerEdgeCases(unittest.TestCase):
    """Edge case tests for boundary conditions and error scenarios."""

    def test_pet_with_no_tasks(self):
        """Edge case: Pet with empty task list."""
        owner = Owner("Test", "test@example.com", 2.0)
        pet = Pet("Buddy", "dog", 3)
        owner.add_pet(pet)

        scheduler = Scheduler(owner)
        plan = scheduler.generate_daily_plan()

        self.assertEqual(len(plan), 0)
        self.assertEqual(len(scheduler.fetch_pending_tasks()), 0)

    def test_zero_available_time(self):
        """Edge case: No time available."""
        owner = Owner("Test", "test@example.com", 0.0)
        pet = Pet("Buddy", "dog", 3)
        task = Task("Walk", "exercise", 30, 5)
        pet.add_task(task)
        owner.add_pet(pet)

        scheduler = Scheduler(owner)
        plan = scheduler.generate_daily_plan()

        self.assertEqual(len(plan), 0)

    def test_tasks_exceeding_available_time(self):
        """Edge case: Total task time > available time."""
        owner = Owner("Test", "test@example.com", 1.0)  # 60 minutes
        pet = Pet("Buddy", "dog", 3)
        owner.add_pet(pet)

        # Add 3 tasks totaling 120 minutes (more than 60 available)
        task1 = Task("Task 1", "misc", 30, 5)
        task2 = Task("Task 2", "misc", 45, 4)
        task3 = Task("Task 3", "misc", 45, 3)
        pet.add_task(task1)
        pet.add_task(task2)
        pet.add_task(task3)

        scheduler = Scheduler(owner)
        plan = scheduler.generate_daily_plan()

        # Should only fit the highest priority task(s) within time limit
        total_scheduled = sum(t.duration_minutes for t in plan)
        self.assertLessEqual(total_scheduled, 60)

        # Should have skipped tasks
        all_pending = scheduler.fetch_pending_tasks()
        skipped = [t for t in all_pending if t not in plan]
        self.assertGreater(len(skipped), 0)

    def test_multiple_tasks_same_time(self):
        """Edge case: Two tasks with identical scheduled_time."""
        owner = Owner("Test", "test@example.com", 2.0)
        pet = Pet("Buddy", "dog", 3)
        owner.add_pet(pet)

        task1 = Task("Walk", "exercise", 30, 5, scheduled_time="08:00")
        task2 = Task("Feed", "feeding", 15, 4, scheduled_time="08:00")  # Same time!
        pet.add_task(task1)
        pet.add_task(task2)

        scheduler = Scheduler(owner)
        scheduler.generate_daily_plan()

        conflicts = scheduler.detect_conflicts()
        self.assertGreater(len(conflicts), 0)

        # Should contain time conflict warning
        conflict_messages = [c for c in conflicts if "TIME CONFLICT" in c]
        self.assertEqual(len(conflict_messages), 1)

    def test_overdue_tasks(self):
        """Edge case: Tasks with due dates in the past."""
        owner = Owner("Test", "test@example.com", 2.0)
        pet = Pet("Buddy", "dog", 3)
        owner.add_pet(pet)

        yesterday = datetime.now() - timedelta(days=1)
        today = datetime.now()
        tomorrow = datetime.now() + timedelta(days=1)

        overdue_task = Task("Overdue", "misc", 10, 3, due_date=yesterday)
        due_today_task = Task("Due today", "misc", 10, 3, due_date=today)
        due_tomorrow_task = Task("Due tomorrow", "misc", 10, 3, due_date=tomorrow)

        pet.add_task(overdue_task)
        pet.add_task(due_today_task)
        pet.add_task(due_tomorrow_task)

        scheduler = Scheduler(owner)

        # Overdue task should get highest score bonus (+5.0)
        overdue_score = scheduler.score_task(overdue_task)
        today_score = scheduler.score_task(due_today_task)
        tomorrow_score = scheduler.score_task(due_tomorrow_task)

        self.assertGreater(overdue_score, today_score)
        self.assertGreater(today_score, tomorrow_score)

    def test_recurring_task_without_frequency(self):
        """Edge case: Task marked completed but has no frequency set."""
        owner = Owner("Test", "test@example.com", 2.0)
        pet = Pet("Buddy", "dog", 3)
        owner.add_pet(pet)

        task = Task("One-time", "misc", 10, 3)  # No frequency
        pet.add_task(task)

        scheduler = Scheduler(owner)
        initial_count = len(pet.task_list)

        task.mark_completed(scheduler)

        # No new task should be created
        self.assertEqual(len(pet.task_list), initial_count)
        self.assertEqual(task.status, "completed")

    def test_recurring_task_without_pet(self):
        """Edge case: create_next_task_occurrence() called on task with pet=None."""
        task = Task("Feed", "feeding", 15, 4, frequency="daily")

        scheduler = Scheduler(Owner("Test", "test@example.com", 2.0))

        with self.assertRaises(ValueError) as context:
            scheduler.create_next_task_occurrence(task)

        self.assertIn("task must have frequency and pet", str(context.exception))

    def test_invalid_frequency_value(self):
        """Edge case: Task with unknown frequency string."""
        owner = Owner("Test", "test@example.com", 2.0)
        pet = Pet("Buddy", "dog", 3)
        owner.add_pet(pet)

        task = Task("Monthly", "misc", 10, 3, frequency="monthly")  # Invalid frequency
        pet.add_task(task)

        scheduler = Scheduler(owner)

        with self.assertRaises(ValueError) as context:
            scheduler.create_next_task_occurrence(task)

        self.assertIn("Unknown frequency", str(context.exception))

    def test_priority_clamping(self):
        """Edge case: Task creation with out-of-range priority values."""
        too_low = Task("Low", "misc", 5, 0)    # Should clamp to 1
        too_high = Task("High", "misc", 5, 10)  # Should clamp to 5

        self.assertEqual(too_low.priority, 1)
        self.assertEqual(too_high.priority, 5)

    def test_task_filtering_combinations(self):
        """Edge case: filter_tasks() with both status and pet name filters."""
        owner = Owner("Test", "test@example.com", 2.0)
        pet1 = Pet("Buddy", "dog", 3)
        pet2 = Pet("Luna", "cat", 2)
        owner.add_pet(pet1)
        owner.add_pet(pet2)

        # Create tasks with different statuses
        task1 = Task("Task1", "misc", 10, 3)  # pending
        task2 = Task("Task2", "misc", 10, 3)  # completed
        task1.status = "completed"
        task2.status = "pending"

        pet1.add_task(task1)
        pet2.add_task(task2)

        all_tasks = owner.get_all_tasks()

        # Filter by both status and pet name
        filtered = Task.filter_tasks(all_tasks, completion_status="pending", pet_name="Luna")

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0], task2)

    def test_same_pet_time_overload(self):
        """Edge case: Single pet with tasks exceeding available time."""
        owner = Owner("Test", "test@example.com", 1.0)  # 60 minutes
        pet = Pet("Buddy", "dog", 3)
        owner.add_pet(pet)

        # Add tasks totaling 90 minutes (more than 60 available)
        task1 = Task("Task1", "misc", 30, 3)
        task2 = Task("Task2", "misc", 35, 3)
        task3 = Task("Task3", "misc", 25, 3)
        pet.add_task(task1)
        pet.add_task(task2)
        pet.add_task(task3)

        scheduler = Scheduler(owner)
        scheduler.generate_daily_plan()

        conflicts = scheduler.detect_conflicts()
        self.assertGreater(len(conflicts), 0)

        # Should contain overload warning
        overload_messages = [c for c in conflicts if "TIME OVERLOAD" in c]
        self.assertEqual(len(overload_messages), 1)

    def test_multiple_high_priority_tasks(self):
        """Edge case: Pet with many priority-4+ tasks."""
        owner = Owner("Test", "test@example.com", 1.0)  # 60 minutes
        pet = Pet("Buddy", "dog", 3)
        owner.add_pet(pet)

        # Add 3 high-priority tasks totaling 55 minutes (close to 60min limit)
        task1 = Task("Task1", "misc", 20, 4)
        task2 = Task("Task2", "misc", 20, 4)
        task3 = Task("Task3", "misc", 15, 5)
        pet.add_task(task1)
        pet.add_task(task2)
        pet.add_task(task3)

        scheduler = Scheduler(owner)
        scheduler.generate_daily_plan()

        conflicts = scheduler.detect_conflicts()
        self.assertGreater(len(conflicts), 0)

        # Should contain pet overload warning
        overload_messages = [c for c in conflicts if "PET OVERLOAD" in c]
        self.assertEqual(len(overload_messages), 1)


class TestSchedulerIntegration(unittest.TestCase):
    """Integration tests for complex scheduling scenarios."""

    def test_recurring_workflow_multiple_days(self):
        """Integration: Daily task lifecycle over multiple days."""
        owner = Owner("Test", "test@example.com", 2.0)
        pet = Pet("Buddy", "dog", 3)
        owner.add_pet(pet)

        task = Task("Daily feed", "feeding", 15, 4, frequency="daily")
        pet.add_task(task)

        scheduler = Scheduler(owner)

        # Simulate multiple completions
        initial_count = len(pet.task_list)
        task.mark_completed(scheduler)
        first_new_task = pet.task_list[-1]

        # Mark the new task completed too
        first_new_task.mark_completed(scheduler)
        second_new_task = pet.task_list[-1]

        # Should have 3 total tasks now (original + 2 new)
        self.assertEqual(len(pet.task_list), initial_count + 2)

        # Due dates should be properly spaced
        self.assertGreater(second_new_task.due_date, first_new_task.due_date)

    def test_mixed_priority_and_time_constraints(self):
        """Integration: Complex scheduling with time limits and priority filters."""
        owner = Owner("Test", "test@example.com", 1.5)  # 90 minutes
        pet = Pet("Buddy", "dog", 3)
        owner.add_pet(pet)

        # Add 8 tasks with mixed priorities and times
        tasks = [
            Task("High1", "misc", 20, 5),
            Task("High2", "misc", 15, 5),
            Task("Med1", "misc", 25, 3),
            Task("Med2", "misc", 30, 3),
            Task("Low1", "misc", 10, 1),
            Task("Low2", "misc", 15, 1),
            Task("Low3", "misc", 20, 1),
            Task("Low4", "misc", 25, 1),
        ]

        for task in tasks:
            pet.add_task(task)

        scheduler = Scheduler(owner)
        # Apply priority filter to only 3,4,5
        scheduler.apply_constraints(time_available_hours=1.5, priorities=[3, 4, 5])

        # Should only include priority 3,4,5 tasks
        for task in scheduler.planned_task_order:
            self.assertIn(task.priority, [3, 4, 5])

        # Total time should not exceed 90 minutes
        total_time = sum(t.duration_minutes for t in scheduler.planned_task_order)
        self.assertLessEqual(total_time, 90)

    def test_conflict_detection_multiple_pets(self):
        """Integration: Multiple pets with overlapping scheduled times."""
        owner = Owner("Test", "test@example.com", 2.0)
        pet1 = Pet("Buddy", "dog", 3)
        pet2 = Pet("Luna", "cat", 2)
        owner.add_pet(pet1)
        owner.add_pet(pet2)

        # Both pets have tasks at same time
        task1 = Task("Walk", "exercise", 30, 5, scheduled_time="08:00")
        task2 = Task("Feed", "feeding", 15, 4, scheduled_time="08:00")
        pet1.add_task(task1)
        pet2.add_task(task2)

        scheduler = Scheduler(owner)
        scheduler.generate_daily_plan()

        conflicts = scheduler.detect_conflicts()
        self.assertGreater(len(conflicts), 0)

        # Should detect the time conflict
        time_conflicts = [c for c in conflicts if "TIME CONFLICT" in c]
        self.assertEqual(len(time_conflicts), 1)


if __name__ == '__main__':
    unittest.main()