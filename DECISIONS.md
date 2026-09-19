# Decisions

## 1. Reading the situation

### Questions I would ask the owner first

1. Are paired lessons actually allowed?
   - The brief says lessons are one-to-one, but the data shows two students booked with the same tutor and room at the same time.
   - If paired lessons are allowed, I would probably model them as one lesson with multiple students instead of two separate bookings.

2. Does the six-booking daily limit include cancelled lessons?
   - For this implementation, I am assuming only active bookings count.

3. Can the centre ever open on Monday?
   - The brief says the centre is closed on Mondays, but there is a Monday lesson in the export.

4. What should happen when the tutor cancels close to the lesson?
   - The brief explains what happens when the family cancels, but not when the tutor cancels.

5. What exactly counts as the tutor already being "told" their schedule?
   - I would need this clarified to know when a change should be treated as a normal update or as a post-cut-off change.

### Things that do not fully match

- Lessons are described as one-to-one, but there is an intentional "exam pair" in the data.
- The centre is supposed to be closed on Monday, but there is a Monday lesson.
- Tutors should have no more than six bookings per day, but T1 has seven on one day.
- The cancellation rules explain family cancellations, but not tutor cancellations.

### Assumptions for this implementation

- I will not treat paired lessons as a supported exception unless the owner confirms it.
- Cancelled lessons do not block the tutor, student, or room.
- I will not validate exact opening hours because the brief only says "mid-morning to mid-evening".
- The six-booking limit applies to active bookings.
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

### Feature chosen

I will focus on preventing scheduling conflicts when creating a lesson.

I chose this because the data already shows several cases where tutors, students, or rooms end up scheduled in ways that should not happen.

For the time available, I think preventing bad bookings before they happen gives more value than trying to build several smaller features.

The feature will validate:

- tutor availability
- room availability
- student availability
- centre opening day
- maximum six active bookings per tutor per day

### What I am not building

For this exercise, I am not implementing:

- WhatsApp notifications
- billing or cancellation charges
- automatic rescheduling
- paired-lesson pricing
- a user interface
- full schedule-change history

These are still useful features, but I would rather make the core scheduling validation clear, reliable, and testable first.