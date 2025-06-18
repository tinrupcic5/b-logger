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
        self.settings_file = os.path.join(self.script_dir, "settings.json")
        self.scripts_file = os.path.join(self.script_dir, "scripts.json")
        self.running = True
        self.load_settings()
        self.load_logs()
        self.load_scripts()
        self.banner = None
        self.load_banner()
        self.links = self.load_links()
        self.input_history = []
        self.history_index = 0
        
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
        
        # Save to main logs file
        with open(self.log_file, 'w') as f:
            json.dump(self.logs, f, indent=2)
            
        # Save to backup file
        backup_file = os.path.join(self.script_dir, "backup", "logs_backup.json")
        with open(backup_file, 'w') as f:
            json.dump(self.logs, f, indent=2)

    def create_new_log(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Create New Log" + self.term.normal)
        
        # Ask about custom date
        while True:
            use_custom_date = input("Do you want to use a different date? (y/n): ").lower()
            if use_custom_date in ['0', 'exit']:
                return
            if use_custom_date in ['y', 'n']:
                break
            print("Invalid choice. Please enter 'y', 'n', '0', or 'exit'")
        
        if use_custom_date == 'y':
            while True:
                try:
                    custom_date = input("Enter date (DD.MM.YYYY) or 0/exit to cancel: ")
                    if custom_date.lower() in ['0', 'exit']:
                        return
                    # Validate date format
                    datetime.strptime(custom_date, "%d.%m.%Y")
                    current_time = f"{custom_date} {datetime.now().strftime('%H:%M:%S')}"
                    break
                except ValueError:
                    print("Invalid date format. Please use DD.MM.YYYY (e.g., 23.04.2024)")
        
        else:
            current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        
        ticket = input("Enter your log here: ")
        if ticket.lower() in ['0', 'exit']:
            return
        
        hours = input("Enter hours (e.g., 1h 30m or just 30m): ")
        if hours.lower() in ['0', 'exit']:
            return
        
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
            log_index = int(input("\nEnter log number to edit (0 to exit): ")) - 1
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
            log_index = int(input("Enter log number to delete (0 to exit): ")) - 1
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
        print("3. Mark tasks as completed in multiple systems")
        print("4. Add subtasks to main tasks")
        print("5. View and edit existing logs")
        print("6. Calculate total hours worked per workday")
        print("7. Support for custom dates")
        print("8. Sprint-based log organization")
        print("9. Customizable log types and sprint settings")
        print("10. Workday-based statistics and reporting")
        
        print("\n" + self.term.underline + "Settings:" + self.term.normal)
        print("You can customize:")
        print("- Log Types: Add, edit, or remove different types of logs")
        print("  Each log type can track its own completion status")
        print("  Example: Q, Jira, GitHub, etc.")
        print("  Custom prefixes for each type")
        print("- Sprint Configuration: Set sprint start date and duration")
        print("Access settings from the main menu (option 10)")
        
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
        print("Each log type can have its own completion status")
        print("Example: A task can be completed in Q but not in Jira")
        
        print("\n" + self.term.underline + "Statistics:" + self.term.normal)
        print("- Shows data for the last 10 workdays")
        print("- Excludes weekends automatically")
        print("- Displays completion status for each log type")
        print("- Shows hours worked per workday")
        print("- Lists incomplete tasks by type")
        print("- Visual charts for hours and logs per day")
        
        print("\n" + self.term.underline + "Custom Dates:" + self.term.normal)
        print("When creating a new log, you can use a custom date")
        print("Format: DD.MM.YYYY")
        print("Example: 28.04.2024")
        
        print("\n" + self.term.underline + "Sprint Features:" + self.term.normal)
        print("- View current sprint logs")
        print("- View sprint history")
        print("- Automatic sprint date calculation")
        print("- Distinct ticket tracking")
        print("- Sprint duration and start date configuration")
        
        print("\n" + self.term.underline + "Keyboard Navigation:" + self.term.normal)
        print("- Use arrow keys to navigate through input history")
        print("- Use backspace to delete characters")
        print("- Press Enter to confirm inputs")
        print("- Press 0 or type 'exit' to return to previous menu")
        print("- Press Ctrl+C to exit the program")
        
        print("\n" + self.term.underline + "Tips:" + self.term.normal)
        print("- Use settings to customize log types and sprint configuration")
        print("- Add subtasks to better organize your work")
        print("- Mark tasks as checked/unchecked to track progress")
        print("- View sprint history to see past work")
        print("- Use custom dates for historical entries")
        print("- Check statistics to monitor your work patterns")
        
        input("\nPress Enter to return to main menu...")

    def mark_as_checked(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Mark Log as Checked" + self.term.normal)
        self.display_logs()
        
        # Ask which status to update
        while True:
            status_choice = input("\nWhich status do you want to update? (q/j/b for Q/Jira/Both, 0 to exit): ").lower()
            if status_choice == '0':
                return
            if status_choice in ['q', 'j', 'b']:
                break
            print("Invalid choice. Please enter 'q' for Q, 'j' for Jira, 'b' for Both, or '0' to exit.")
        
        try:
            log_index = int(input("\nEnter log number to mark as checked (0 to exit): ")) - 1
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
            status_choice = input("\nWhich status do you want to update? (q/j/b for Q/Jira/Both, 0 to exit): ").lower()
            if status_choice == '0':
                return
            if status_choice in ['q', 'j', 'b']:
                break
            print("Invalid choice. Please enter 'q' for Q, 'j' for Jira, 'b' for Both, or '0' to exit.")
        
        try:
            log_index = int(input("\nEnter log number to mark as unchecked (0 to exit): ")) - 1
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
            log_index = int(input("\nEnter log number to edit subtasks (0 to exit): ")) - 1
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
                    print("\nOptions:")
                    print("1. Edit subtask")
                    print("2. Delete subtask")
                    print("0. Return to main menu")
                    
                    option = input("\nEnter your choice (0-2): ").strip()
                    
                    if option == "0":
                        break
                    elif option in ["1", "2"]:
                        subtask_input = input("\nEnter subtask number: ").strip()
                        try:
                            subtask_index = int(subtask_input) - 1
                            if 0 <= subtask_index < len(log['subtasks']):
                                if option == "1":
                                    print(f"\nCurrent subtask: {log['subtasks'][subtask_index]}")
                                    new_subtask = input("Enter new subtask description: ")
                                    if new_subtask.strip():
                                        log['subtasks'][subtask_index] = new_subtask
                                        print("Subtask updated successfully!")
                                    else:
                                        print("Subtask description cannot be empty!")
                                else:  # option == "2"
                                    deleted_subtask = log['subtasks'].pop(subtask_index)
                                    print(f"Deleted subtask: {deleted_subtask}")
                                
                                # Show updated subtasks
                                print("\nCurrent subtasks:")
                                for i, task in enumerate(log['subtasks'], 1):
                                    print(f"{i}. {task}")
                            else:
                                print("Invalid subtask number!")
                        except ValueError:
                            print("Please enter a valid number!")
                    else:
                        print("Invalid option. Please enter 0, 1, or 2.")
                
                self.save_logs()
                print("\nChanges saved successfully!")
                input("\nPress Enter to continue...")
        except ValueError:
            print("Invalid input")
            input("\nPress Enter to continue...")

    def load_settings(self):
        """Load settings from file or create default settings"""
        default_settings = {
            "log_types": [
                {"name": "Q", "prefix": "QI-", "status": "❌"},
                {"name": "Jira", "prefix": "JIRA-", "status": "❌"}
            ],
            "sprint_config": {
                "start_date": "2025-04-30",
                "duration_weeks": 2
            }
        }
        
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    self.settings = json.load(f)
            except json.JSONDecodeError:
                print("Error loading settings. Using default settings.")
                self.settings = default_settings
        else:
            self.settings = default_settings
            self.save_settings()

    def save_settings(self):
        """Save current settings to file"""
        with open(self.settings_file, 'w') as f:
            json.dump(self.settings, f, indent=2)

    def manage_settings(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Settings" + self.term.normal)
        
        while True:
            print("\n1. Manage Log Types")
            print("2. Configure Sprint Settings")
            print("3. View Current Settings")
            print("4. Return to Main Menu")
            
            try:
                choice = input("\nEnter your choice (1-4): ")
                
                if choice == "1":
                    self.manage_log_types()
                elif choice == "2":
                    self.configure_sprint_settings()
                elif choice == "3":
                    self.view_settings()
                elif choice == "4":
                    break
                else:
                    print("Invalid choice. Please enter a number between 1 and 4.")
            except KeyboardInterrupt:
                break

    def manage_log_types(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Manage Log Types" + self.term.normal)
        
        while True:
            print("\nCurrent Log Types:")
            for i, log_type in enumerate(self.settings["log_types"], 1):
                print(f"{i}. {log_type['name']} (Prefix: {log_type['prefix']})")
            
            print("\n1. Add New Log Type")
            print("2. Edit Existing Log Type")
            print("3. Delete Log Type")
            print("4. Return to Settings")
            
            try:
                choice = input("\nEnter your choice (1-4): ")
                
                if choice == "1":
                    name = input("Enter log type name: ")
                    prefix = input("Enter log type prefix: ")
                    self.settings["log_types"].append({
                        "name": name,
                        "prefix": prefix,
                        "status": "❌"
                    })
                    self.save_settings()
                    print("Log type added successfully!")
                
                elif choice == "2":
                    if not self.settings["log_types"]:
                        print("No log types to edit.")
                        continue
                    
                    index = int(input("Enter log type number to edit: ")) - 1
                    if 0 <= index < len(self.settings["log_types"]):
                        log_type = self.settings["log_types"][index]
                        name = input(f"Enter new name [{log_type['name']}]: ") or log_type['name']
                        prefix = input(f"Enter new prefix [{log_type['prefix']}]: ") or log_type['prefix']
                        self.settings["log_types"][index] = {
                            "name": name,
                            "prefix": prefix,
                            "status": log_type["status"]
                        }
                        self.save_settings()
                        print("Log type updated successfully!")
                    else:
                        print("Invalid log type number.")
                
                elif choice == "3":
                    if not self.settings["log_types"]:
                        print("No log types to delete.")
                        continue
                    
                    index = int(input("Enter log type number to delete: ")) - 1
                    if 0 <= index < len(self.settings["log_types"]):
                        del self.settings["log_types"][index]
                        self.save_settings()
                        print("Log type deleted successfully!")
                    else:
                        print("Invalid log type number.")
                
                elif choice == "4":
                    break
                
                else:
                    print("Invalid choice. Please enter a number between 1 and 4.")
            
            except (ValueError, IndexError):
                print("Invalid input. Please enter a valid number.")
            except KeyboardInterrupt:
                break

    def configure_sprint_settings(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Configure Sprint Settings" + self.term.normal)
        
        while True:
            print("\nCurrent Sprint Settings:")
            print(f"Start Date: {self.settings['sprint_config']['start_date']}")
            print(f"Duration: {self.settings['sprint_config']['duration_weeks']} weeks")
            
            print("\n1. Change Sprint Start Date")
            print("2. Change Sprint Duration")
            print("3. Return to Settings")
            
            try:
                choice = input("\nEnter your choice (1-3): ")
                
                if choice == "1":
                    while True:
                        new_date = input("Enter new start date (YYYY-MM-DD): ")
                        try:
                            datetime.strptime(new_date, "%Y-%m-%d")
                            self.settings["sprint_config"]["start_date"] = new_date
                            self.save_settings()
                            print("Sprint start date updated successfully!")
                            break
                        except ValueError:
                            print("Invalid date format. Please use YYYY-MM-DD.")
                
                elif choice == "2":
                    while True:
                        try:
                            new_duration = int(input("Enter new sprint duration in weeks: "))
                            if new_duration > 0:
                                self.settings["sprint_config"]["duration_weeks"] = new_duration
                                self.save_settings()
                                print("Sprint duration updated successfully!")
                                break
                            else:
                                print("Duration must be greater than 0.")
                        except ValueError:
                            print("Please enter a valid number.")
                
                elif choice == "3":
                    break
                
                else:
                    print("Invalid choice. Please enter a number between 1 and 3.")
            
            except KeyboardInterrupt:
                break

    def view_settings(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Current Settings" + self.term.normal)
        
        print("\nLog Types:")
        for log_type in self.settings["log_types"]:
            print(f"- {log_type['name']} (Prefix: {log_type['prefix']})")
        
        print("\nSprint Configuration:")
        print(f"Start Date: {self.settings['sprint_config']['start_date']}")
        print(f"Duration: {self.settings['sprint_config']['duration_weeks']} weeks")
        
        input("\nPress Enter to continue...")

    def get_sprint_dates(self, sprint_number=None):
        """Get start and end dates for a specific sprint number or current sprint"""
        # Get sprint configuration from settings
        first_sprint_start = datetime.strptime(self.settings["sprint_config"]["start_date"], "%Y-%m-%d")
        sprint_duration = self.settings["sprint_config"]["duration_weeks"] * 7  # Convert weeks to days
        
        if sprint_number is None:
            # Calculate current sprint based on current date
            now = datetime.now()
            days_since_first_sprint = (now - first_sprint_start).days
            sprint_number = days_since_first_sprint // sprint_duration
        
        # Calculate sprint dates based on sprint number
        sprint_start = first_sprint_start + timedelta(days=sprint_duration * sprint_number)
        sprint_end = sprint_start + timedelta(days=sprint_duration - 1)  # Sprint ends one day before next sprint
        
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
        
        # Get current sprint dates (pass None to get current sprint)
        sprint_start, sprint_end = self.get_sprint_dates(None)
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

    def display_statistics(self):
        """Display statistics and charts for logs in the last 10 workdays"""
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Statistics and Charts" + self.term.normal)
        
        if not self.logs:
            print("\nNo logs found.")
            input("\nPress Enter to continue...")
            return
        
        # Get current date and calculate date 14 days ago (to ensure we get 10 workdays)
        current_date = datetime.now()
        fourteen_days_ago = current_date - timedelta(days=13)
        
        # First, get all logs from the last 14 days
        recent_logs = []
        for log in self.logs:
            log_date = datetime.strptime(log['timestamp'].split()[0], "%d.%m.%Y")
            if log_date >= fourteen_days_ago:
                recent_logs.append(log)
        
        if not recent_logs:
            print("\nNo logs found in the last 10 workdays.")
            input("\nPress Enter to continue...")
            return
        
        # Get unique workdays from the logs
        workdays = set()
        for log in recent_logs:
            log_date = datetime.strptime(log['timestamp'].split()[0], "%d.%m.%Y")
            if log_date.weekday() < 5:  # 0-4 are weekdays
                workdays.add(log_date.strftime("%d.%m.%Y"))
        
        # Sort workdays and take the last 10
        workdays = sorted(list(workdays), key=lambda x: datetime.strptime(x, "%d.%m.%Y"), reverse=True)[:10]
        
        # Filter logs to only include those from the last 10 workdays
        recent_logs = [log for log in recent_logs if log['timestamp'].split()[0] in workdays]
        
        # Calculate statistics
        total_logs = len(recent_logs)
        
        # Calculate completion status for each log type
        completion_stats = {}
        for log_type in self.settings["log_types"]:
            type_name = log_type["name"]
            status_field = f"{type_name.lower()}_status"
            completed = sum(1 for log in recent_logs if log.get(status_field, "❌") == "✅")
            completion_stats[type_name] = {
                "completed": completed,
                "total": total_logs,
                "percentage": (completed/total_logs*100) if total_logs > 0 else 0
            }
        
        # Calculate hours per day
        hours_per_day = {}
        for log in recent_logs:
            date = log['timestamp'].split()[0]
            if date not in hours_per_day:
                hours_per_day[date] = 0
            hours_per_day[date] += self.parse_hours(log['hours'])
        
        # Display statistics
        print("\n" + self.term.underline + "Summary Statistics (Last 10 Workdays):" + self.term.normal)
        print(f"Total Logs: {total_logs}")
        for type_name, stats in completion_stats.items():
            print(f"Completed {type_name} Logs: {stats['completed']} ({stats['percentage']:.1f}%)")
        
        # Display incomplete logs for each type
        for log_type in self.settings["log_types"]:
            type_name = log_type["name"]
            status_field = f"{type_name.lower()}_status"
            print(f"\n" + self.term.underline + f"Incomplete {type_name} Logs:" + self.term.normal)
            incomplete_logs = [log for log in recent_logs if log.get(status_field, "❌") == "❌"]
            if incomplete_logs:
                for log in sorted(incomplete_logs, key=lambda x: datetime.strptime(x['timestamp'].split()[0], "%d.%m.%Y")):
                    print(f"{log['timestamp'].split()[0]}: {log['ticket']}")
            else:
                print(f"No incomplete {type_name} logs found.")
        
        # Display hours chart
        print("\n" + self.term.underline + "Hours per Workday:" + self.term.normal)
        max_hours = max(hours_per_day.values()) if hours_per_day else 0
        chart_width = 50  # Maximum width of the chart
        
        # Display hours for each workday
        for date in workdays:
            hours = hours_per_day.get(date, 0)
            bar_length = int((hours / max_hours) * chart_width) if max_hours > 0 else 0
            bar = "█" * bar_length
            hours_str = self.format_hours(hours)
            # Add a star (*) to indicate today's date
            if date == current_date.strftime("%d.%m.%Y"):
                print(f"{date}*: {bar} {hours_str}")
            else:
                print(f"{date}: {bar} {hours_str}")
        
        # Display logs per workday chart
        print("\n" + self.term.underline + "Logs per Workday:" + self.term.normal)
        logs_by_date = {}
        for log in recent_logs:
            date = log['timestamp'].split()[0]
            if date not in logs_by_date:
                logs_by_date[date] = 0
            logs_by_date[date] += 1
        
        max_logs = max(logs_by_date.values()) if logs_by_date else 0
        
        # Display logs for each workday
        for date in workdays:
            num_logs = logs_by_date.get(date, 0)
            bar_length = int((num_logs / max_logs) * chart_width) if max_logs > 0 else 0
            bar = "█" * bar_length
            # Add a star (*) to indicate today's date
            if date == current_date.strftime("%d.%m.%Y"):
                print(f"{date}*: {bar} {num_logs} logs")
            else:
                print(f"{date}: {bar} {num_logs} logs")
        
        print("\n* Today's date")
        input("\nPress Enter to continue...")

    def load_scripts(self):
        """Load migration scripts from file"""
        if os.path.exists(self.scripts_file):
            with open(self.scripts_file, 'r') as f:
                self.scripts = json.load(f)
        else:
            self.scripts = []
            self.save_scripts()

    def save_scripts(self):
        """Save migration scripts to file"""
        with open(self.scripts_file, 'w') as f:
            json.dump(self.scripts, f, indent=2)

    def log_migration_script(self):
        """Log a new migration script"""
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Log Migration Script" + self.term.normal)
        
        ticket = input("\nEnter ticket: ").strip()
        if not ticket or ticket.lower() in ['0', 'exit']:
            return
        
        script = input("Enter migration script: ")
        if script.lower() in ['0', 'exit']:
            return
        
        # Get status for Demo
        while True:
            demo_status = input("Update Demo status (x for ❌, c for ✅): ").lower()
            if demo_status in ['x', 'c']:
                break
            print("Invalid choice. Please enter 'x' for ❌ or 'c' for ✅")
        
        # Get status for Stage
        while True:
            stage_status = input("Update Stage status (x for ❌, c for ✅): ").lower()
            if stage_status in ['x', 'c']:
                break
            print("Invalid choice. Please enter 'x' for ❌ or 'c' for ✅")
        
        # Get status for Release notes
        while True:
            release_status = input("Update Release notes status (x for ❌, c for ✅): ").lower()
            if release_status in ['x', 'c']:
                break
            print("Invalid choice. Please enter 'x' for ❌ or 'c' for ✅")
        
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        
        new_script = {
            "timestamp": current_time,
            "ticket": ticket,
            "script": script,
            "demo_status": "✅" if demo_status == "c" else "❌",
            "stage_status": "✅" if stage_status == "c" else "❌",
            "release_status": "✅" if release_status == "c" else "❌"
        }
        
        self.scripts.append(new_script)
        self.save_scripts()
        print("\nMigration script logged successfully!")
        input("\nPress Enter to continue...")

    def view_migration_scripts(self):
        """View all migration scripts"""
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Migration Scripts" + self.term.normal)
        
        if not self.scripts:
            print("\nNo migration scripts found.")
            input("\nPress Enter to continue...")
            return
        
        print("\nMigration Scripts:")
        print("-" * 72)
        for i, script in enumerate(self.scripts, 1):
            print(f"\n{i}. Ticket: {script['ticket']}")
            print(f"   Timestamp: {script['timestamp']}")
            print(f"   Script: {script['script']}")
            print(f"   Demo: {script.get('demo_status', '❌')}")
            print(f"   Stage: {script.get('stage_status', '❌')}")
            print(f"   Release Notes: {script.get('release_status', '❌')}")
            print("-" * 72)
        
        input("\nPress Enter to continue...")

    def edit_migration_script(self):
        """Edit an existing migration script"""
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Edit Migration Script" + self.term.normal)
        
        if not self.scripts:
            print("\nNo migration scripts found.")
            input("\nPress Enter to continue...")
            return
        
        print("\nMigration Scripts:")
        print("-" * 72)
        for i, script in enumerate(self.scripts, 1):
            print(f"\n{i}. Ticket: {script['ticket']}")
            print(f"   Timestamp: {script['timestamp']}")
            print(f"   Script: {script['script']}")
            print(f"   Demo: {script.get('demo_status', '❌')}")
            print(f"   Stage: {script.get('stage_status', '❌')}")
            print(f"   Release Notes: {script.get('release_status', '❌')}")
            print("-" * 72)
        
        try:
            script_index = int(input("\nEnter script number to edit (0 to exit): ")) - 1
            if script_index == -1:
                return
            
            if 0 <= script_index < len(self.scripts):
                script = self.scripts[script_index]
                
                # Edit ticket
                print(f"\nCurrent ticket: {script['ticket']}")
                new_ticket = input("Enter new ticket (press Enter to keep current): ").strip()
                if new_ticket:
                    script['ticket'] = new_ticket
                
                # Edit script
                print(f"\nCurrent script: {script['script']}")
                new_script = input("Enter new script (press Enter to keep current): ").strip()
                if new_script:
                    script['script'] = new_script
                
                # Edit Demo status
                print(f"\nCurrent Demo status: {script.get('demo_status', '❌')}")
                while True:
                    demo_status = input("Update Demo status (x for ❌, c for ✅, Enter to keep current): ").lower()
                    if not demo_status:
                        break
                    if demo_status in ['x', 'c']:
                        script['demo_status'] = "✅" if demo_status == "c" else "❌"
                        break
                    print("Invalid choice. Please enter 'x' for ❌ or 'c' for ✅")
                
                # Edit Stage status
                print(f"\nCurrent Stage status: {script.get('stage_status', '❌')}")
                while True:
                    stage_status = input("Update Stage status (x for ❌, c for ✅, Enter to keep current): ").lower()
                    if not stage_status:
                        break
                    if stage_status in ['x', 'c']:
                        script['stage_status'] = "✅" if stage_status == "c" else "❌"
                        break
                    print("Invalid choice. Please enter 'x' for ❌ or 'c' for ✅")
                
                # Edit Release notes status
                print(f"\nCurrent Release notes status: {script.get('release_status', '❌')}")
                while True:
                    release_status = input("Update Release notes status (x for ❌, c for ✅, Enter to keep current): ").lower()
                    if not release_status:
                        break
                    if release_status in ['x', 'c']:
                        script['release_status'] = "✅" if release_status == "c" else "❌"
                        break
                    print("Invalid choice. Please enter 'x' for ❌ or 'c' for ✅")
                
                self.scripts[script_index] = script
                self.save_scripts()
                print("\nMigration script updated successfully!")
                input("\nPress Enter to continue...")
        except ValueError:
            print("Invalid input")
            input("\nPress Enter to continue...")

    def delete_migration_script(self):
        """Delete a migration script"""
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Delete Migration Script" + self.term.normal)
        
        if not self.scripts:
            print("\nNo migration scripts found.")
            input("\nPress Enter to continue...")
            return
        
        print("\nMigration Scripts:")
        print("-" * 72)
        for i, script in enumerate(self.scripts, 1):
            print(f"\n{i}. Ticket: {script['ticket']}")
            print(f"   Timestamp: {script['timestamp']}")
            print(f"   Script: {script['script']}")
            print(f"   Demo: {script.get('demo_status', '❌')}")
            print(f"   Stage: {script.get('stage_status', '❌')}")
            print(f"   Release Notes: {script.get('release_status', '❌')}")
            print("-" * 72)
        
        try:
            script_index = int(input("\nEnter script number to delete (0 to exit): ")) - 1
            if script_index == -1:
                return
            
            if 0 <= script_index < len(self.scripts):
                confirm = input(f"Are you sure you want to delete script {script_index + 1}? (y/n): ").lower()
                if confirm == 'y':
                    deleted_script = self.scripts.pop(script_index)
                    print(f"Deleted script: {deleted_script['ticket']}")
                    self.save_scripts()
                    input("\nPress Enter to continue...")
        except ValueError:
            print("Invalid input")
            input("\nPress Enter to continue...")

    def load_links(self):
        try:
            links_file = os.path.join(self.script_dir, "links.json")
            with open(links_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"links": []}

    def save_links(self):
        # Save to main links file
        links_file = os.path.join(self.script_dir, "links.json")
        with open(links_file, 'w') as f:
            json.dump(self.links, f, indent=4)
            
        # Save to backup file
        backup_file = os.path.join(self.script_dir, "backup", "links_backup.json")
        with open(backup_file, 'w') as f:
            json.dump(self.links, f, indent=4)

    def add_link(self):
        print(self.term.clear)
        print(self.term.black_on_white + "Add Important Link" + self.term.normal)
        
        link = input("\nEnter the link: ").strip()
        if not link:
            print("Link cannot be empty!")
            input("\nPress Enter to continue...")
            return
        
        comments = input("Enter comments (optional): ").strip()
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self.links["links"].append({
            "timestamp": timestamp,
            "link": link,
            "comments": comments
        })
        
        self.save_links()
        print("\nLink added successfully!")
        input("\nPress Enter to continue...")

    def view_links(self):
        print(self.term.clear)
        print(self.term.black_on_white + "Important Links" + self.term.normal)
        
        if not self.links["links"]:
            print("\nNo links found!")
            input("\nPress Enter to continue...")
            return
        
        print("\nLinks:")
        print("-" * 72)
        for i, link in enumerate(self.links["links"], 1):
            print(f"{i}. created: {link['timestamp']}")
            print(f"   link: @{link['link']}")
            if link['comments']:
                print(f"   Comments: {link['comments']}")
            print("-" * 72)
        
        input("\nPress Enter to continue...")

    def edit_link(self):
        print(self.term.clear)
        print(self.term.black_on_white + "Edit Important Link" + self.term.normal)
        
        if not self.links["links"]:
            print("\nNo links found!")
            input("\nPress Enter to continue...")
            return
        
        for i, link in enumerate(self.links["links"], 1):
            print(f"\n{i}. {link['link']}")
            print(f"   Timestamp: {link['timestamp']}")
            if link['comments']:
                print(f"   Comments: {link['comments']}")
        
        try:
            choice = int(input("\nEnter the number of the link to edit (0 to cancel): "))
            if choice == 0:
                return
            if 1 <= choice <= len(self.links["links"]):
                link = self.links["links"][choice - 1]
                print(f"\nCurrent link: {link['link']}")
                new_link = input("Enter new link (press Enter to keep current): ").strip()
                if new_link:
                    link['link'] = new_link
                
                print(f"\nCurrent comments: {link['comments']}")
                new_comments = input("Enter new comments (press Enter to keep current): ").strip()
                if new_comments:
                    link['comments'] = new_comments
                
                link['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.save_links()
                print("\nLink updated successfully!")
            else:
                print("\nInvalid choice!")
        except ValueError:
            print("\nPlease enter a valid number!")
        
        input("\nPress Enter to continue...")

    def delete_link(self):
        print(self.term.clear)
        print(self.term.black_on_white + "Delete Important Link" + self.term.normal)
        
        if not self.links["links"]:
            print("\nNo links found!")
            input("\nPress Enter to continue...")
            return
        
        for i, link in enumerate(self.links["links"], 1):
            print(f"\n{i}. {link['link']}")
            print(f"   Timestamp: {link['timestamp']}")
            if link['comments']:
                print(f"   Comments: {link['comments']}")
        
        try:
            choice = int(input("\nEnter the number of the link to delete (0 to cancel): "))
            if choice == 0:
                return
            if 1 <= choice <= len(self.links["links"]):
                deleted_link = self.links["links"].pop(choice - 1)
                self.save_links()
                print(f"\nLink deleted: {deleted_link['link']}")
            else:
                print("\nInvalid choice!")
        except ValueError:
            print("\nPlease enter a valid number!")
        
        input("\nPress Enter to continue...")

    def view_logs_for_date(self):
        print(self.term.clear)
        print(self.term.black_on_white + "View Logs for a Date" + self.term.normal)
        date_str = input("\nEnter date (DD.MM.YYYY): ").strip()
        try:
            datetime.strptime(date_str, "%d.%m.%Y")
        except ValueError:
            print("Invalid date format. Please use DD.MM.YYYY.")
            input("\nPress Enter to continue...")
            return
        found = False
        output_lines = []
        for log in self.logs:
            log_date = log['timestamp'].split()[0]
            if log_date == date_str:
                if not found:
                    output_lines.append(date_str)
                    found = True
                # Main log line
                ticket_line = log['ticket']
                if log['hours']:
                    ticket_line += f" ({log['hours']})"
                output_lines.append(ticket_line)
                # Subtasks
                for sub in log.get('subtasks', []):
                    output_lines.append(f"   └─ {sub}")
        if not found:
            print(f"\nNo logs found for {date_str}.")
        else:
            print("\n" + "\n".join(output_lines))
        input("\nPress Enter to continue...")

    def run(self):
        self.reset_screen()
        while self.running:
            print(self.term.black_on_white + "B-Logger" + self.term.normal)
            print("\n1. Logs")
            print("2. View current sprint")
            print("3. View sprint history")
            print("4. Migration script")
            print("5. Important Links")
            print("6. Settings")
            print("7. Help")
            print("8. Statistics")
            print("9. Exit")
            
            try:
                choice = input("\nEnter your choice (1-9): ")
                
                if choice == "1":  # Logs submenu
                    while True:
                        print(self.term.clear)
                        print(self.term.black_on_white + "Logs Menu" + self.term.normal)
                        print("\n1. Create log")
                        print("2. View logs")
                        print("3. Edit log")
                        print("4. Delete log")
                        print("5. Mark as checked")
                        print("6. Mark as unchecked")
                        print("7. Edit subtasks")
                        print("8. View logs for a date")
                        print("0. Back to main menu")
                        
                        subchoice = input("\nEnter your choice (0-8): ")
                        if subchoice == "0":
                            break
                        elif subchoice == "1":
                            self.create_new_log()
                        elif subchoice == "2":
                            self.display_logs()
                            input("\nPress Enter to continue...")
                        elif subchoice == "3":
                            self.edit_log()
                        elif subchoice == "4":
                            self.delete_log()
                        elif subchoice == "5":
                            self.mark_as_checked()
                        elif subchoice == "6":
                            self.mark_as_unchecked()
                        elif subchoice == "7":
                            self.edit_subtasks()
                        elif subchoice == "8":
                            self.view_logs_for_date()
                        self.reset_screen()
                
                elif choice == "2":
                    self.view_sprint_logs()
                    self.reset_screen()
                
                elif choice == "3":
                    self.view_sprint_history()
                    self.reset_screen()
                
                elif choice == "4":  # Migration script submenu
                    while True:
                        print(self.term.clear)
                        print(self.term.black_on_white + "Migration Script Menu" + self.term.normal)
                        print("\n1. Create migration script")
                        print("2. View migration scripts")
                        print("3. Edit migration script")
                        print("4. Delete migration script")
                        print("0. Back to main menu")
                        
                        subchoice = input("\nEnter your choice (0-4): ")
                        if subchoice == "0":
                            break
                        elif subchoice == "1":
                            self.log_migration_script()
                        elif subchoice == "2":
                            self.view_migration_scripts()
                        elif subchoice == "3":
                            self.edit_migration_script()
                        elif subchoice == "4":
                            self.delete_migration_script()
                        self.reset_screen()
                
                elif choice == "5":  # Important Links submenu
                    while True:
                        print(self.term.clear)
                        print(self.term.black_on_white + "Important Links Menu" + self.term.normal)
                        print("\n1. Add link")
                        print("2. View links")
                        print("3. Edit link")
                        print("4. Delete link")
                        print("0. Back to main menu")
                        
                        subchoice = input("\nEnter your choice (0-4): ")
                        if subchoice == "0":
                            break
                        elif subchoice == "1":
                            self.add_link()
                        elif subchoice == "2":
                            self.view_links()
                        elif subchoice == "3":
                            self.edit_link()
                        elif subchoice == "4":
                            self.delete_link()
                        self.reset_screen()
                
                elif choice == "6":
                    self.manage_settings()
                    self.reset_screen()
                
                elif choice == "7":
                    self.display_help()
                    self.reset_screen()
                
                elif choice == "8":
                    self.display_statistics()
                    self.reset_screen()
                
                elif choice == "9":
                    self.running = False
                    break
                
                self.reset_screen()
            except KeyboardInterrupt:
                print("\nExiting B-LOGGER...")
                self.running = False
                break

if __name__ == "__main__":
    logger = BLogger()
    logger.run() 