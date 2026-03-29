import streamlit as st
from pawpal_system import Task, Pet, Owner, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("👤 Owner Profile Setup")
st.caption("Create or update your owner profile to get started.")

col1, col2 = st.columns([2, 1])
with col1:
    owner_name = st.text_input("Owner name", value="Jordan", key="owner_name")
with col2:
    owner_email = st.text_input("Email", value="owner@example.com", key="owner_email")

col3, col4 = st.columns([1, 1])
with col3:
    available_hours = st.number_input("Available hours per day", min_value=0.5, max_value=24.0, value=3.0, step=0.5, key="available_hours")
with col4:
    if st.button("👤 Create/Update Owner Profile", type="primary", help="Set up your owner profile"):
        # Create or update owner
        if "owner" not in st.session_state or st.session_state.owner is None:
            st.session_state.owner = Owner(
                name=owner_name,
                email=owner_email,
                available_hours_per_day=available_hours
            )
            st.session_state.scheduler = Scheduler(owner=st.session_state.owner)
            st.success(f"✅ Owner profile created for {owner_name}!")
        else:
            # Update existing owner
            st.session_state.owner.name = owner_name
            st.session_state.owner.email = owner_email
            st.session_state.owner.available_hours_per_day = available_hours
            st.success(f"✅ Owner profile updated for {owner_name}!")
        st.balloons()

# Display current owner info
if "owner" in st.session_state and st.session_state.owner:
    st.write("**Current Owner:**")
    st.info(f"👤 {st.session_state.owner.name} ({st.session_state.owner.email}) - {st.session_state.owner.available_hours_per_day} hours/day available")

st.divider()

st.subheader("🐕 Pet Management")
st.caption("Add pets to your profile.")

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    pet_name = st.text_input("Pet name", value="Mochi", key="pet_name")
with col2:
    species = st.selectbox("Species", ["dog", "cat", "bird", "other"], index=0, key="species")
with col3:
    pet_age = st.number_input("Age", min_value=0, max_value=30, value=2, key="pet_age")

if st.button("🐕 Add Pet", type="primary", help="Add this pet to your profile"):
    if "owner" in st.session_state and st.session_state.owner:
        pet = Pet(name=pet_name, type=species, age=pet_age)
        st.session_state.owner.add_pet(pet)
        st.success(f"✅ Added pet {pet_name} ({species}, {pet_age} years old)!")
        st.balloons()
    else:
        st.error("❌ Please create an owner profile first.")

# Display current pets
if "owner" in st.session_state and st.session_state.owner and st.session_state.owner.pets:
    st.write("**Your Pets:**")
    pet_data = []
    for pet in st.session_state.owner.pets:
        pet_data.append({
            "Name": pet.name,
            "Species": pet.type.title(),
            "Age": f"{pet.age} years",
            "Tasks": len(pet.task_list)
        })
    st.table(pet_data)
elif "owner" in st.session_state and st.session_state.owner:
    st.info("No pets added yet. Add one above!")

st.divider()

st.subheader("📝 Task Management")
st.caption("Add tasks to your pets.")

# Pet selection for tasks
if "owner" in st.session_state and st.session_state.owner and st.session_state.owner.pets:
    pet_options = [f"{pet.name} ({pet.type})" for pet in st.session_state.owner.pets]
    selected_pet_index = st.selectbox("Select pet for task", range(len(pet_options)), format_func=lambda x: pet_options[x], key="selected_pet")

    col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
    with col1:
        task_title = st.text_input("Task title", value="Morning walk", key="task_title")
    with col2:
        duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=30, key="duration")
    with col3:
        priority = st.selectbox("Priority", ["⭐ Low", "⭐⭐ Medium", "⭐⭐⭐ High", "⭐⭐⭐⭐ Very High", "⭐⭐⭐⭐⭐ Critical"],
                               index=2, key="priority")
    with col4:
        category = st.selectbox("Category", ["exercise", "feeding", "grooming", "health", "play", "other"],
                               index=0, key="category")
    with col5:
        frequency = st.selectbox("Frequency", ["One-time", "Daily", "Weekly"], 
                                index=0, key="frequency", help="How often should this task repeat?")

    if st.button("Add Task", type="primary", help="Add this task to your pet care schedule"):
        # Convert priority display to numeric
        priority_map = {"⭐ Low": 1, "⭐⭐ Medium": 2, "⭐⭐⭐ High": 3, "⭐⭐⭐⭐ Very High": 4, "⭐⭐⭐⭐⭐ Critical": 5}
        numeric_priority = priority_map[priority]

        # Convert frequency display to internal value
        frequency_map = {"One-time": None, "Daily": "daily", "Weekly": "weekly"}
        task_frequency = frequency_map[frequency]

        selected_pet = st.session_state.owner.pets[selected_pet_index]
        task = Task(
            title=task_title,
            category=category,
            duration_minutes=duration,
            priority=numeric_priority,
            frequency=task_frequency
        )
        selected_pet.add_task(task)
        frequency_text = f" ({frequency.lower()})" if task_frequency else ""
        st.success(f"✅ Task '{task_title}'{frequency_text} added to {selected_pet.name}!")
        st.balloons()
else:
    st.warning("⚠️ Please add pets first before creating tasks.")

# Display tasks by pet
if "owner" in st.session_state and st.session_state.owner:
    for pet in st.session_state.owner.pets:
        if pet.task_list:
            st.write(f"**Tasks for {pet.name} ({pet.type}):**")
            task_data = []
            for task in pet.task_list:
                priority_stars = "⭐" * task.priority
                frequency_display = task.frequency.title() if task.frequency else "One-time"
                task_data.append({
                    "Task": task.title,
                    "Category": task.category.title(),
                    "Duration": f"{task.duration_minutes}m",
                    "Priority": priority_stars,
                    "Frequency": frequency_display,
                    "Status": task.status.title()
                })
            st.table(task_data)

st.subheader("📅 Generate Daily Schedule")
st.caption("Generate and view your personalized pet care schedule.")

if st.button("🎯 Generate Schedule", type="primary", help="Create your personalized daily pet care plan"):
    if "scheduler" in st.session_state and st.session_state.scheduler:
        plan = st.session_state.scheduler.generate_daily_plan()
        if plan:
            st.success(f"✅ Generated schedule with {len(plan)} tasks!")
            st.balloons()
            with st.expander("📋 View Detailed Schedule", expanded=True):
                st.code(st.session_state.scheduler.explain_plan())
        else:
            st.info("ℹ️ No tasks scheduled. Add some tasks first or check available time.")
    else:
        st.error("❌ Please set up your owner profile first.")

# Display current schedule summary
if "scheduler" in st.session_state and st.session_state.scheduler and st.session_state.scheduler.planned_task_order:
    st.write("**📅 Today's Schedule:**")
    total_time = sum(task.duration_minutes for task in st.session_state.scheduler.planned_task_order)
    st.info(f"Scheduled {len(st.session_state.scheduler.planned_task_order)} tasks totaling {total_time} minutes")

    for i, task in enumerate(st.session_state.scheduler.planned_task_order, 1):
        priority_stars = "⭐" * task.priority
        st.write(f"{i}. **{task.title}** - {task.duration_minutes}m ({task.category}) - {priority_stars}")

    # Mark tasks as completed
    st.divider()
    st.subheader("✅ Mark Tasks Complete")
    completed_tasks = []
    for task in st.session_state.scheduler.planned_task_order:
        if st.button(f"✅ Complete: {task.title}", key=f"complete_{task.title}_{id(task)}"):
            task.mark_completed(scheduler=st.session_state.scheduler)
            completed_tasks.append(task.title)

    if completed_tasks:
        st.success(f"✅ Marked {len(completed_tasks)} task(s) as completed!")
        st.rerun()  # Refresh to update the schedule
