# PawPal+ Project Reflection

## 1. System Design
This pet care app is designed as a smart, adaptive assistant for busy pet owners who want to provide consistent, high-quality care without the stress of constant planning.

At its core, the app tracks all essential aspects of pet care: daily walks, feeding schedules, medications, enrichment activities, grooming routines, and more. Users can easily log tasks, set recurring routines, and input specific needs for each pet, creating a complete, personalized care profile.

Each day, the app generates a clear, manageable care plan tailored to that specific schedule. It doesn’t just tell the user what to do—it explains why. For instance, it might highlight that a shorter walk is scheduled today due to time constraints, but includes extra enrichment to compensate, or that a grooming task was moved forward to prevent buildup.

The result is a supportive, transparent assistant that helps pet owners stay consistent, make informed decisions, and feel confident that their pet’s needs are being met—even on the busiest days.

Example core actions: add a pet, schedule a grooming appointment, set a feeding schedule

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

```mermaid
classDiagram
    class Owner {
        +String name
        +String email
        +List~Pet~ pets
        +int availableHoursPerDay
        +addPet(pet)
        +removePet(pet)
        +setPreferences(pref)
    }

    class Pet {
        +String name
        +String type
        +int age
        +List~Task~ taskList
        +String feedingSchedule
        +String medicationNotes
        +addTask(task)
        +removeTask(task)
        +updateCareInfo(info)
    }

    class Task {
        +String title
        +String category
        +int durationMinutes
        +int priority (1..5)
        +DateTime dueDate
        +boolean recurring
        +String status
        +markCompleted()
        +reschedule(dateTime)
        +toDisplayString()
    }

    class Scheduler {
        +Owner owner
        +Date date
        +List~Task~ plannedTaskOrder
        +generateDailyPlan()
        +scoreTask(task)
        +applyConstraints(timeAvailable, priorities, preferences)
        +explainPlan()
    }

    erDiagram
    OWNER ||--o{ PET : owns
    PET ||--o{ TASK : has
    SCHEDULER }o--|| OWNER : uses
    SCHEDULER }o--|| TASK : schedules
```
![alt text](image.png)

**b. Design changes**

- Did your design change during implementation?
1. No changes on Task class attributes or methods. 
2. No changes on Pet class attributes or methods. 

- If yes, describe at least one change and why you made it.
3. A float variable available_hours_per_day was added to the Owner dataclass. A method called Owner.get_all_tasks() was added to collects tasks from all owned pets.
4. Four methods were added to the Scheduler dataclass. 
    a. Scheduler.fetch_pending_tasks() derives pending tasks using owner’s list.
    b. Scheduler.generate_daily_plan() sorts by pending status, priority, due date and fits items into available_hours_per_day
    c. Scheduler.apply_constraints() and Scheduler.explain_plan() were updated with minimal logic to avoid no-op bottllneck. 
---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
