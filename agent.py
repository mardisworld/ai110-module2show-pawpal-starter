"""
PawPal+ AI Agent
Uses Claude with tool use to let users manage pets and schedules via natural language.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import anthropic

from pawpal_system import Owner, Pet, Scheduler, Task

# ---------------------------------------------------------------------------
# Shared state — one owner per Streamlit session (passed in from session_state)
# ---------------------------------------------------------------------------

TOOLS: list[dict[str, Any]] = [
    {
        "name": "add_pet",
        "description": "Add a new pet to the owner's profile.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The pet's name"},
                "type": {"type": "string", "description": "Species, e.g. dog, cat, rabbit"},
                "age": {"type": "integer", "description": "The pet's age in years"},
                "feeding_schedule": {"type": "string", "description": "Brief feeding schedule, e.g. 'twice daily'"},
                "medication_notes": {"type": "string", "description": "Any medication info"},
            },
            "required": ["name", "type", "age"],
        },
    },
    {
        "name": "add_task",
        "description": "Add a care task to one of the owner's pets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pet_name": {"type": "string", "description": "Name of the pet to add the task to"},
                "title": {"type": "string", "description": "Task title, e.g. 'Morning walk'"},
                "category": {"type": "string", "description": "Category, e.g. exercise, feeding, grooming, medication"},
                "duration_minutes": {"type": "integer", "description": "How long the task takes in minutes"},
                "priority": {"type": "integer", "description": "Priority from 1 (low) to 5 (high)"},
                "due_date": {"type": "string", "description": "Optional ISO date string YYYY-MM-DD"},
                "recurring": {"type": "boolean", "description": "Whether this task repeats daily"},
            },
            "required": ["pet_name", "title", "category", "duration_minutes", "priority"],
        },
    },
    {
        "name": "set_available_hours",
        "description": "Set how many hours per day the owner has available for pet care.",
        "input_schema": {
            "type": "object",
            "properties": {
                "hours": {"type": "number", "description": "Hours available per day, e.g. 2.5"},
            },
            "required": ["hours"],
        },
    },
    {
        "name": "generate_schedule",
        "description": "Generate an optimized daily care schedule based on current pets and tasks.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_current_state",
        "description": "Get a summary of the current pets, tasks, and schedule.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]

SYSTEM_PROMPT = """You are PawPal+, a friendly AI assistant that helps pet owners plan daily care for their pets.

You help users:
- Add pets to their profile (add_pet)
- Add care tasks for each pet (add_task)
- Set how much time they have available each day (set_available_hours)
- Generate an optimized daily schedule (generate_schedule)
- View current pets, tasks, and the schedule (get_current_state)

Be warm, encouraging, and concise. When you generate a schedule, explain *why* each task was prioritized — mention priority score, time constraints, and due dates where relevant. If a task couldn't fit, explain why and suggest alternatives."""


def _execute_tool(tool_name: str, tool_input: dict[str, Any], owner: Owner) -> str:
    """Execute a tool call and return the result as a string."""

    if tool_name == "add_pet":
        pet = Pet(
            name=tool_input["name"],
            type=tool_input["type"],
            age=tool_input["age"],
            feeding_schedule=tool_input.get("feeding_schedule", ""),
            medication_notes=tool_input.get("medication_notes", ""),
        )
        owner.add_pet(pet)
        return f"Added pet: {pet.name} ({pet.type}, age {pet.age})."

    elif tool_name == "add_task":
        pet_name = tool_input["pet_name"]
        pet = next((p for p in owner.pets if p.name.lower() == pet_name.lower()), None)
        if pet is None:
            return f"No pet named '{pet_name}' found. Available pets: {[p.name for p in owner.pets]}"
        due_date = None
        if tool_input.get("due_date"):
            try:
                due_date = datetime.fromisoformat(tool_input["due_date"])
            except ValueError:
                pass
        task = Task(
            title=tool_input["title"],
            category=tool_input["category"],
            duration_minutes=tool_input["duration_minutes"],
            priority=tool_input["priority"],
            due_date=due_date,
            recurring=tool_input.get("recurring", False),
        )
        pet.add_task(task)
        return f"Added task '{task.title}' ({task.duration_minutes}m, priority {task.priority}) to {pet.name}."

    elif tool_name == "set_available_hours":
        owner.available_hours_per_day = tool_input["hours"]
        return f"Available hours per day set to {owner.available_hours_per_day}h."

    elif tool_name == "generate_schedule":
        scheduler = Scheduler(owner=owner)
        plan = scheduler.generate_daily_plan()
        if not plan:
            total_tasks = len(owner.get_all_tasks())
            return (
                f"No tasks fit the schedule. "
                f"You have {total_tasks} total task(s) and "
                f"{owner.available_hours_per_day}h available. "
                "Try increasing available hours or reducing task durations."
            )
        lines = []
        for t in plan:
            due_str = f", due {t.due_date.date()}" if t.due_date else ""
            lines.append(
                f"- {t.title} [{t.category}] — {t.duration_minutes}m, priority {t.priority}{due_str}"
            )
        total_minutes = sum(t.duration_minutes for t in plan)
        return (
            f"Generated schedule ({len(plan)} tasks, {total_minutes}m total):\n"
            + "\n".join(lines)
        )

    elif tool_name == "get_current_state":
        if not owner.pets:
            return "No pets added yet."
        lines = [f"Owner: {owner.name} ({owner.available_hours_per_day}h/day available)"]
        for pet in owner.pets:
            lines.append(f"\nPet: {pet.name} ({pet.type}, age {pet.age})")
            if not pet.task_list:
                lines.append("  No tasks yet.")
            for t in pet.task_list:
                lines.append(f"  • {t.to_display_string()}")
        return "\n".join(lines)

    else:
        return f"Unknown tool: {tool_name}"


def run_agent_turn(
    user_message: str,
    conversation_history: list[dict[str, Any]],
    owner: Owner,
) -> tuple[str, list[dict[str, Any]]]:
    """
    Send one user message to the Claude agent and return the assistant reply
    plus the updated conversation history.
    """
    client = anthropic.Anthropic()

    conversation_history.append({"role": "user", "content": user_message})

    messages = list(conversation_history)

    while True:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Append assistant turn to history
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Extract text reply
            reply = next(
                (block.text for block in response.content if block.type == "text"),
                "(no reply)",
            )
            # Sync history back
            conversation_history.clear()
            conversation_history.extend(messages)
            return reply, conversation_history

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = _execute_tool(block.name, block.input, owner)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )
            messages.append({"role": "user", "content": tool_results})
            continue

        # Unexpected stop reason — surface as error
        break

    conversation_history.clear()
    conversation_history.extend(messages)
    return "Sorry, something went wrong. Please try again.", conversation_history
