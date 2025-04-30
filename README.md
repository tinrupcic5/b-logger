# B-LOGGER

A terminal-based logging application for tracking work hours and tasks.

## Features

- Create and manage work logs with timestamps
- Track hours worked on different tasks
- Mark tasks as completed in 1 and 2
- Add subtasks to main tasks
- View and edit existing logs
- Calculate total hours worked per day
- Support for custom dates

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/b-logger.git
cd b-logger
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Make the script executable:
```bash
chmod +x b_logger.py
```

## Usage

Run the application:
```bash
./b_logger.py
```

### Main Menu Options

1. **Create new log**
   - Create a new work log entry
   - Option to use custom date
   - Track hours and task status

2. **View logs**
   - Display all logs sorted by date
   - Shows total hours worked per day
   - Includes subtasks and completion status

3. **Edit log**
   - Modify existing log entries
   - Update hours, status, or subtasks

4. **Delete log**
   - Remove unwanted log entries

5. **Exit**
   - Close the application

### How to Input Hours

When creating or editing a log, you can input hours in several formats:
- `1h` - One hour
- `30m` - Thirty minutes
- `1h 30m` - One hour and thirty minutes
- `ongoing` - For tasks still in progress

Examples:
```
2h        # 2 hours
45m       # 45 minutes
1h 15m    # 1 hour and 15 minutes
2h 30m    # 2 hours and 30 minutes
ongoing   # Task in progress (not counted in totals)
```

### Status Indicators

- ✅ - Task is completed
- ❌ - Task is not completed

Status can be set for both 1 and 2 separately.

### Subtasks

You can add multiple subtasks to any main task. They will be displayed indented under the main task in the log view.

### Daily Totals

The application automatically calculates and displays the total hours worked for each day at the end of that day's logs. The total is shown in the format:
```
Total for DD.MM.YYYY: Xh Ym
```

### Custom Dates

When creating a new log, you can choose to use a custom date instead of the current date. The date should be entered in the format:
```
DD.MM.YYYY
```
Example: `28.04.2024`

## Data Storage

All logs are stored in `logs.json` in the application directory. The file is automatically created when you make your first log entry.

## Keyboard Navigation

- Use arrow keys to navigate through input history
- Use backspace to delete characters
- Press Enter to confirm inputs

## Requirements

- Python 3.x
- blessed
- dateutil

## License

MIT License