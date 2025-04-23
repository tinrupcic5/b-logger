#!/usr/bin/env python3

import os
import sys
import json
from datetime import datetime
from blessed import Terminal
from dateutil import parser

class BLogger:
    def __init__(self):
        self.term = Terminal()
        self.logs = []
        self.current_log = None
        self.log_file = "logs.json"
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.load_logs()
        self.banner = None
        self.load_banner()

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
        with open(self.log_file, 'w') as f:
            json.dump(self.logs, f, indent=2)

    def create_new_log(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Create New Log" + self.term.normal)
        
        ticket = input("Enter your log here: ")
        description = input("Enter description: ")
        
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        
        self.current_log = {
            "timestamp": current_time,
            "ticket": ticket,
            "description": description,
            "q_status": "❌",
            "jira_status": "❌",
            "subtasks": []
        }
        
        self.update_status()
        self.logs.append(self.current_log)
        self.save_logs()

    def update_status(self):
        print(self.term.clear)
        print(f"Current log: {self.current_log['ticket']} - {self.current_log['description']}")
        
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

    def display_logs(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Log History" + self.term.normal)
        
        for i, log in enumerate(self.logs):
            print(f"{i+1}. {log['timestamp']} {log['ticket']} - {log['description']} {log['q_status']} {log['jira_status']}")
            if log['subtasks']:
                for subtask in log['subtasks']:
                    print(f"   └─ {subtask}")

    def edit_log(self):
        print(self.term.clear)
        self.display_logs()
        try:
            log_index = int(input("Enter log number to edit (0 to cancel): ")) - 1
            if log_index == -1:
                return
            
            if 0 <= log_index < len(self.logs):
                self.current_log = self.logs[log_index]
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
                    print(f"Deleted log: {deleted_log['ticket']} - {deleted_log['description']}")
                    self.save_logs()
                    input("\nPress Enter to continue...")
        except ValueError:
            print("Invalid input")
            input("\nPress Enter to continue...")

    def run(self):
        while True:
            self.display_banner()  # Redisplay banner before menu
            print(self.term.black_on_white + "B-Logger" + self.term.normal)
            print("\n1. Create new log")
            print("2. View logs")
            print("3. Edit log")
            print("4. Delete log")
            print("5. Exit")
            
            choice = input("\nEnter your choice (1-5): ")
            
            if choice == "1":
                self.create_new_log()
            elif choice == "2":
                self.display_logs()
                input("\nPress Enter to continue...")
            elif choice == "3":
                self.edit_log()
            elif choice == "4":
                self.delete_log()
            elif choice == "5":
                break

if __name__ == "__main__":
    logger = BLogger()
    logger.run() 