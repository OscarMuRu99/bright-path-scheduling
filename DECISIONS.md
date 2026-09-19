# Decisions

## 1. Reading the situation

### Questions I would ask the owner first

1. Are paired lessons actually allowed?
   - The brief says lessons are one-to-one, but the data shows two students booked with the same tutor and room at the same time.
   - If paired lessons are allowed, I would probably model them as one lesson with multiple students instead of two separate bookings.

2. Does the six-booking daily limit include cancelled lessons?
   - For this implementation, I am assuming only non-cancelled bookings count. If cancelled lessons should count, I would change the daily-count filter, while still freeing their slots.

3. Can the centre ever open on Monday?
   - The brief says the centre is closed on Mondays, but there is a Monday lesson in the export. If exceptions are allowed, I would use an explicit opening-calendar exception instead of silently allowing every Monday.

4. What should happen when the tutor cancels close to the lesson?
   - The brief explains what happens when the family cancels, but not when the tutor cancels. The answer would determine who is charged or paid in a future cancellation workflow; it would not change that cancellation frees the slot.

5. What exactly counts as the tutor already being "told" their schedule?
   - The brief fixes tomorrow's schedule at 16:00 today. I would clarify whether delivery or acknowledgement also needs recording, so a future history table could distinguish a published schedule from one the tutor has actually received.

### Things that do not fully match

- Lessons are described as one-to-one, but there is an intentional "exam pair" in the data.
- The centre is supposed to be closed on Monday, but there is a Monday lesson.
- Tutors should have no more than six bookings per day, but T1 has seven on one day.
- The cancellation rules explain family cancellations, but not tutor cancellations.

### Assumptions for this implementation

- I will not treat paired lessons as a supported exception unless the owner confirms it.
- Cancelled lessons do not block the tutor, student, or room.
- I will not validate exact opening hours because the brief only says "mid-morning to mid-evening".
- The six-booking limit applies to non-cancelled bookings.
- Monday bookings will be rejected based on the stated operating rules.

## 2. Choosing what to build

### Features this tool could have

- Detect tutor conflicts.
- Detect room conflicts.
- Detect student conflicts.
- Enforce the six-booking daily tutor limit.
- Track cancellations and late cancellations.
- Keep a history of schedule changes after the cut-off.
- Notify tutors when their schedule changes.
- Show today's schedule in one view.

### Feature chosen

I will focus on preventing scheduling conflicts when creating a lesson.

I chose this because the data already shows several cases where tutors, students, or rooms end up scheduled in ways that should not happen.

For the time available, I think preventing bad bookings before they happen gives more value than trying to build several smaller features.

The feature will validate:

- tutor availability
- room availability
- student availability
- centre opening day
- maximum six non-cancelled bookings per tutor per day

### What I am not building

For this exercise, I am not implementing:

- WhatsApp notifications
- billing or cancellation charges
- automatic rescheduling
- paired-lesson pricing
- a user interface
- full schedule-change history

These are still useful features, but I would rather make the core scheduling validation clear, reliable, and testable first. This choice leaves the receptionist's cancellation/message delays, the tutor's uncertainty about the latest schedule, and the owner's requested today view unresolved. The immediate priority is the owner's explicit requirement that a student must never be booked in two places at once.

## 3. Design

### Data model

For this feature I only needed tutors and bookings.

A booking stores:

- lesson ID
- date
- start time
- duration
- student
- tutor
- room
- status
- cancellation information
- note

Tutors are stored separately and bookings reference them through `tutor_id`.

I kept the model close to the original spreadsheet export so it is easy to understand where the data came from.

### How I would handle schedule changes

The current feature only validates new bookings.

If I continued the project, I would not overwrite important schedule changes after the tutor has already received the schedule.

I would add a booking event or history table with events such as:

- created
- moved
- cancelled

That would let the system keep both the original schedule and what changed later. Each event would reference the lesson and record the previous and new date/time/tutor/room or status, when it changed, who changed it, and which published schedule it affected. A schedule published at the 16:00 cut-off would remain visible, with later changes shown separately. This is a proposed design, not an implemented history feature.

### Rules in the database vs application

The database handles basic integrity:

- unique lesson IDs
- valid tutor references
- valid booking status
- positive lesson duration

The application handles scheduling rules because they depend on other bookings and time ranges:

- tutor conflicts
- room conflicts
- student conflicts
- Monday closure
- six non-cancelled bookings per tutor per day
- 60 or 90 minute lesson duration

I kept these rules explicit in the application so they are easy to read, test and change if the owner clarifies the requirements.

### API

I implemented:

`POST /bookings`

It receives `lesson_id`, `date`, `start_time`, `duration_min`, `student`, `tutor_id`, and `room`. It returns the created booking with `201`, a business conflict with `409` and a `detail.code`/`detail.message`, or invalid request input with `422`. Dates must be valid `YYYY-MM-DD` and times local `HH:MM`. IDs already in the database return `LESSON_ID_EXISTS`.

Possible conflict or validation codes include:

- `TUTOR_CONFLICT`
- `ROOM_CONFLICT`
- `STUDENT_CONFLICT`
- `TUTOR_DAILY_LIMIT`
- `CENTRE_CLOSED`
- `INVALID_DURATION`
- `UNKNOWN_TUTOR`
- `LESSON_ID_EXISTS`

### Endpoint I decided not to build

I considered `POST /bookings/{lesson_id}/reschedule`, but decided not to build automatic rescheduling.

Choosing which tutor, room or family should be moved requires business priorities that are not defined in the brief.

I preferred to detect and explain the conflict instead of making a scheduling decision for the receptionist.

## 4. Reflection

### What I would build next

With another week, I would start by designing a stronger foundation for the system before adding more automation.

My first step would be to define a more complete database model for:

- students and families
- tutors
- rooms
- bookings
- opening days and hours
- tutor availability
- booking history and schedule changes
- cancellation rules
- pricing rules

I would use the client requirements and the operational rules in the brief as the starting point, making the important business rules explicit and testable instead of relying on people remembering them.

Once that foundation is clear, I would start designing an n8n workflow around it.

The idea would be to use n8n as the orchestration layer for incoming WhatsApp conversations, with an AI agent helping interpret requests and coordinating deterministic tools for specific responsibilities, for example:

- checking booking availability
- checking current pricing and cancellation rules
- creating or changing a booking
- notifying tutors when their schedule changes

I would keep the actual scheduling and pricing rules in deterministic application logic rather than inside the AI agent. The agent would use those capabilities instead of deciding the rules itself.

If a request is ambiguous, conflicts with a rule, or requires a decision that the system cannot safely make, the workflow should create a clear human handoff instead of guessing.

I would not try to build the entire automation in that week. I would focus first on getting the data model, business rules, API boundaries and human-handoff flow right, and then automate the workflow on top of that.

I prepared a static owner-view concept in `docs/OWNER_VIEW_CONCEPT.md`. It uses the supplied March 10 records to show booked lessons, a known free room and the existing tutor conflict, and proposes a future `GET /schedule?date=...` contract. It is deliberately labelled as a concept rather than implemented functionality because the export does not identify all six rooms or exact opening hours.

### What I know is still weak

The current implementation is intentionally small.

Some things I would improve in a production version are:

- richer date/time modelling, including an explicit centre timezone
- explicit room records instead of treating the room as a string
- concurrency protection if multiple people create bookings at the same time
- full booking history instead of only storing the current state
- student IDs instead of matching student names as strings

The current solution also does not implement the cancellation or post-cut-off workflows because I kept the scope focused on preventing invalid new bookings.

### Dates used

The implementation does not depend on the real current date.

The examples and tests use fixed dates from the week provided in the seed data.

### AI usage

I used an AI assistant throughout the exercise as a reasoning and pair-programming tool.

I used it to:

- review my interpretation of the brief
- challenge assumptions
- identify edge cases
- review the data model
- help draft implementation code
- help design and review tests
- troubleshoot issues while running the project
- review documentation

I made the final scope and design decisions, reviewed the generated suggestions, ran the code and tests myself, and only kept code that I understood and could explain.

### One AI suggestion I rejected

One option we discussed was automatic conflict resolution or rescheduling.

I decided not to implement it because there was not enough information in the brief to know which tutor, room, student or lesson should be moved.

I think rejecting that idea was the safer choice because the tool should not silently invent business priorities that the client never defined.

### Final review corrections

The final review added regression tests and small fixes within the chosen booking-validation feature: malformed or incomplete requests now return 422, existing lesson IDs return a conflict, and overlap checks also consider lessons crossing midnight. SQLite connections close explicitly after each transaction. Validation and insertion now run in one `BEGIN IMMEDIATE` transaction, so an error rolls back the write and concurrent requests cannot both pass conflict validation. Database failures return 503. The architecture and seed records are unchanged. A production deployment with multiple application instances would still need a server database and database-level conflict protection.
