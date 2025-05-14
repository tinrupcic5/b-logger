#!/usr/bin/env python3

import os
import sys
import json
import signal
import readline
from datetime import datetime, timedelta
from blessed import Terminal
from dateutil import parser

class BLogger:
    def __init__(self):
        self.term = Terminal()
        self.logs = []
        self.current_log = None
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.log_file = os.path.join(self.script_dir, "logs.json")
        self.load_logs()
        self.banner = None
        self.load_banner()
        self.running = True
        
        # Set up signal handler for Ctrl+C
        signal.signal(signal.SIGINT, self.handle_exit)
        
        # Configure readline for better input handling
        readline.parse_and_bind('bind ^[[D backward-char')
        readline.parse_and_bind('bind ^[[C forward-char')
        readline.parse_and_bind('bind ^[[A previous-history')
        readline.parse_and_bind('bind ^[[B next-history')

    def handle_exit(self, signum, frame):
        """Handle clean exit on Ctrl+C"""
        print("\nExiting B-LOGGER...")
        self.running = False
        sys.exit(0)

    def load_banner(self):
        try:
            banner_path = os.path.join(self.script_dir, 'banner.txt')
            with open(banner_path, 'r') as f:
                self.banner = f.read()
        except FileNotFoundError:
            self.banner = "B-LOGGER\nYour Retro B-logging Companion"

    def display_banner(self):
        print(self.term.clear)
        print(self.term.move_y(0))
        print(self.term.cyan(self.banner))
        print("\n")  # Add some space after banner

    def load_logs(self):
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r') as f:
                self.logs = json.load(f)

    def save_logs(self):
        # Sort logs by date before saving (oldest first)
        self.logs.sort(key=lambda x: datetime.strptime(x['timestamp'].split()[0], "%d.%m.%Y"))
        with open(self.log_file, 'w') as f:
            json.dump(self.logs, f, indent=2)

    def create_new_log(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Create New Log" + self.term.normal)
        
        # Ask about custom date
        use_custom_date = input("Do you want to use a different date? (y/n): ").lower()
        if use_custom_date == 'y':
            while True:
                try:
                    custom_date = input("Enter date (DD.MM.YYYY): ")
                    # Validate date format
                    datetime.strptime(custom_date, "%d.%m.%Y")
                    current_time = f"{custom_date} {datetime.now().strftime('%H:%M:%S')}"
                    break
                except ValueError:
                    print("Invalid date format. Please use DD.MM.YYYY (e.g., 23.04.2024)")
        else:
            current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        
        ticket = input("Enter your log here: ")
        hours = input("Enter hours (e.g., 1h 30m or just 30m): ")
        
        self.current_log = {
            "timestamp": current_time,
            "ticket": ticket,
            "hours": hours,
            "q_status": "❌",
            "jira_status": "❌",
            "subtasks": []
        }
        
        self.update_status()
        self.logs.append(self.current_log)
        self.save_logs()

    def update_status(self):
        print(self.term.clear)
        print(f"Current log: {self.current_log['ticket']} - {self.current_log['hours']} hours")
        
        # Ask if user wants to update hours
        update_hours = input("Do you want to update hours? (y/n): ").lower()
        if update_hours == 'y':
            new_hours = input("Enter new hours: ")
            self.current_log["hours"] = new_hours
        
        q_status = input("Update Q log status (x for ❌, c for ✅): ").lower()
        jira_status = input("Update Jira log status (x for ❌, c for ✅): ").lower()
        
        self.current_log["q_status"] = "✅" if q_status == "c" else "❌"
        self.current_log["jira_status"] = "✅" if jira_status == "c" else "❌"
        
        while True:
            subtask = input("Add subtask? (y/n): ").lower()
            if subtask != "y":
                break
                
            subtask_desc = input("Enter subtask description: ")
            self.current_log["subtasks"].append(subtask_desc)
            print(f"Added subtask: {subtask_desc}")
            print("Current subtasks:")
            for i, task in enumerate(self.current_log["subtasks"], 1):
                print(f"{i}. {task}")
            print()  # Add empty line for better readability

    def parse_hours(self, hours_str):
        """Parse hours string into total minutes"""
        if not hours_str or hours_str.lower() == 'ongoing':
            return 0
        
        total_minutes = 0
        hours_str = hours_str.lower().replace('hours', '').strip()
        
        # Handle hours
        if 'h' in hours_str:
            hours_part = hours_str.split('h')[0]
            try:
                total_minutes += int(hours_part.strip()) * 60
            except ValueError:
                pass
        elif hours_str.isdigit():
            # Handle case like "1 hours"
            try:
                total_minutes += int(hours_str.strip()) * 60
            except ValueError:
                pass
        
        # Handle minutes
        if 'm' in hours_str:
            minutes_part = hours_str.split('m')[0]
            if 'h' in minutes_part:
                minutes_part = minutes_part.split('h')[-1]
            try:
                total_minutes += int(minutes_part.strip())
            except ValueError:
                pass
        
        return total_minutes

    def format_hours(self, total_minutes):
        """Format total minutes into hours and minutes string"""
        if total_minutes == 0:
            return ""
        hours = total_minutes // 60
        minutes = total_minutes % 60
        if minutes == 0:
            return f"{hours}h"
        return f"{hours}h {minutes}m"

    def display_logs(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Log History" + self.term.normal)
        
        # Sort logs by date before displaying (oldest first)
        sorted_logs = sorted(self.logs, key=lambda x: datetime.strptime(x['timestamp'].split()[0], "%d.%m.%Y"))
        
        current_date = None
        day_total_minutes = 0
        
        for i, log in enumerate(sorted_logs):
            log_date = log['timestamp'].split()[0]
            
            # Add separator and total hours if date changes
            if current_date is not None and log_date != current_date:
                total_hours = self.format_hours(day_total_minutes)
                if total_hours:
                    # Check if total is exactly 8h
                    if day_total_minutes == 480:  # 8 hours = 480 minutes
                        print(f"\nTotal for {current_date}: {self.term.green(total_hours)}")
                    else:
                        print(f"\nTotal for {current_date}: {self.term.red(total_hours)}")
                    print("-" * 72)  # Separator line after total
                print("-" * 72)  # Separator line between days
                day_total_minutes = 0
            
            current_date = log_date
            print(f"{i+1}. {log['timestamp']} {log['ticket']} - {log['hours']} hours [Q-> {log['q_status']}] [J-> {log['jira_status']}]")
            if log['subtasks']:
                for subtask in log['subtasks']:
                    print(f"   └─ {subtask}")
            
            # Add to day total
            day_total_minutes += self.parse_hours(log['hours'])
        
        # Add total for the last day
        if day_total_minutes > 0:
            total_hours = self.format_hours(day_total_minutes)
            # Check if total is exactly 8h
            if day_total_minutes == 480:  # 8 hours = 480 minutes
                print(f"\nTotal for {current_date}: {self.term.green(total_hours)}")
            else:
                print(f"\nTotal for {current_date}: {self.term.red(total_hours)}")
            print("-" * 72)  # Separator line after total

    def edit_log(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Edit Log" + self.term.normal)
        self.display_logs()
        try:
            log_index = int(input("\nEnter log number to edit (0 to cancel): ")) - 1
            if log_index == -1:
                return
            
            if 0 <= log_index < len(self.logs):
                print(self.term.clear)  # Clear screen after log selection
                print(self.term.move_y(0) + self.term.black_on_white + f"Editing Log {log_index + 1}" + self.term.normal)
                self.current_log = self.logs[log_index]
                
                # Ask if user wants to edit description
                edit_desc = input("Do you want to edit the description? (y/n): ").lower()
                if edit_desc == 'y':
                    print(f"\nCurrent description: {self.current_log['ticket']}")
                    new_desc = input("Enter new description: ")
                    if new_desc.strip():  # Only update if new description is not empty
                        self.current_log["ticket"] = new_desc
                
                self.update_status()
                self.logs[log_index] = self.current_log
                self.save_logs()
        except ValueError:
            print("Invalid input")

    def delete_log(self):
        print(self.term.clear)
        self.display_logs()
        try:
            log_index = int(input("Enter log number to delete (0 to cancel): ")) - 1
            if log_index == -1:
                return
            
            if 0 <= log_index < len(self.logs):
                confirm = input(f"Are you sure you want to delete log {log_index + 1}? (y/n): ").lower()
                if confirm == 'y':
                    deleted_log = self.logs.pop(log_index)
                    print(f"Deleted log: {deleted_log['ticket']} - {deleted_log['hours']} hours")
                    self.save_logs()
                    input("\nPress Enter to continue...")
        except ValueError:
            print("Invalid input")
            input("\nPress Enter to continue...")

    def reset_screen(self):
        """Clear screen and show banner"""
        print(self.term.clear)
        self.display_banner()

    def display_help(self):
        """Display help information"""
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "B-LOGGER Help" + self.term.normal)
        print("\n" + self.term.underline + "Main Features:" + self.term.normal)
        print("1. Create and manage work logs with timestamps")
        print("2. Track hours worked on different tasks")
        print("3. Mark tasks as completed in 1 and 2")
        print("4. Add subtasks to main tasks")
        print("5. View and edit existing logs")
        print("6. Calculate total hours worked per day")
        print("7. Support for custom dates")
        
        print("\n" + self.term.underline + "How to Input Hours:" + self.term.normal)
        print("You can input hours in several formats:")
        print("- 1h        - One hour")
        print("- 30m       - Thirty minutes")
        print("- 1h 30m    - One hour and thirty minutes")
        print("- ongoing   - For tasks still in progress")
        
        print("\n" + self.term.underline + "Examples:" + self.term.normal)
        print("2h        # 2 hours")
        print("45m       # 45 minutes")
        print("1h 15m    # 1 hour and 15 minutes")
        print("2h 30m    # 2 hours and 30 minutes")
        print("ongoing   # Task in progress (not counted in totals)")
        
        print("\n" + self.term.underline + "Status Indicators:" + self.term.normal)
        print("✅ - Task is completed")
        print("❌ - Task is not completed")
        print("Status can be set for both 1 and 2 separately")
        
        print("\n" + self.term.underline + "Custom Dates:" + self.term.normal)
        print("When creating a new log, you can use a custom date")
        print("Format: DD.MM.YYYY")
        print("Example: 28.04.2024")
        
        print("\n" + self.term.underline + "Keyboard Navigation:" + self.term.normal)
        print("- Use arrow keys to navigate through input history")
        print("- Use backspace to delete characters")
        print("- Press Enter to confirm inputs")
        
        input("\nPress Enter to return to main menu...")

    def mark_as_checked(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Mark Log as Checked" + self.term.normal)
        self.display_logs()
        
        # Ask which status to update
        while True:
            status_choice = input("\nWhich status do you want to update? (q/j/b for Q/Jira/Both): ").lower()
            if status_choice in ['q', 'j', 'b']:
                break
            print("Invalid choice. Please enter 'q' for Q, 'j' for Jira, or 'b' for Both.")
        
        try:
            log_index = int(input("\nEnter log number to mark as checked (0 to cancel): ")) - 1
            if log_index == -1:
                return
            
            if 0 <= log_index < len(self.logs):
                if status_choice in ['q', 'b']:
                    self.logs[log_index]["q_status"] = "✅"
                if status_choice in ['j', 'b']:
                    self.logs[log_index]["jira_status"] = "✅"
                
                status_updated = []
                if status_choice in ['q', 'b']:
                    status_updated.append("Q")
                if status_choice in ['j', 'b']:
                    status_updated.append("Jira")
                
                print(f"\nMarked log {log_index + 1} as checked for {', '.join(status_updated)}.")
                self.save_logs()
                
                # Ask if user wants to mark another log
                while True:
                    another = input("\nDo you want to mark another log as checked? (y/n): ").lower()
                    if another == 'y':
                        self.mark_as_checked()
                        break
                    elif another == 'n':
                        break
                    else:
                        print("Please enter 'y' or 'n'")
        except ValueError:
            print("Invalid input")
            input("\nPress Enter to continue...")

    def mark_as_unchecked(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Mark Log as Unchecked" + self.term.normal)
        self.display_logs()
        
        # Ask which status to update
        while True:
            status_choice = input("\nWhich status do you want to update? (q/j/b for Q/Jira/Both): ").lower()
            if status_choice in ['q', 'j', 'b']:
                break
            print("Invalid choice. Please enter 'q' for Q, 'j' for Jira, or 'b' for Both.")
        
        try:
            log_index = int(input("\nEnter log number to mark as unchecked (0 to cancel): ")) - 1
            if log_index == -1:
                return
            
            if 0 <= log_index < len(self.logs):
                if status_choice in ['q', 'b']:
                    self.logs[log_index]["q_status"] = "❌"
                if status_choice in ['j', 'b']:
                    self.logs[log_index]["jira_status"] = "❌"
                
                status_updated = []
                if status_choice in ['q', 'b']:
                    status_updated.append("Q")
                if status_choice in ['j', 'b']:
                    status_updated.append("Jira")
                
                print(f"\nMarked log {log_index + 1} as unchecked for {', '.join(status_updated)}.")
                self.save_logs()
                
                # Ask if user wants to mark another log
                while True:
                    another = input("\nDo you want to mark another log as unchecked? (y/n): ").lower()
                    if another == 'y':
                        self.mark_as_unchecked()
                        break
                    elif another == 'n':
                        break
                    else:
                        print("Please enter 'y' or 'n'")
        except ValueError:
            print("Invalid input")
            input("\nPress Enter to continue...")

    def edit_subtasks(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Edit Subtasks" + self.term.normal)
        self.display_logs()
        try:
            log_index = int(input("\nEnter log number to edit subtasks (0 to cancel): ")) - 1
            if log_index == -1:
                return
            
            if 0 <= log_index < len(self.logs):
                log = self.logs[log_index]
                if not log['subtasks']:
                    print("\nThis log has no subtasks.")
                    input("\nPress Enter to continue...")
                    return
                
                print(f"\nCurrent subtasks for log {log_index + 1}:")
                for i, subtask in enumerate(log['subtasks'], 1):
                    print(f"{i}. {subtask}")
                
                while True:
                    subtask_input = input("\nEnter subtask number to edit (press Enter to finish): ").strip()
                    if not subtask_input:  # If user just presses Enter
                        break
                    
                    try:
                        subtask_index = int(subtask_input) - 1
                        if 0 <= subtask_index < len(log['subtasks']):
                            print(f"\nCurrent subtask: {log['subtasks'][subtask_index]}")
                            new_subtask = input("Enter new subtask description: ")
                            if new_subtask.strip():
                                log['subtasks'][subtask_index] = new_subtask
                                print("Subtask updated successfully!")
                            else:
                                print("Subtask description cannot be empty!")
                        else:
                            print("Invalid subtask number!")
                    except ValueError:
                        print("Please enter a valid number!")
                
                self.save_logs()
                print("\nChanges saved successfully!")
                input("\nPress Enter to continue...")
        except ValueError:
            print("Invalid input")
            input("\nPress Enter to continue...")

    def get_sprint_dates(self, sprint_number):
        """Get start and end dates for a specific sprint number (0 is current sprint, -1 is previous, etc.)"""
        # Define the first sprint start date
        first_sprint_start = datetime(2025, 4, 30)
        
        # Calculate sprint dates based on sprint number
        sprint_start = first_sprint_start + timedelta(days=14 * sprint_number)
        sprint_end = sprint_start + timedelta(days=13)  # Sprint ends 13 days after start
        
        return sprint_start, sprint_end

    def view_sprint_history(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Sprint History" + self.term.normal)
        
        if not self.logs:
            print("\nNo logs found.")
            input("\nPress Enter to continue...")
            return
            
        # Find the earliest and latest log dates
        log_dates = [datetime.strptime(log['timestamp'].split()[0], "%d.%m.%Y") for log in self.logs]
        earliest_date = min(log_dates)
        latest_date = max(log_dates)
        
        # Calculate sprint numbers
        first_sprint_start = datetime(2025, 4, 30)
        days_since_first_sprint = (earliest_date - first_sprint_start).days
        sprints_back = abs(days_since_first_sprint // 14)  # How many sprints before April 30, 2025
        
        days_since_first_sprint = (latest_date - first_sprint_start).days
        sprints_forward = days_since_first_sprint // 14  # How many sprints after April 30, 2025
        
        # Show sprints from earliest to latest with logs
        for i in range(-sprints_back, sprints_forward + 1):
            sprint_start, sprint_end = self.get_sprint_dates(i)
            
            # Filter logs within sprint period
            sprint_logs = []
            for log in self.logs:
                log_date = datetime.strptime(log['timestamp'].split()[0], "%d.%m.%Y")
                if sprint_start <= log_date <= sprint_end:
                    sprint_logs.append(log)
            
            # Show sprint if it has logs or is in the past
            if sprint_logs or sprint_end < datetime.now():
                print(f"\nSprint Period: {sprint_start.strftime('%d.%m.%Y')} - {sprint_end.strftime('%d.%m.%Y')}")
                
                if sprint_logs:
                    # Sort logs by date
                    sprint_logs.sort(key=lambda x: datetime.strptime(x['timestamp'].split()[0], "%d.%m.%Y"))
                    
                    # Group logs by date
                    current_date = None
                    for log in sprint_logs:
                        log_date = log['timestamp'].split()[0]
                        if current_date != log_date:
                            current_date = log_date
                            print(f"\n  {self.term.yellow(current_date)}")
                        print(f"    {self.term.cyan(log['ticket'])}")
                else:
                    print("  No logs found for this sprint")
                
                print("-" * 72)
        
        input("\nPress Enter to continue...")

    def view_sprint_logs(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Current Sprint Logs" + self.term.normal)
        
        sprint_start, sprint_end = self.get_sprint_dates(0)
        print(f"\nSprint Period: {sprint_start.strftime('%d.%m.%Y')} - {sprint_end.strftime('%d.%m.%Y')}")
        print("-" * 72)
        
        # Filter logs within sprint period
        sprint_logs = []
        for log in self.logs:
            log_date = datetime.strptime(log['timestamp'].split()[0], "%d.%m.%Y")
            if sprint_start <= log_date <= sprint_end:
                sprint_logs.append(log)
        
        if not sprint_logs:
            print("\nNo logs found for the current sprint.")
            input("\nPress Enter to continue...")
            return
        
        # Get distinct QI- logs
        qi_logs = {}  # Use dict to store unique QI numbers
        for log in sprint_logs:
            if log['ticket'].startswith('QI-'):
                # Extract QI number (everything before the first space or [)
                qi_number = log['ticket'].split()[0].split('[')[0]
                # Keep the version with [Q] if it exists, otherwise keep the first one
                if '[Q]' in log['ticket'] or qi_number not in qi_logs:
                    qi_logs[qi_number] = log['ticket']
        
        # Display QI logs first
        if qi_logs:
            print("\nQI Tickets:")
            for qi_log in sorted(qi_logs.values()):
                print(f"  {self.term.cyan(qi_log)}")
            print("-" * 72)
        
        # Display all logs sorted by date
        print("\nOther Logs:")
        # Sort logs by date
        sprint_logs.sort(key=lambda x: datetime.strptime(x['timestamp'].split()[0], "%d.%m.%Y"))
        
        # Group logs by date
        current_date = None
        for log in sprint_logs:
            log_date = log['timestamp'].split()[0]
            if current_date != log_date:
                current_date = log_date
                print(f"\n  {self.term.yellow(current_date)}")
            print(f"    {self.term.cyan(log['ticket'])}")
        
            input("\nPress Enter to continue...")

    def run(self):
        self.reset_screen()
        while self.running:
            print(self.term.black_on_white + "B-Logger" + self.term.normal)
            print("\n1. Create new log")
            print("2. View logs")
            print("3. Edit log")
            print("4. Delete log")
            print("5. Mark as checked")
            print("6. Mark as unchecked")
            print("7. Edit subtasks")
            print("8. View current sprint")
            print("9. View sprint history")
            print("10. Help")
            print("11. Exit")
            
            try:
                choice = input("\nEnter your choice (1-11): ")
                if choice == "1":
                    self.create_new_log()
                    self.reset_screen()
                elif choice == "2":
                    self.display_logs()
                    input("\nPress Enter to continue...")
                    self.reset_screen()
                elif choice == "3":
                    self.edit_log()
                    self.reset_screen()
                elif choice == "4":
                    self.delete_log()
                    self.reset_screen()
                elif choice == "5":
                    self.mark_as_checked()
                    self.reset_screen()
                elif choice == "6":
                    self.mark_as_unchecked()
                    self.reset_screen()
                elif choice == "7":
                    self.edit_subtasks()
                    self.reset_screen()
                elif choice == "8":
                    self.view_sprint_logs()
                    self.reset_screen()
                elif choice == "9":
                    self.view_sprint_history()
                    self.reset_screen()
                elif choice == "10":
                    self.display_help()
                    self.reset_screen()
                elif choice == "11":
                    self.running = False
                    break
            except KeyboardInterrupt:
                print("\nExiting B-LOGGER...")
                self.running = False
                break

if __name__ == "__main__":
    logger = BLogger()
    logger.run() 