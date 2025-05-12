# B-LOGGER

A terminal-based logging application to track work tasks and hours.

## Features

- Create and manage work logs with timestamps
- Track hours worked on different tasks
- Mark tasks as completed in Q and Jira
- Add subtasks to main tasks
- View and edit existing logs
- Calculate total hours worked per day
- Support for custom dates
- Sprint-based log organization
  - View current sprint logs
  - View sprint history
  - Automatic sprint date calculation (every other Wednesday)
  - Distinct QI ticket tracking

## Sprint Features

- Sprints are 14 days long, ending every other Wednesday
- Current sprint view shows:
  - Distinct QI tickets (without duplicates)
  - All logs organized by date
- Sprint history shows:
  - All past sprints
  - Current sprint
  - Future sprints with logs
  - Logs organized by date within each sprint

## How to Input Hours

You can input hours in several formats:
- `1h`        - One hour
- `30m`       - Thirty minutes
- `1h 30m`    - One hour and thirty minutes
- `ongoing`   - For tasks still in progress

## Status Indicators

- ✅ - Task is completed
- ❌ - Task is not completed
- Status can be set for both Q and Jira separately

## Custom Dates

When creating a new log, you can use a custom date:
- Format: DD.MM.YYYY
- Example: 28.04.2024

## Keyboard Navigation

- Use arrow keys to navigate through input history
- Use backspace to delete characters
- Press Enter to confirm inputs

## Installation

1. Clone the repository
2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python b_logger.py
   ```

## Requirements

- Python 3.x
- Required packages (see requirements.txt):
  - blessed
  - python-dateutil
