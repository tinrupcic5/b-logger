   ```bash
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║  ███████████             ████                                                ║
║ ░░███░░░░░███           ░░███                                                ║
║  ░███    ░███            ░███   ██████   ███████  ███████  ██████  ████████  ║
║  ░██████████  ██████████ ░███  ███░░███ ███░░███ ███░░███ ███░░███░░███░░███ ║
║  ░███░░░░░███░░░░░░░░░░  ░███ ░███ ░███░███ ░███░███ ░███░███████  ░███ ░░░  ║
║  ░███    ░███            ░███ ░███ ░███░███ ░███░███ ░███░███░░░   ░███      ║
║  ███████████             █████░░██████ ░░███████░░███████░░██████  █████     ║
║ ░░░░░░░░░░░             ░░░░░  ░░░░░░   ░░░░░███ ░░░░░███ ░░░░░░  ░░░░░      ║
║                                         ███ ░███ ███ ░███                    ║
║                                        ░░██████ ░░██████                     ║
║                                         ░░░░░░   ░░░░░░                      ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝ 
   ```
A terminal-based time logging application that helps you track your work tasks and their status.

## Features

- 📝 Create and manage work logs with timestamps
- ⏰ Track hours spent on tasks
- ✅ Track 1 and 2 status for each task
- 📋 Add subtasks to your logs
- 📅 Support for custom dates
- 🎨 Retro-style terminal interface
- 💾 Persistent storage in JSON format

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/b-logger.git
cd b-logger
```

2. Make the run script executable:
```bash
chmod +x run.sh
```

3. Add the alias to your shell configuration file (~/.zshrc or ~/.bashrc):
```bash
alias b-logger="/path/to/b-logger/run.sh"
```

4. Reload your shell configuration:
```bash
source ~/.zshrc  # or source ~/.bashrc
```

## Usage

Run the tool by typing:
```bash
b-logger
```

### Creating a New Log

1. Select option 1 from the menu
2. Choose whether to use today's date or a custom date
3. Enter your task/ticket information
4. Enter the hours spent
5. Update 1 and 2 status (x for ❌, c for ✅)
6. Optionally add subtasks

### Viewing Logs

- Select option 2 to view all logs
- Logs are sorted by date (oldest first)
- Each log shows:
  - Timestamp
  - Ticket/Task
  - Hours spent
  - 1 and 2 status
  - Subtasks (if any)

### Editing Logs

1. Select option 3
2. Choose the log number to edit
3. Update the status and subtasks as needed

### Deleting Logs

1. Select option 4
2. Choose the log number to delete
3. Confirm deletion

## Data Storage

- Logs are stored in `logs.json` in the same directory as the script
- The file is automatically created when you add your first log
- Logs are sorted by date when saved

## Requirements

- Python 3.x
- Required Python packages (automatically installed):
  - blessed
  - python-dateutil

## License
