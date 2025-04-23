# B-Logger 🚀

A terminal-based time logging application that helps you track your work tasks and their status.

## Features

- Create new logs with ticket numbers and descriptions
- Track 1 and 2 status for each log
- Add subtasks to logs
- View log history
- Edit existing logs
- Persistent storage of logs

## Installation

1. Make sure you have Python 3.6+ installed
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the application:
```bash
python b_logger.py
```

### Creating a New Log

1. Select option 1 from the main menu
2. Enter the ticket number (e.g., JI-12345)
3. Enter the description
4. Update the 1 and 2 status:
   - Press 'x' for ❌
   - Press 'c' for ✅
5. Optionally add subtasks by pressing 'y' when prompted

### Viewing Logs

Select option 2 from the main menu to view all logs and their subtasks.

### Editing Logs

1. Select option 3 from the main menu
2. Choose the log number you want to edit
3. Update the status and subtasks as needed

## Log Format

Logs are stored in the following format:
```
23.4.2025 09:50:00  JI-12345 - Implement Advanced Sorting Logic ❌ ❌
```

The status indicators represent:
- First ❌/✅: 1 log status
- Second ❌/✅: 2 log status 
