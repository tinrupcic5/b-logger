#!/usr/bin/env python3

import os
import sys
import json
import signal
from datetime import datetime, timedelta
from blessed import Terminal
from dateutil import parser
from typing import Optional

try:
    import readline
except Exception:  # pragma: no cover
    readline = None

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
        self._configure_readline()
        
        signal.signal(signal.SIGINT, self.handle_exit)

    def daily_target_minutes(self) -> int:
        return 8 * 60

    def format_minutes_signed(self, total_minutes: int) -> str:
        sign = "-" if total_minutes < 0 else ""
        minutes_abs = abs(total_minutes)
        if minutes_abs == 0:
            return f"{sign}0h"
        hours = minutes_abs // 60
        minutes = minutes_abs % 60
        if minutes == 0:
            return f"{sign}{hours}h"
        return f"{sign}{hours}h {minutes}m"

    def color_remaining(self, remaining_minutes: int) -> str:
        remaining_str = self.format_minutes_signed(remaining_minutes)
        if remaining_minutes > 0:
            return self.term.cyan(remaining_str)
        if remaining_minutes == 0:
            return self.term.green(remaining_str)
        return self.term.red(remaining_str)

    def _configure_readline(self) -> None:
        if readline is None:
            return

        try:
            readline.parse_and_bind("set editing-mode emacs")
        except Exception:
            pass

        is_libedit = False
        try:
            is_libedit = bool(getattr(readline, "__doc__", "") and "libedit" in readline.__doc__)
        except Exception:
            is_libedit = False

        if is_libedit:
            libedit_binds = [
                r'bind "\e[1;3D" ed-move-to-beg',  # Option+Left (xterm)
                r'bind "\e[1;3C" ed-move-to-end',  # Option+Right (xterm)
                r'bind "\e[1;9D" ed-move-to-beg',  # Option+Left (some terminals)
                r'bind "\e[1;9C" ed-move-to-end',  # Option+Right (some terminals)
                r'bind "\e[3D" ed-move-to-beg',    # Fallback
                r'bind "\e[3C" ed-move-to-end',    # Fallback
            ]
            for bind in libedit_binds:
                try:
                    readline.parse_and_bind(bind)
                except Exception:
                    pass
        else:
            sequences = [
                r'"\e[1;3D": beginning-of-line',  # Option+Left (xterm)
                r'"\e[1;3C": end-of-line',        # Option+Right (xterm)
                r'"\e[1;9D": beginning-of-line',  # Option+Left (some terminals)
                r'"\e[1;9C": end-of-line',        # Option+Right (some terminals)
                r'"\e[3D": beginning-of-line',    # Fallback
                r'"\e[3C": end-of-line',          # Fallback
                r'"\e;3D": beginning-of-line',    # Some terminals omit '['
                r'"\e;3C": end-of-line',          # Some terminals omit '['
            ]
            for bind in sequences:
                try:
                    readline.parse_and_bind(bind)
                except Exception:
                    pass

    def ask(self, text: str) -> str:
        return input(text)

    def select_menu(
        self,
        title: str,
        options: list[tuple[str, str]],
        *,
        default_index: int = 0,
        preamble: Optional[str] = None,
    ) -> Optional[str]:
        if not options:
            return None

        selected = max(0, min(default_index, len(options) - 1))
        values = {value for value, _ in options}
        digit_buffer = ""
        window_start = 0

        def visible_capacity() -> int:
            preamble_lines = preamble.count("\n") + 1 if preamble else 0
            # title, blank, hint, optional scroll indicator, padding
            reserved = preamble_lines + 5
            return max(3, self.term.height - reserved)

        def ensure_visible() -> None:
            nonlocal window_start
            capacity = visible_capacity()
            if selected < window_start:
                window_start = selected
            elif selected >= window_start + capacity:
                window_start = selected - capacity + 1

        def render() -> None:
            ensure_visible()
            capacity = visible_capacity()
            window_end = min(len(options), window_start + capacity)

            print(self.term.clear + self.term.home, end="")
            if preamble:
                print(preamble)
            print(self.term.black_on_white + title + self.term.normal)
            print()
            if window_start > 0:
                print(self.term.dim + f"   ↑ {window_start} more" + self.term.normal)
            for i in range(window_start, window_end):
                value, label = options[i]
                line = f"{value}. {label}"
                if i == selected:
                    print(self.term.black_on_white(f" > {line} ") + self.term.normal)
                else:
                    print(f"   {line}")
            remaining = len(options) - window_end
            if remaining > 0:
                print(self.term.dim + f"   ↓ {remaining} more" + self.term.normal)
            print()
            hint = "↑/↓ navigate, Enter confirm, number select, Esc back"
            if digit_buffer:
                hint += f"  [{digit_buffer}]"
            print(self.term.dim + hint + self.term.normal)
            sys.stdout.flush()

        try:
            with self.term.cbreak(), self.term.hidden_cursor():
                while True:
                    render()
                    timeout = 0.5 if digit_buffer else None
                    key = self.term.inkey(timeout=timeout)

                    if not key:
                        if digit_buffer in values:
                            return digit_buffer
                        digit_buffer = ""
                        continue

                    if key.name == "KEY_ESCAPE":
                        return None

                    if key.name == "KEY_UP":
                        digit_buffer = ""
                        selected = (selected - 1) % len(options)
                        continue

                    if key.name == "KEY_DOWN":
                        digit_buffer = ""
                        selected = (selected + 1) % len(options)
                        continue

                    if key.name in ("KEY_ENTER", "KEY_RETURN") or key in ("\n", "\r"):
                        if digit_buffer and digit_buffer in values:
                            return digit_buffer
                        return options[selected][0]

                    if key.name in ("KEY_BACKSPACE", "KEY_DELETE") or key in ("\x7f", "\b"):
                        digit_buffer = digit_buffer[:-1]
                        continue

                    if key.isdigit():
                        candidate = digit_buffer + str(key)
                        matches = [value for value in values if value.startswith(candidate)]
                        if not matches:
                            candidate = str(key)
                            matches = [value for value in values if value.startswith(candidate)]
                            if not matches:
                                digit_buffer = ""
                                continue

                        digit_buffer = candidate
                        exact = next((i for i, (value, _) in enumerate(options) if value == digit_buffer), None)
                        if exact is not None:
                            selected = exact
                        else:
                            selected = next(
                                i for i, (value, _) in enumerate(options) if value.startswith(digit_buffer)
                            )
                        if digit_buffer in values and len(matches) == 1:
                            return digit_buffer
                        continue
        except KeyboardInterrupt:
            return None

        return None

    def get_sorted_logs(self):
        return sorted(self.logs, key=lambda x: datetime.strptime(x['timestamp'].split()[0], "%d.%m.%Y"))

    def format_log_label(self, log: dict) -> str:
        return (
            f"{log['timestamp']} {log['ticket']} - {log['hours']} hours "
            f"[Q-> {log['q_status']}] [J-> {log['jira_status']}]"
        )

    def handle_exit(self, signum, frame):
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
        print("\n")

    def load_logs(self):
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r') as f:
                self.logs = json.load(f)

    def save_logs(self):
        self.logs.sort(key=lambda x: datetime.strptime(x['timestamp'].split()[0], "%d.%m.%Y"))
        
        with open(self.log_file, 'w') as f:
            json.dump(self.logs, f, indent=2)
            
        backup_file = os.path.join(self.script_dir, "backup", "logs_backup.json")
        with open(backup_file, 'w') as f:
            json.dump(self.logs, f, indent=2)

    def create_new_log(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Create New Log" + self.term.normal)
        
        while True:
            use_custom_date = self.ask("Do you want to use a different date? (y/n): ").lower()
            if use_custom_date in ['0', 'exit']:
                return
            if use_custom_date in ['y', 'n']:
                break
            print("Invalid choice. Please enter 'y', 'n', '0', or 'exit'")
        
        if use_custom_date == 'y':
            while True:
                try:
                    custom_date = self.ask("Enter date (DD.MM.YYYY) or 0/exit to cancel: ")
                    if custom_date.lower() in ['0', 'exit']:
                        return
                    datetime.strptime(custom_date, "%d.%m.%Y")
                    current_time = f"{custom_date} {datetime.now().strftime('%H:%M:%S')}"
                    break
                except ValueError:
                    print("Invalid date format. Please use DD.MM.YYYY (e.g., 23.04.2024)")
        
        else:
            current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        ticket = self.ask("Enter your log here: ")
        if ticket.lower() in ['0', 'exit']:
            return

        log_date = current_time.split()[0]
        day_total_minutes = sum(
            self.parse_hours(log.get('hours', ''))
            for log in self.logs
            if log['timestamp'].split()[0] == log_date
        )
        logged_so_far = self.format_hours(day_total_minutes) or "0h"
        remaining_minutes = self.daily_target_minutes() - day_total_minutes
        remaining_str = self.format_minutes_signed(remaining_minutes)
        for_line = (
            f"For {log_date} you logged {logged_so_far} and still have left {remaining_str}."
        )
        print(self.term.cyan(for_line))

        hours = self.ask("Enter hours (e.g., 1h 30m or just 30m): ")
        if hours.lower() in ['0', 'exit']:
            return

        entered_minutes = self.parse_hours(hours)
        remaining_after_minutes = self.daily_target_minutes() - (day_total_minutes + entered_minutes)
        print(
            f"After this entry, remaining for {log_date}: "
            f"{self.color_remaining(remaining_after_minutes)}."
        )
        
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
        
        update_hours = self.ask("Do you want to update hours? (y/n): ").lower()
        if update_hours == 'y':
            log_date = self.current_log["timestamp"].split()[0]
            day_total_minutes = sum(
                self.parse_hours(log.get('hours', ''))
                for log in self.logs
                if log['timestamp'].split()[0] == log_date
            )
            current_log_minutes = self.parse_hours(self.current_log.get("hours", ""))
            total_without_current = day_total_minutes - current_log_minutes

            logged_so_far = self.format_hours(day_total_minutes) or "0h"
            remaining_minutes = self.daily_target_minutes() - day_total_minutes
            remaining_str = self.format_minutes_signed(remaining_minutes)
            for_line = (
                f"For {log_date} you logged {logged_so_far} and still have left {remaining_str}."
            )
            print(self.term.cyan(for_line))

            new_hours = self.ask("Enter new hours: ")
            new_minutes = self.parse_hours(new_hours)
            remaining_after_minutes = self.daily_target_minutes() - (total_without_current + new_minutes)
            print(
                f"After update, for {log_date} you logged "
                f"{self.format_hours(total_without_current + new_minutes) or '0h'} and still have left "
                f"{self.color_remaining(remaining_after_minutes)}."
            )
            self.current_log["hours"] = new_hours
        
        q_status = self.ask("Update Q log status (x for ❌, c for ✅): ").lower()
        jira_status = self.ask("Update Jira log status (x for ❌, c for ✅): ").lower()
        
        self.current_log["q_status"] = "✅" if q_status == "c" else "❌"
        self.current_log["jira_status"] = "✅" if jira_status == "c" else "❌"
        
        while True:
            subtask = self.ask("Add subtask? (y/n): ").lower()
            if subtask != "y":
                break
                
            subtask_desc = self.ask("Enter subtask description: ")
            self.current_log["subtasks"].append(subtask_desc)
            print(f"Added subtask: {subtask_desc}")
            print("Current subtasks:")
            for i, task in enumerate(self.current_log["subtasks"], 1):
                print(f"{i}. {task}")
            print()

    def parse_hours(self, hours_str):
        if not hours_str or hours_str.lower() == 'ongoing':
            return 0
        
        total_minutes = 0
        hours_str = hours_str.lower().replace('hours', '').strip()
        
        if 'h' in hours_str:
            hours_part = hours_str.split('h')[0]
            try:
                total_minutes += int(hours_part.strip()) * 60
            except ValueError:
                pass
        elif hours_str.isdigit():
            try:
                total_minutes += int(hours_str.strip()) * 60
            except ValueError:
                pass
        
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
        
        for line in self.build_log_view_lines(self.get_sorted_logs()):
            print(line["text"])

    def build_log_view_lines(self, sorted_logs, selected_index: Optional[int] = None):
        """Build display rows for logs, separated by date with day totals."""
        lines = []
        current_date = None
        day_total_minutes = 0

        def flush_day_total(date_str: str, minutes: int) -> None:
            total_hours = self.format_hours(minutes)
            if total_hours:
                color = self.term.green if minutes == 480 else self.term.red
                lines.append({"kind": "meta", "log_index": None, "text": ""})
                lines.append({
                    "kind": "meta",
                    "log_index": None,
                    "text": f"Total for {date_str}: {color(total_hours)}",
                })
                lines.append({"kind": "meta", "log_index": None, "text": "-" * 72})
            lines.append({"kind": "meta", "log_index": None, "text": "-" * 72})

        for i, log in enumerate(sorted_logs):
            log_date = log['timestamp'].split()[0]

            if current_date is not None and log_date != current_date:
                flush_day_total(current_date, day_total_minutes)
                day_total_minutes = 0

            current_date = log_date
            label = f"{i + 1}. {self.format_log_label(log)}"
            if selected_index is not None and i == selected_index:
                text = self.term.black_on_white(f" > {label} ") + self.term.normal
            else:
                text = f"   {label}" if selected_index is not None else label
            lines.append({"kind": "log", "log_index": i, "text": text})

            if log.get('subtasks'):
                for subtask in log['subtasks']:
                    lines.append({
                        "kind": "meta",
                        "log_index": i,
                        "text": f"   └─ {subtask}",
                    })

            day_total_minutes += self.parse_hours(log['hours'])

        if current_date is not None and day_total_minutes > 0:
            total_hours = self.format_hours(day_total_minutes)
            color = self.term.green if day_total_minutes == 480 else self.term.red
            lines.append({"kind": "meta", "log_index": None, "text": ""})
            lines.append({
                "kind": "meta",
                "log_index": None,
                "text": f"Total for {current_date}: {color(total_hours)}",
            })
            lines.append({"kind": "meta", "log_index": None, "text": "-" * 72})

        return lines

    def view_logs(self):
        while True:
            if not self.logs:
                print(self.term.clear)
                print(self.term.black_on_white + "View Logs" + self.term.normal)
                print("\nNo logs found.")
                self.ask("\nPress Enter to continue...")
                return

            sorted_logs = self.get_sorted_logs()
            selected = len(sorted_logs) - 1
            digit_buffer = ""
            window_start = 0

            def selected_line_index(lines) -> int:
                for idx, line in enumerate(lines):
                    if line["kind"] == "log" and line["log_index"] == selected:
                        return idx
                return 0

            def visible_capacity() -> int:
                # title, blank, hint, scroll indicators, padding
                return max(5, self.term.height - 6)

            def ensure_visible(lines) -> None:
                nonlocal window_start
                capacity = visible_capacity()
                focus = selected_line_index(lines)
                if focus < window_start:
                    window_start = focus
                elif focus >= window_start + capacity:
                    window_start = focus - capacity + 1
                # On the last log, pin to bottom so day totals aren't hidden below
                if selected == len(sorted_logs) - 1:
                    window_start = max(0, len(lines) - capacity)
                max_start = max(0, len(lines) - capacity)
                window_start = max(0, min(window_start, max_start))

            def render() -> None:
                nonlocal window_start
                lines = self.build_log_view_lines(sorted_logs, selected)
                ensure_visible(lines)
                capacity = visible_capacity()
                window_end = min(len(lines), window_start + capacity)
                logs_above = sum(1 for line in lines[:window_start] if line["kind"] == "log")
                logs_below = sum(1 for line in lines[window_end:] if line["kind"] == "log")

                print(self.term.clear + self.term.home, end="")
                print(self.term.black_on_white + "View Logs" + self.term.normal)
                print()
                if logs_above > 0:
                    print(self.term.dim + f"   ↑ {logs_above} more" + self.term.normal)
                for line in lines[window_start:window_end]:
                    print(line["text"])
                if logs_below > 0:
                    print(self.term.dim + f"   ↓ {logs_below} more" + self.term.normal)
                print()
                hint = "↑/↓ navigate, Enter edit/delete, number jump, Esc back"
                if digit_buffer:
                    hint += f"  [{digit_buffer}]"
                print(self.term.dim + hint + self.term.normal)
                sys.stdout.flush()

            choice = None
            try:
                with self.term.cbreak(), self.term.hidden_cursor():
                    while True:
                        render()
                        timeout = 0.5 if digit_buffer else None
                        key = self.term.inkey(timeout=timeout)

                        if not key:
                            if digit_buffer.isdigit():
                                jump = int(digit_buffer) - 1
                                if 0 <= jump < len(sorted_logs):
                                    choice = jump
                                    break
                            digit_buffer = ""
                            continue

                        if key.name == "KEY_ESCAPE" or key == "0":
                            choice = None
                            break

                        if key.name == "KEY_UP":
                            digit_buffer = ""
                            selected = (selected - 1) % len(sorted_logs)
                            continue

                        if key.name == "KEY_DOWN":
                            digit_buffer = ""
                            selected = (selected + 1) % len(sorted_logs)
                            continue

                        if key.name in ("KEY_ENTER", "KEY_RETURN") or key in ("\n", "\r"):
                            if digit_buffer.isdigit():
                                jump = int(digit_buffer) - 1
                                if 0 <= jump < len(sorted_logs):
                                    choice = jump
                                    break
                            choice = selected
                            break

                        if key.name in ("KEY_BACKSPACE", "KEY_DELETE") or key in ("\x7f", "\b"):
                            digit_buffer = digit_buffer[:-1]
                            continue

                        if key.isdigit():
                            candidate = digit_buffer + str(key)
                            jump = int(candidate) - 1
                            if jump + 1 > len(sorted_logs) and len(candidate) > 1:
                                candidate = str(key)
                                jump = int(candidate) - 1
                            if jump + 1 > len(sorted_logs):
                                digit_buffer = ""
                                continue
                            digit_buffer = candidate
                            if 0 <= jump < len(sorted_logs):
                                selected = jump
                            continue
            except KeyboardInterrupt:
                return

            if choice is None:
                return

            log = sorted_logs[choice]
            action = self.select_menu(
                f"Log {choice + 1}",
                [
                    ("1", "Edit"),
                    ("2", "Delete"),
                    ("3", "Mark as checked"),
                    ("4", "Mark as unchecked"),
                    ("5", "Mark all day as checked"),
                    ("6", "Mark all day as unchecked"),
                    ("0", "Back"),
                ],
                preamble=self.format_log_label(log),
            )
            if action in (None, "0"):
                continue
            if action == "1":
                self.edit_log_entry(log, choice + 1)
            elif action == "2":
                self.delete_log_entry(log, choice + 1)
            elif action == "3":
                self.mark_log_entry(log, choice + 1, checked=True)
            elif action == "4":
                self.mark_log_entry(log, choice + 1, checked=False)
            elif action == "5":
                self.mark_day_for_log(log, checked=True)
            elif action == "6":
                self.mark_day_for_log(log, checked=False)

    def edit_log_entry(self, log: dict, display_number: Optional[int] = None):
        label = f"Editing Log {display_number}" if display_number else "Editing Log"
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + label + self.term.normal)
        print(f"\nCurrent: {self.format_log_label(log)}")
        self.current_log = log

        edit_date = self.ask("\nDo you want to edit the date? (y/n): ").lower()
        if edit_date == 'y':
            current_date = self.current_log['timestamp'].split()[0]
            print(f"Current date: {current_date}")
            while True:
                new_date = self.ask("Enter new date (DD.MM.YYYY) or leave empty to cancel: ").strip()
                if not new_date:
                    break
                try:
                    datetime.strptime(new_date, "%d.%m.%Y")
                    time_part = (
                        self.current_log['timestamp'].split()[1]
                        if len(self.current_log['timestamp'].split()) > 1
                        else datetime.now().strftime('%H:%M:%S')
                    )
                    self.current_log["timestamp"] = f"{new_date} {time_part}"
                    break
                except ValueError:
                    print("Invalid date format. Please use DD.MM.YYYY (e.g., 23.04.2024)")

        edit_desc = self.ask("Do you want to edit the description? (y/n): ").lower()
        if edit_desc == 'y':
            print(f"\nCurrent description: {self.current_log['ticket']}")
            new_desc = self.ask("Enter new description: ")
            if new_desc.strip():
                self.current_log["ticket"] = new_desc

        self.update_status()
        self.save_logs()
        print("\nLog updated successfully!")
        self.ask("\nPress Enter to continue...")

    def delete_log_entry(self, log: dict, display_number: Optional[int] = None):
        label = f"log {display_number}" if display_number else "this log"
        confirm = self.ask(f"Are you sure you want to delete {label}? (y/n): ").lower()
        if confirm != 'y':
            return False

        try:
            self.logs.remove(log)
        except ValueError:
            print("Log not found.")
            self.ask("\nPress Enter to continue...")
            return False

        print(f"Deleted log: {log['ticket']} - {log['hours']} hours")
        self.save_logs()
        self.ask("\nPress Enter to continue...")
        return True

    def ask_status_choice(self) -> Optional[str]:
        while True:
            status_choice = self.ask(
                "\nWhich status do you want to update? (q/j/b for Q/Jira/Both, 0 to exit): "
            ).lower()
            if status_choice == '0':
                return None
            if status_choice in ['q', 'j', 'b']:
                return status_choice
            print("Invalid choice. Please enter 'q' for Q, 'j' for Jira, 'b' for Both, or '0' to exit.")

    def apply_status_choice(self, log: dict, status_choice: str, checked: bool) -> list[str]:
        mark = "✅" if checked else "❌"
        updated = []
        if status_choice in ['q', 'b']:
            log["q_status"] = mark
            updated.append("Q")
        if status_choice in ['j', 'b']:
            log["jira_status"] = mark
            updated.append("Jira")
        return updated

    def mark_log_entry(self, log: dict, display_number: Optional[int] = None, *, checked: bool = True):
        action = "checked" if checked else "unchecked"
        label = f"Log {display_number}" if display_number else "Log"
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + f"Mark {label} as {action.title()}" + self.term.normal)
        print(f"\n{self.format_log_label(log)}")

        status_choice = self.ask_status_choice()
        if status_choice is None:
            return

        updated = self.apply_status_choice(log, status_choice, checked)
        print(f"\nMarked log{f' {display_number}' if display_number else ''} as {action} for {', '.join(updated)}.")
        self.save_logs()
        self.ask("\nPress Enter to continue...")

    def mark_day_for_log(self, log: dict, *, checked: bool = True):
        action = "checked" if checked else "unchecked"
        date_str = log['timestamp'].split()[0]
        print(self.term.clear)
        print(
            self.term.move_y(0)
            + self.term.black_on_white
            + f"Mark All Day as {action.title()}"
            + self.term.normal
        )
        print(f"\nDate: {date_str}")

        status_choice = self.ask_status_choice()
        if status_choice is None:
            return

        count = 0
        updated = []
        for day_log in self.logs:
            if day_log['timestamp'].split()[0] == date_str:
                updated = self.apply_status_choice(day_log, status_choice, checked)
                count += 1

        print(f"\nMarked {count} log(s) as {action} for {date_str} ({', '.join(updated)}).")
        if count > 0:
            self.save_logs()
        self.ask("\nPress Enter to continue...")

    def edit_log(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Edit Log" + self.term.normal)
        self.display_logs()
        try:
            log_index = int(self.ask("\nEnter log number to edit (0 to exit): ")) - 1
            if log_index == -1:
                return

            sorted_logs = self.get_sorted_logs()
            if 0 <= log_index < len(sorted_logs):
                self.edit_log_entry(sorted_logs[log_index], log_index + 1)
        except ValueError:
            print("Invalid input")
            self.ask("\nPress Enter to continue...")

    def delete_log(self):
        print(self.term.clear)
        self.display_logs()
        try:
            log_index = int(self.ask("Enter log number to delete (0 to exit): ")) - 1
            if log_index == -1:
                return

            sorted_logs = self.get_sorted_logs()
            if 0 <= log_index < len(sorted_logs):
                self.delete_log_entry(sorted_logs[log_index], log_index + 1)
        except ValueError:
            print("Invalid input")
            self.ask("\nPress Enter to continue...")

    def reset_screen(self):
        print(self.term.clear)
        self.display_banner()

    def display_help(self):
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
        print("- Use ↑/↓ arrow keys to move through menu options")
        print("- Press Enter to select the highlighted option")
        print("- Press a number to jump to / select that option")
        print("- Press Esc to cancel / go back")
        print("- Use arrow keys to navigate through input history")
        print("- Use backspace to delete characters")
        print("- Press Enter to confirm text inputs")
        print("- Press 0 or type 'exit' to return to previous menu")
        print("- Press Ctrl+C to exit the program")
        
        print("\n" + self.term.underline + "Tips:" + self.term.normal)
        print("- Use settings to customize log types and sprint configuration")
        print("- Add subtasks to better organize your work")
        print("- Mark tasks as checked/unchecked to track progress")
        print("- View sprint history to see past work")
        print("- Use custom dates for historical entries")
        print("- Check statistics to monitor your work patterns")
        
        self.ask("\nPress Enter to return to main menu...")

    def display_about(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "About B-Logger" + self.term.normal)

        print("\n" + self.term.underline + "B-Logger" + self.term.normal)
        print("Terminal tool for logging work hours and tasks.")

        print("\n" + self.term.underline + "Author:" + self.term.normal)
        print("  Tin")

        print("\n" + self.term.underline + "Version:" + self.term.normal)
        print("  V1.0.12")

        print("\n" + self.term.underline + "GitHub:" + self.term.normal)
        print("  https://github.com/tinrupcic5/b-logger.git")

        print("\n" + self.term.underline + "License:" + self.term.normal)
        print("  Edde License")
        print("  See LICENSE file for details.")

        self.ask("\nPress Enter to return to main menu...")

    def mark_as_checked(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Mark Log as Checked" + self.term.normal)
        self.display_logs()
        
        while True:
            status_choice = self.ask("\nWhich status do you want to update? (q/j/b for Q/Jira/Both, 0 to exit): ").lower()
            if status_choice == '0':
                return
            if status_choice in ['q', 'j', 'b']:
                break
            print("Invalid choice. Please enter 'q' for Q, 'j' for Jira, 'b' for Both, or '0' to exit.")
        
        try:
            log_index = int(self.ask("\nEnter log number to mark as checked (0 to exit): ")) - 1
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
                
                while True:
                    another = self.ask("\nDo you want to mark another log as checked? (y/n): ").lower()
                    if another == 'y':
                        self.mark_as_checked()
                        break
                    elif another == 'n':
                        break
                    else:
                        print("Please enter 'y' or 'n'")
        except ValueError:
            print("Invalid input")
            self.ask("\nPress Enter to continue...")

    def mark_as_unchecked(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Mark Log as Unchecked" + self.term.normal)
        self.display_logs()
        
        while True:
            status_choice = self.ask("\nWhich status do you want to update? (q/j/b for Q/Jira/Both, 0 to exit): ").lower()
            if status_choice == '0':
                return
            if status_choice in ['q', 'j', 'b']:
                break
            print("Invalid choice. Please enter 'q' for Q, 'j' for Jira, 'b' for Both, or '0' to exit.")
        
        try:
            log_index = int(self.ask("\nEnter log number to mark as unchecked (0 to exit): ")) - 1
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
                
                while True:
                    another = self.ask("\nDo you want to mark another log as unchecked? (y/n): ").lower()
                    if another == 'y':
                        self.mark_as_unchecked()
                        break
                    elif another == 'n':
                        break
                    else:
                        print("Please enter 'y' or 'n'")
        except ValueError:
            print("Invalid input")
            self.ask("\nPress Enter to continue...")

    def mark_all_day_as_checked(self):
        while True:
            print(self.term.clear)
            print(self.term.move_y(0) + self.term.black_on_white + "Mark All Day as Checked" + self.term.normal)

            while True:
                status_choice = self.ask("\nWhich status do you want to update? (q/j/b for Q/Jira/Both, 0 to exit): ").lower()
                if status_choice == '0':
                    return
                if status_choice in ['q', 'j', 'b']:
                    break
                print("Invalid choice. Please enter 'q' for Q, 'j' for Jira, 'b' for Both, or '0' to exit.")

            dates_with_logs = sorted(
                set(log['timestamp'].split()[0] for log in self.logs),
                key=lambda d: datetime.strptime(d, "%d.%m.%Y"),
                reverse=True
            )
            last_5_days = dates_with_logs[:5]
            print("\nLast 5 days with logs:")
            for idx, d in enumerate(last_5_days, 1):
                print(f"  {idx}. {d}")
                logs_for_day = [log for log in self.logs if log['timestamp'].split()[0] == d]
                for log in logs_for_day:
                    hours = f" ({log['hours']})" if log.get('hours') else ""
                    print(f"      {log['ticket']}{hours}  Q:{log.get('q_status', '❌')} Jira:{log.get('jira_status', '❌')}")
            if not last_5_days:
                print("  (no logs yet)")
            date_prompt = f"\nEnter date (1-{len(last_5_days)} or DD.MM.YYYY): " if last_5_days else "\nEnter date (DD.MM.YYYY): "
            date_input = self.ask(date_prompt).strip()
            if last_5_days and date_input in [str(i) for i in range(1, len(last_5_days) + 1)]:
                date_str = last_5_days[int(date_input) - 1]
            else:
                date_str = date_input
            try:
                datetime.strptime(date_str, "%d.%m.%Y")
            except ValueError:
                print("Invalid date format. Please use 1-5 or DD.MM.YYYY.")
                self.ask("\nPress Enter to continue...")
                continue

            count = 0
            for log in self.logs:
                log_date = log['timestamp'].split()[0]
                if log_date == date_str:
                    if status_choice in ['q', 'b']:
                        log["q_status"] = "✅"
                    if status_choice in ['j', 'b']:
                        log["jira_status"] = "✅"
                    count += 1

            status_updated = []
            if status_choice in ['q', 'b']:
                status_updated.append("Q")
            if status_choice in ['j', 'b']:
                status_updated.append("Jira")
            print(f"\nMarked {count} log(s) as checked for {date_str} ({', '.join(status_updated)}).")
            if count > 0:
                self.save_logs()

            while True:
                again = self.ask("\nDo you want to do it for another date? (y/n): ").lower()
                if again == 'n':
                    return
                if again == 'y':
                    break
                print("Unesi 'y' ili 'n'.")

    def mark_all_day_as_unchecked(self):
        while True:
            print(self.term.clear)
            print(self.term.move_y(0) + self.term.black_on_white + "Mark All Day as Unchecked" + self.term.normal)

            while True:
                status_choice = self.ask("\nWhich status do you want to update? (q/j/b for Q/Jira/Both, 0 to exit): ").lower()
                if status_choice == '0':
                    return
                if status_choice in ['q', 'j', 'b']:
                    break
                print("Invalid choice. Please enter 'q' for Q, 'j' for Jira, 'b' for Both, or '0' to exit.")

            dates_with_logs = sorted(
                set(log['timestamp'].split()[0] for log in self.logs),
                key=lambda d: datetime.strptime(d, "%d.%m.%Y"),
                reverse=True
            )
            last_5_days = dates_with_logs[:5]
            print("\nLast 5 days with logs:")
            for idx, d in enumerate(last_5_days, 1):
                print(f"  {idx}. {d}")
                logs_for_day = [log for log in self.logs if log['timestamp'].split()[0] == d]
                for log in logs_for_day:
                    hours = f" ({log['hours']})" if log.get('hours') else ""
                    print(f"      {log['ticket']}{hours}  Q:{log.get('q_status', '❌')} Jira:{log.get('jira_status', '❌')}")
            if not last_5_days:
                print("  (no logs yet)")
            date_prompt = f"\nEnter date (1-{len(last_5_days)} or DD.MM.YYYY): " if last_5_days else "\nEnter date (DD.MM.YYYY): "
            date_input = self.ask(date_prompt).strip()
            if last_5_days and date_input in [str(i) for i in range(1, len(last_5_days) + 1)]:
                date_str = last_5_days[int(date_input) - 1]
            else:
                date_str = date_input
            try:
                datetime.strptime(date_str, "%d.%m.%Y")
            except ValueError:
                print("Invalid date format. Please use 1-5 or DD.MM.YYYY.")
                self.ask("\nPress Enter to continue...")
                continue

            count = 0
            for log in self.logs:
                log_date = log['timestamp'].split()[0]
                if log_date == date_str:
                    if status_choice in ['q', 'b']:
                        log["q_status"] = "❌"
                    if status_choice in ['j', 'b']:
                        log["jira_status"] = "❌"
                    count += 1

            status_updated = []
            if status_choice in ['q', 'b']:
                status_updated.append("Q")
            if status_choice in ['j', 'b']:
                status_updated.append("Jira")
            print(f"\nMarked {count} log(s) as unchecked for {date_str} ({', '.join(status_updated)}).")
            if count > 0:
                self.save_logs()

            while True:
                again = self.ask("\nDo you want to do it for another date? (y/n): ").lower()
                if again == 'n':
                    return
                if again == 'y':
                    break
                print("Unesi 'y' ili 'n'.")

    def edit_subtasks(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Edit Subtasks" + self.term.normal)
        self.display_logs()
        try:
            log_index = int(self.ask("\nEnter log number to edit subtasks (0 to exit): ")) - 1
            if log_index == -1:
                return
            
            if 0 <= log_index < len(self.logs):
                log = self.logs[log_index]
                if not log['subtasks']:
                    print("\nThis log has no subtasks.")
                    self.ask("\nPress Enter to continue...")
                    return
                
                print(f"\nCurrent subtasks for log {log_index + 1}:")
                for i, subtask in enumerate(log['subtasks'], 1):
                    print(f"{i}. {subtask}")
                
                while True:
                    print("\nOptions:")
                    print("1. Edit subtask")
                    print("2. Delete subtask")
                    print("0. Return to main menu")
                    
                    option = self.ask("\nEnter your choice (0-2): ").strip()
                    
                    if option == "0":
                        break
                    elif option in ["1", "2"]:
                        subtask_input = self.ask("\nEnter subtask number: ").strip()
                        try:
                            subtask_index = int(subtask_input) - 1
                            if 0 <= subtask_index < len(log['subtasks']):
                                if option == "1":
                                    print(f"\nCurrent subtask: {log['subtasks'][subtask_index]}")
                                    new_subtask = self.ask("Enter new subtask description: ")
                                    if new_subtask.strip():
                                        log['subtasks'][subtask_index] = new_subtask
                                        print("Subtask updated successfully!")
                                    else:
                                        print("Subtask description cannot be empty!")
                                else:
                                    deleted_subtask = log['subtasks'].pop(subtask_index)
                                    print(f"Deleted subtask: {deleted_subtask}")
                                
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
                self.ask("\nPress Enter to continue...")
        except ValueError:
            print("Invalid input")
            self.ask("\nPress Enter to continue...")

    def load_settings(self):
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
        with open(self.settings_file, 'w') as f:
            json.dump(self.settings, f, indent=2)

    def manage_settings(self):
        while True:
            choice = self.select_menu(
                "Settings",
                [
                    ("1", "Manage Log Types"),
                    ("2", "Configure Sprint Settings"),
                    ("3", "View Current Settings"),
                    ("4", "Return to Main Menu"),
                ],
            )

            if choice in (None, "4"):
                break
            if choice == "1":
                self.manage_log_types()
            elif choice == "2":
                self.configure_sprint_settings()
            elif choice == "3":
                self.view_settings()

    def manage_log_types(self):
        while True:
            current = "\nCurrent Log Types:"
            if self.settings["log_types"]:
                for i, log_type in enumerate(self.settings["log_types"], 1):
                    current += f"\n{i}. {log_type['name']} (Prefix: {log_type['prefix']})"
            else:
                current += "\n(none)"

            choice = self.select_menu(
                "Manage Log Types",
                [
                    ("1", "Add New Log Type"),
                    ("2", "Edit Existing Log Type"),
                    ("3", "Delete Log Type"),
                    ("4", "Return to Settings"),
                ],
                preamble=current,
            )

            if choice in (None, "4"):
                break

            try:
                if choice == "1":
                    name = self.ask("Enter log type name: ")
                    prefix = self.ask("Enter log type prefix: ")
                    self.settings["log_types"].append({
                        "name": name,
                        "prefix": prefix,
                        "status": "❌"
                    })
                    self.save_settings()
                    print("Log type added successfully!")
                    self.ask("\nPress Enter to continue...")

                elif choice == "2":
                    if not self.settings["log_types"]:
                        print("No log types to edit.")
                        self.ask("\nPress Enter to continue...")
                        continue

                    index = int(self.ask("Enter log type number to edit: ")) - 1
                    if 0 <= index < len(self.settings["log_types"]):
                        log_type = self.settings["log_types"][index]
                        name = self.ask(f"Enter new name [{log_type['name']}]: ") or log_type['name']
                        prefix = self.ask(f"Enter new prefix [{log_type['prefix']}]: ") or log_type['prefix']
                        self.settings["log_types"][index] = {
                            "name": name,
                            "prefix": prefix,
                            "status": log_type["status"]
                        }
                        self.save_settings()
                        print("Log type updated successfully!")
                    else:
                        print("Invalid log type number.")
                    self.ask("\nPress Enter to continue...")

                elif choice == "3":
                    if not self.settings["log_types"]:
                        print("No log types to delete.")
                        self.ask("\nPress Enter to continue...")
                        continue

                    index = int(self.ask("Enter log type number to delete: ")) - 1
                    if 0 <= index < len(self.settings["log_types"]):
                        del self.settings["log_types"][index]
                        self.save_settings()
                        print("Log type deleted successfully!")
                    else:
                        print("Invalid log type number.")
                    self.ask("\nPress Enter to continue...")

            except (ValueError, IndexError):
                print("Invalid input. Please enter a valid number.")
                self.ask("\nPress Enter to continue...")
            except KeyboardInterrupt:
                break

    def configure_sprint_settings(self):
        while True:
            preamble = (
                "\nCurrent Sprint Settings:\n"
                f"Start Date: {self.settings['sprint_config']['start_date']}\n"
                f"Duration: {self.settings['sprint_config']['duration_weeks']} weeks"
            )
            choice = self.select_menu(
                "Configure Sprint Settings",
                [
                    ("1", "Change Sprint Start Date"),
                    ("2", "Change Sprint Duration"),
                    ("3", "Return to Settings"),
                ],
                preamble=preamble,
            )

            if choice in (None, "3"):
                break

            try:
                if choice == "1":
                    while True:
                        new_date = self.ask("Enter new start date (YYYY-MM-DD): ")
                        try:
                            datetime.strptime(new_date, "%Y-%m-%d")
                            self.settings["sprint_config"]["start_date"] = new_date
                            self.save_settings()
                            print("Sprint start date updated successfully!")
                            break
                        except ValueError:
                            print("Invalid date format. Please use YYYY-MM-DD.")
                    self.ask("\nPress Enter to continue...")

                elif choice == "2":
                    while True:
                        try:
                            new_duration = int(self.ask("Enter new sprint duration in weeks: "))
                            if new_duration > 0:
                                self.settings["sprint_config"]["duration_weeks"] = new_duration
                                self.save_settings()
                                print("Sprint duration updated successfully!")
                                break
                            else:
                                print("Duration must be greater than 0.")
                        except ValueError:
                            print("Please enter a valid number.")
                    self.ask("\nPress Enter to continue...")

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
        
        self.ask("\nPress Enter to continue...")

    def get_sprint_dates(self, sprint_number=None):
        first_sprint_start = datetime.strptime(self.settings["sprint_config"]["start_date"], "%Y-%m-%d")
        sprint_duration = self.settings["sprint_config"]["duration_weeks"] * 7
        
        if sprint_number is None:
            now = datetime.now()
            days_since_first_sprint = (now - first_sprint_start).days
            sprint_number = days_since_first_sprint // sprint_duration
        
        sprint_start = first_sprint_start + timedelta(days=sprint_duration * sprint_number)
        sprint_end = sprint_start + timedelta(days=sprint_duration - 1)
        
        return sprint_start, sprint_end

    def view_sprint_history(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Sprint History" + self.term.normal)
        
        if not self.logs:
            print("\nNo logs found.")
            self.ask("\nPress Enter to continue...")
            return
            
        log_dates = [datetime.strptime(log['timestamp'].split()[0], "%d.%m.%Y") for log in self.logs]
        earliest_date = min(log_dates)
        latest_date = max(log_dates)
        
        first_sprint_start = datetime(2025, 4, 30)
        days_since_first_sprint = (earliest_date - first_sprint_start).days
        sprints_back = abs(days_since_first_sprint // 14)
        
        days_since_first_sprint = (latest_date - first_sprint_start).days
        sprints_forward = days_since_first_sprint // 14
        
        for i in range(-sprints_back, sprints_forward + 1):
            sprint_start, sprint_end = self.get_sprint_dates(i)
            
            sprint_logs = []
            for log in self.logs:
                log_date = datetime.strptime(log['timestamp'].split()[0], "%d.%m.%Y")
                if sprint_start <= log_date <= sprint_end:
                    sprint_logs.append(log)
            
            if sprint_logs or sprint_end < datetime.now():
                print(f"\nSprint Period: {sprint_start.strftime('%d.%m.%Y')} - {sprint_end.strftime('%d.%m.%Y')}")
                
                if sprint_logs:
                    sprint_logs.sort(key=lambda x: datetime.strptime(x['timestamp'].split()[0], "%d.%m.%Y"))
                    
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
        
        self.ask("\nPress Enter to continue...")

    def view_sprint_logs(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Current Sprint Logs" + self.term.normal)
        
        sprint_start, sprint_end = self.get_sprint_dates(None)
        print(f"\nSprint Period: {sprint_start.strftime('%d.%m.%Y')} - {sprint_end.strftime('%d.%m.%Y')}")
        print("-" * 72)
        
        sprint_logs = []
        for log in self.logs:
            log_date = datetime.strptime(log['timestamp'].split()[0], "%d.%m.%Y")
            if sprint_start <= log_date <= sprint_end:
                sprint_logs.append(log)
        
        if not sprint_logs:
            print("\nNo logs found for the current sprint.")
            self.ask("\nPress Enter to continue...")
            return
        
        qi_logs = {}
        for log in sprint_logs:
            if log['ticket'].startswith('QI-'):
                qi_number = log['ticket'].split()[0].split('[')[0]
                if '[Q]' in log['ticket'] or qi_number not in qi_logs:
                    qi_logs[qi_number] = log['ticket']
        
        if qi_logs:
            print("\nQI Tickets:")
            for qi_log in sorted(qi_logs.values()):
                print(f"  {self.term.cyan(qi_log)}")
            print("-" * 72)
        
        print("\nOther Logs:")
        sprint_logs.sort(key=lambda x: datetime.strptime(x['timestamp'].split()[0], "%d.%m.%Y"))
        
        current_date = None
        for log in sprint_logs:
            log_date = log['timestamp'].split()[0]
            if current_date != log_date:
                current_date = log_date
                print(f"\n  {self.term.yellow(current_date)}")
            print(f"    {self.term.cyan(log['ticket'])}")
        
        self.ask("\nPress Enter to continue...")

    def display_statistics(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Statistics and Charts" + self.term.normal)
        
        if not self.logs:
            print("\nNo logs found.")
            self.ask("\nPress Enter to continue...")
            return
        
        current_date = datetime.now()
        fourteen_days_ago = current_date - timedelta(days=13)
        
        recent_logs = []
        for log in self.logs:
            log_date = datetime.strptime(log['timestamp'].split()[0], "%d.%m.%Y")
            if log_date >= fourteen_days_ago:
                recent_logs.append(log)
        
        if not recent_logs:
            print("\nNo logs found in the last 10 workdays.")
            self.ask("\nPress Enter to continue...")
            return
        
        workdays = set()
        for log in recent_logs:
            log_date = datetime.strptime(log['timestamp'].split()[0], "%d.%m.%Y")
            if log_date.weekday() < 5:  # 0-4 are weekdays
                workdays.add(log_date.strftime("%d.%m.%Y"))
        
        workdays = sorted(list(workdays), key=lambda x: datetime.strptime(x, "%d.%m.%Y"), reverse=True)[:10]
        
        recent_logs = [log for log in recent_logs if log['timestamp'].split()[0] in workdays]
        
        total_logs = len(recent_logs)
        
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
        
        hours_per_day = {}
        for log in recent_logs:
            date = log['timestamp'].split()[0]
            if date not in hours_per_day:
                hours_per_day[date] = 0
            hours_per_day[date] += self.parse_hours(log['hours'])
        
        print("\n" + self.term.underline + "Summary Statistics (Last 10 Workdays):" + self.term.normal)
        print(f"Total Logs: {total_logs}")
        for type_name, stats in completion_stats.items():
            print(f"Completed {type_name} Logs: {stats['completed']} ({stats['percentage']:.1f}%)")
        
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
        
        print("\n" + self.term.underline + "Hours per Workday:" + self.term.normal)
        max_hours = max(hours_per_day.values()) if hours_per_day else 0
        chart_width = 50
        
        for date in workdays:
            hours = hours_per_day.get(date, 0)
            bar_length = int((hours / max_hours) * chart_width) if max_hours > 0 else 0
            bar = "█" * bar_length
            hours_str = self.format_hours(hours)
            if date == current_date.strftime("%d.%m.%Y"):
                print(f"{date}*: {bar} {hours_str}")
            else:
                print(f"{date}: {bar} {hours_str}")
        
        print("\n" + self.term.underline + "Logs per Workday:" + self.term.normal)
        logs_by_date = {}
        for log in recent_logs:
            date = log['timestamp'].split()[0]
            if date not in logs_by_date:
                logs_by_date[date] = 0
            logs_by_date[date] += 1
        
        max_logs = max(logs_by_date.values()) if logs_by_date else 0
        
        for date in workdays:
            num_logs = logs_by_date.get(date, 0)
            bar_length = int((num_logs / max_logs) * chart_width) if max_logs > 0 else 0
            bar = "█" * bar_length
            if date == current_date.strftime("%d.%m.%Y"):
                print(f"{date}*: {bar} {num_logs} logs")
            else:
                print(f"{date}: {bar} {num_logs} logs")
        
        print("\n* Today's date")
        self.ask("\nPress Enter to continue...")

    def load_scripts(self):
        if os.path.exists(self.scripts_file):
            with open(self.scripts_file, 'r') as f:
                self.scripts = json.load(f)
        else:
            self.scripts = []
            self.save_scripts()

    def save_scripts(self):
        with open(self.scripts_file, 'w') as f:
            json.dump(self.scripts, f, indent=2)

    def log_migration_script(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Log Migration Script" + self.term.normal)
        
        ticket = self.ask("\nEnter ticket: ").strip()
        if not ticket or ticket.lower() in ['0', 'exit']:
            return
        
        print("\nEnter migration script (press Enter twice to finish):")
        print("(You can enter multiple lines with spaces and newlines)")
        script_lines = []
        while True:
            line = self.ask("")
            if line.lower() in ['0', 'exit']:
                return
            if line == "" and script_lines and script_lines[-1] == "":
                # end input: two empty lines
                script_lines.pop()
                break
            script_lines.append(line)
        
        script = '\n'.join(script_lines)
        if not script.strip():
            print("Script cannot be empty!")
            self.ask("\nPress Enter to continue...")
            return
        
        while True:
            demo_status = self.ask("Update Demo status (x for ❌, c for ✅): ").lower()
            if demo_status in ['x', 'c']:
                break
            print("Invalid choice. Please enter 'x' for ❌ or 'c' for ✅")
        
        while True:
            stage_status = self.ask("Update Stage status (x for ❌, c for ✅): ").lower()
            if stage_status in ['x', 'c']:
                break
            print("Invalid choice. Please enter 'x' for ❌ or 'c' for ✅")
        
        while True:
            release_status = self.ask("Update Release notes status (x for ❌, c for ✅): ").lower()
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
        self.ask("\nPress Enter to continue...")

    def view_migration_scripts(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Migration Scripts" + self.term.normal)
        
        if not self.scripts:
            print("\nNo migration scripts found.")
            self.ask("\nPress Enter to continue...")
            return
        
        print("\nMigration Scripts:")
        print("-" * 72)
        for i, script in enumerate(self.scripts, 1):
            print(f"\n{i}. Ticket: {script['ticket']}")
            print(f"   Timestamp: {script['timestamp']}")
            print(f"   Script:")
            script_lines = script['script'].split('\n')
            for line in script_lines:
                print(f"      {line}")
            print(f"   Demo: {script.get('demo_status', '❌')}")
            print(f"   Stage: {script.get('stage_status', '❌')}")
            print(f"   Release Notes: {script.get('release_status', '❌')}")
            print("-" * 72)
        
        self.ask("\nPress Enter to continue...")

    def edit_migration_script(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Edit Migration Script" + self.term.normal)
        
        if not self.scripts:
            print("\nNo migration scripts found.")
            self.ask("\nPress Enter to continue...")
            return
        
        print("\nMigration Scripts:")
        print("-" * 72)
        for i, script in enumerate(self.scripts, 1):
            print(f"\n{i}. Ticket: {script['ticket']}")
            print(f"   Timestamp: {script['timestamp']}")
            print(f"   Script:")
            script_lines = script['script'].split('\n')
            for line in script_lines:
                print(f"      {line}")
            print(f"   Demo: {script.get('demo_status', '❌')}")
            print(f"   Stage: {script.get('stage_status', '❌')}")
            print(f"   Release Notes: {script.get('release_status', '❌')}")
            print("-" * 72)
        
        try:
            script_index = int(self.ask("\nEnter script number to edit (0 to exit): ")) - 1
            if script_index == -1:
                return
            
            if 0 <= script_index < len(self.scripts):
                script = self.scripts[script_index]
                
                print(f"\nCurrent ticket: {script['ticket']}")
                new_ticket = self.ask("Enter new ticket (press Enter to keep current): ").strip()
                if new_ticket:
                    script['ticket'] = new_ticket
                
                print(f"\nCurrent script:")
                script_lines = script['script'].split('\n')
                for line in script_lines:
                    print(f"      {line}")
                print("\nEnter new script (press Enter twice to finish, or just Enter to keep current):")
                print("(You can enter multiple lines with spaces and newlines)")
                new_script_lines = []
                while True:
                    line = self.ask("")
                    if line == "" and new_script_lines and new_script_lines[-1] == "":
                        # end input: two empty lines
                        new_script_lines.pop()
                        break
                    if line == "" and not new_script_lines:
                        # empty = keep current
                        break
                    new_script_lines.append(line)
                
                if new_script_lines:
                    new_script = '\n'.join(new_script_lines)
                    if new_script.strip():
                        script['script'] = new_script
                    else:
                        print("Script cannot be empty, keeping current script.")
                
                print(f"\nCurrent Demo status: {script.get('demo_status', '❌')}")
                while True:
                    demo_status = self.ask("Update Demo status (x for ❌, c for ✅, Enter to keep current): ").lower()
                    if not demo_status:
                        break
                    if demo_status in ['x', 'c']:
                        script['demo_status'] = "✅" if demo_status == "c" else "❌"
                        break
                    print("Invalid choice. Please enter 'x' for ❌ or 'c' for ✅")
                
                print(f"\nCurrent Stage status: {script.get('stage_status', '❌')}")
                while True:
                    stage_status = self.ask("Update Stage status (x for ❌, c for ✅, Enter to keep current): ").lower()
                    if not stage_status:
                        break
                    if stage_status in ['x', 'c']:
                        script['stage_status'] = "✅" if stage_status == "c" else "❌"
                        break
                    print("Invalid choice. Please enter 'x' for ❌ or 'c' for ✅")
                
                print(f"\nCurrent Release notes status: {script.get('release_status', '❌')}")
                while True:
                    release_status = self.ask("Update Release notes status (x for ❌, c for ✅, Enter to keep current): ").lower()
                    if not release_status:
                        break
                    if release_status in ['x', 'c']:
                        script['release_status'] = "✅" if release_status == "c" else "❌"
                        break
                    print("Invalid choice. Please enter 'x' for ❌ or 'c' for ✅")
                
                self.scripts[script_index] = script
                self.save_scripts()
                print("\nMigration script updated successfully!")
                self.ask("\nPress Enter to continue...")
        except ValueError:
            print("Invalid input")
            self.ask("\nPress Enter to continue...")

    def delete_migration_script(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Delete Migration Script" + self.term.normal)
        
        if not self.scripts:
            print("\nNo migration scripts found.")
            self.ask("\nPress Enter to continue...")
            return
        
        print("\nMigration Scripts:")
        print("-" * 72)
        for i, script in enumerate(self.scripts, 1):
            print(f"\n{i}. Ticket: {script['ticket']}")
            print(f"   Timestamp: {script['timestamp']}")
            print(f"   Script:")
            script_lines = script['script'].split('\n')
            for line in script_lines:
                print(f"      {line}")
            print(f"   Demo: {script.get('demo_status', '❌')}")
            print(f"   Stage: {script.get('stage_status', '❌')}")
            print(f"   Release Notes: {script.get('release_status', '❌')}")
            print("-" * 72)
        
        try:
            script_index = int(self.ask("\nEnter script number to delete (0 to exit): ")) - 1
            if script_index == -1:
                return
            
            if 0 <= script_index < len(self.scripts):
                confirm = self.ask(f"Are you sure you want to delete script {script_index + 1}? (y/n): ").lower()
                if confirm == 'y':
                    deleted_script = self.scripts.pop(script_index)
                    print(f"Deleted script: {deleted_script['ticket']}")
                    self.save_scripts()
                    self.ask("\nPress Enter to continue...")
        except ValueError:
            print("Invalid input")
            self.ask("\nPress Enter to continue...")

    def load_links(self):
        try:
            links_file = os.path.join(self.script_dir, "links.json")
            with open(links_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"links": []}

    def save_links(self):
        links_file = os.path.join(self.script_dir, "links.json")
        with open(links_file, 'w') as f:
            json.dump(self.links, f, indent=4)
            
        backup_file = os.path.join(self.script_dir, "backup", "links_backup.json")
        with open(backup_file, 'w') as f:
            json.dump(self.links, f, indent=4)

    def add_link(self):
        print(self.term.clear)
        print(self.term.black_on_white + "Add Important Link" + self.term.normal)
        
        link = self.ask("\nEnter the link: ").strip()
        if not link:
            print("Link cannot be empty!")
            self.ask("\nPress Enter to continue...")
            return
        
        comments = self.ask("Enter comments (optional): ").strip()
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self.links["links"].append({
            "timestamp": timestamp,
            "link": link,
            "comments": comments
        })
        
        self.save_links()
        print("\nLink added successfully!")
        self.ask("\nPress Enter to continue...")

    def view_links(self):
        print(self.term.clear)
        print(self.term.black_on_white + "Important Links" + self.term.normal)
        
        if not self.links["links"]:
            print("\nNo links found!")
            self.ask("\nPress Enter to continue...")
            return
        
        print("\nLinks:")
        print("-" * 72)
        for i, link in enumerate(self.links["links"], 1):
            print(f"{i}. created: {link['timestamp']}")
            print(f"   link: @{link['link']}")
            if link['comments']:
                print(f"   Comments: {link['comments']}")
            print("-" * 72)
        
        self.ask("\nPress Enter to continue...")

    def edit_link(self):
        print(self.term.clear)
        print(self.term.black_on_white + "Edit Important Link" + self.term.normal)
        
        if not self.links["links"]:
            print("\nNo links found!")
            self.ask("\nPress Enter to continue...")
            return
        
        for i, link in enumerate(self.links["links"], 1):
            print(f"\n{i}. {link['link']}")
            print(f"   Timestamp: {link['timestamp']}")
            if link['comments']:
                print(f"   Comments: {link['comments']}")
        
        try:
            choice = int(self.ask("\nEnter the number of the link to edit (0 to cancel): "))
            if choice == 0:
                return
            if 1 <= choice <= len(self.links["links"]):
                link = self.links["links"][choice - 1]
                print(f"\nCurrent link: {link['link']}")
                new_link = self.ask("Enter new link (press Enter to keep current): ").strip()
                if new_link:
                    link['link'] = new_link
                
                print(f"\nCurrent comments: {link['comments']}")
                new_comments = self.ask("Enter new comments (press Enter to keep current): ").strip()
                if new_comments:
                    link['comments'] = new_comments
                
                link['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.save_links()
                print("\nLink updated successfully!")
            else:
                print("\nInvalid choice!")
        except ValueError:
            print("\nPlease enter a valid number!")
        
        self.ask("\nPress Enter to continue...")

    def delete_link(self):
        print(self.term.clear)
        print(self.term.black_on_white + "Delete Important Link" + self.term.normal)
        
        if not self.links["links"]:
            print("\nNo links found!")
            self.ask("\nPress Enter to continue...")
            return
        
        for i, link in enumerate(self.links["links"], 1):
            print(f"\n{i}. {link['link']}")
            print(f"   Timestamp: {link['timestamp']}")
            if link['comments']:
                print(f"   Comments: {link['comments']}")
        
        try:
            choice = int(self.ask("\nEnter the number of the link to delete (0 to cancel): "))
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
        
        self.ask("\nPress Enter to continue...")

    def view_logs_for_date(self):
        print(self.term.clear)
        print(self.term.black_on_white + "View Logs for a Date" + self.term.normal)

        dates_with_logs = sorted(
            set(log['timestamp'].split()[0] for log in self.logs),
            key=lambda d: datetime.strptime(d, "%d.%m.%Y"),
            reverse=True
        )
        last_5_days = dates_with_logs[:5]
        print("\nLast 5 days with logs:")
        for idx, d in enumerate(last_5_days, 1):
            print(f"  {idx}. {d}")
            logs_for_day = [log for log in self.logs if log['timestamp'].split()[0] == d]
            for log in logs_for_day:
                hours = f" ({log['hours']})" if log.get('hours') else ""
                print(f"      {log['ticket']}{hours}  Q:{log.get('q_status', '❌')} Jira:{log.get('jira_status', '❌')}")
        if not last_5_days:
            print("  (no logs yet)")
        date_prompt = f"\nEnter date (1-{len(last_5_days)} or DD.MM.YYYY): " if last_5_days else "\nEnter date (DD.MM.YYYY): "
        date_input = self.ask(date_prompt).strip()
        if last_5_days and date_input in [str(i) for i in range(1, len(last_5_days) + 1)]:
            date_str = last_5_days[int(date_input) - 1]
        else:
            date_str = date_input
        try:
            datetime.strptime(date_str, "%d.%m.%Y")
        except ValueError:
            print("Invalid date format. Please use 1-5 or DD.MM.YYYY.")
            self.ask("\nPress Enter to continue...")
            return

        found = False
        output_lines = []
        for log in self.logs:
            log_date = log['timestamp'].split()[0]
            if log_date == date_str:
                if not found:
                    output_lines.append(date_str)
                    found = True
                ticket_line = log['ticket']
                if log['hours']:
                    ticket_line += f" ({log['hours']})"
                output_lines.append(ticket_line)
                for sub in log.get('subtasks', []):
                    output_lines.append(f"   └─ {sub}")
        if not found:
            print(f"\nNo logs found for {date_str}.")
        else:
            print("\n" + "\n".join(output_lines))
        self.ask("\nPress Enter to continue...")

    def list_available_sprints(self):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + "Available Sprints" + self.term.normal)
        
        if not self.logs:
            print("\nNo logs found.")
            self.ask("\nPress Enter to continue...")
            return None
            
        log_dates = [datetime.strptime(log['timestamp'].split()[0], "%d.%m.%Y") for log in self.logs]
        earliest_date = min(log_dates)
        latest_date = max(log_dates)
        
        first_sprint_start = datetime.strptime(self.settings["sprint_config"]["start_date"], "%Y-%m-%d")
        sprint_duration = self.settings["sprint_config"]["duration_weeks"] * 7
        
        days_since_first_sprint = (earliest_date - first_sprint_start).days
        sprints_back = abs(days_since_first_sprint // sprint_duration)
        
        days_since_first_sprint = (latest_date - first_sprint_start).days
        sprints_forward = days_since_first_sprint // sprint_duration
        
        available_sprints = []
        for i in range(-sprints_back, sprints_forward + 1):
            sprint_start, sprint_end = self.get_sprint_dates(i)
            
            sprint_logs = []
            for log in self.logs:
                log_date = datetime.strptime(log['timestamp'].split()[0], "%d.%m.%Y")
                if sprint_start <= log_date <= sprint_end:
                    sprint_logs.append(log)
            
            if sprint_logs or sprint_end < datetime.now():
                available_sprints.append({
                    'sprint_number': i,
                    'start_date': sprint_start,
                    'end_date': sprint_end,
                    'logs_count': len(sprint_logs)
                })
        
        if not available_sprints:
            print("\nNo sprints found.")
            self.ask("\nPress Enter to continue...")
            return None
        
        print("\nAvailable Sprints:")
        print("-" * 50)
        for i, sprint in enumerate(available_sprints, 1):
            sprint_num = sprint['sprint_number']
            start_date = sprint['start_date'].strftime('%d.%m.%Y')
            end_date = sprint['end_date'].strftime('%d.%m.%Y')
            logs_count = sprint['logs_count']
            
            current_marker = ""
            if sprint_num == self.get_current_sprint_number():
                current_marker = " (Current)"
            
            print(f"{i}. Sprint {sprint_num}: {start_date} - {end_date} ({logs_count} logs){current_marker}")
        
        try:
            choice = int(self.ask(f"\nEnter sprint number (1-{len(available_sprints)}) or 0 to cancel: "))
            if choice == 0:
                return None
            if 1 <= choice <= len(available_sprints):
                return available_sprints[choice - 1]['sprint_number']
            else:
                print("\nInvalid choice!")
                self.ask("\nPress Enter to continue...")
                return None
        except ValueError:
            print("\nPlease enter a valid number!")
            self.ask("\nPress Enter to continue...")
            return None

    def get_current_sprint_number(self):
        now = datetime.now()
        first_sprint_start = datetime.strptime(self.settings["sprint_config"]["start_date"], "%Y-%m-%d")
        sprint_duration = self.settings["sprint_config"]["duration_weeks"] * 7
        days_since_first_sprint = (now - first_sprint_start).days
        return days_since_first_sprint // sprint_duration

    def view_specific_sprint(self, sprint_number):
        print(self.term.clear)
        print(self.term.move_y(0) + self.term.black_on_white + f"Sprint {sprint_number} Logs" + self.term.normal)
        
        sprint_start, sprint_end = self.get_sprint_dates(sprint_number)
        print(f"\nSprint Period: {sprint_start.strftime('%d.%m.%Y')} - {sprint_end.strftime('%d.%m.%Y')}")
        print("-" * 72)
        
        sprint_logs = []
        for log in self.logs:
            log_date = datetime.strptime(log['timestamp'].split()[0], "%d.%m.%Y")
            if sprint_start <= log_date <= sprint_end:
                sprint_logs.append(log)
        
        if not sprint_logs:
            print("\nNo logs found for this sprint.")
            self.ask("\nPress Enter to continue...")
            return
        
        qi_logs = {}
        for log in sprint_logs:
            if log['ticket'].startswith('QI-'):
                qi_number = log['ticket'].split()[0].split('[')[0]
                if '[Q]' in log['ticket'] or qi_number not in qi_logs:
                    qi_logs[qi_number] = log['ticket']
        
        if qi_logs:
            print("\nQI Tickets:")
            for qi_log in sorted(qi_logs.values()):
                print(f"  {self.term.cyan(qi_log)}")
            print("-" * 72)
        
        print("\nOther Logs:")
        sprint_logs.sort(key=lambda x: datetime.strptime(x['timestamp'].split()[0], "%d.%m.%Y"))
        
        current_date = None
        for log in sprint_logs:
            log_date = log['timestamp'].split()[0]
            if current_date != log_date:
                current_date = log_date
                print(f"\n  {self.term.yellow(current_date)}")
            print(f"    {self.term.cyan(log['ticket'])}")
        
        self.ask("\nPress Enter to continue...")

    def run(self):
        while self.running:
            try:
                banner = self.term.cyan(self.banner) if self.banner else None
                choice = self.select_menu(
                    "B-Logger",
                    [
                        ("1", "Logs"),
                        ("2", "Sprint"),
                        ("3", "Migration script"),
                        ("4", "Important Links"),
                        ("5", "Settings"),
                        ("6", "Help"),
                        ("7", "Statistics"),
                        ("8", "About"),
                        ("9", "Exit"),
                    ],
                    preamble=banner,
                )

                if choice is None:
                    continue

                if choice == "1":
                    while True:
                        subchoice = self.select_menu(
                            "Logs Menu",
                            [
                                ("1", "Create log"),
                                ("2", "View logs"),
                                ("3", "Edit log"),
                                ("4", "Delete log"),
                                ("5", "Mark as checked"),
                                ("6", "Mark as unchecked"),
                                ("7", "Edit subtasks"),
                                ("8", "View logs for a date"),
                                ("9", "Mark all day as checked"),
                                ("10", "Mark all day as unchecked"),
                                ("0", "Back to main menu"),
                            ],
                        )
                        if subchoice in (None, "0"):
                            break
                        elif subchoice == "1":
                            self.create_new_log()
                        elif subchoice == "2":
                            self.view_logs()
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
                        elif subchoice == "9":
                            self.mark_all_day_as_checked()
                        elif subchoice == "10":
                            self.mark_all_day_as_unchecked()

                elif choice == "2":
                    while True:
                        subchoice = self.select_menu(
                            "Sprint Menu",
                            [
                                ("1", "View current sprint"),
                                ("2", "View sprint by date"),
                                ("3", "View sprint history"),
                                ("0", "Back to main menu"),
                            ],
                        )
                        if subchoice in (None, "0"):
                            break
                        elif subchoice == "1":
                            self.view_sprint_logs()
                        elif subchoice == "2":
                            selected_sprint = self.list_available_sprints()
                            if selected_sprint is not None:
                                self.view_specific_sprint(selected_sprint)
                        elif subchoice == "3":
                            self.view_sprint_history()

                elif choice == "3":
                    while True:
                        subchoice = self.select_menu(
                            "Migration Script Menu",
                            [
                                ("1", "Create migration script"),
                                ("2", "View migration scripts"),
                                ("3", "Edit migration script"),
                                ("4", "Delete migration script"),
                                ("0", "Back to main menu"),
                            ],
                        )
                        if subchoice in (None, "0"):
                            break
                        elif subchoice == "1":
                            self.log_migration_script()
                        elif subchoice == "2":
                            self.view_migration_scripts()
                        elif subchoice == "3":
                            self.edit_migration_script()
                        elif subchoice == "4":
                            self.delete_migration_script()

                elif choice == "4":
                    while True:
                        subchoice = self.select_menu(
                            "Important Links Menu",
                            [
                                ("1", "Add link"),
                                ("2", "View links"),
                                ("3", "Edit link"),
                                ("4", "Delete link"),
                                ("0", "Back to main menu"),
                            ],
                        )
                        if subchoice in (None, "0"):
                            break
                        elif subchoice == "1":
                            self.add_link()
                        elif subchoice == "2":
                            self.view_links()
                        elif subchoice == "3":
                            self.edit_link()
                        elif subchoice == "4":
                            self.delete_link()

                elif choice == "5":
                    self.manage_settings()

                elif choice == "6":
                    self.display_help()

                elif choice == "7":
                    self.display_statistics()

                elif choice == "8":
                    self.display_about()

                elif choice == "9":
                    self.running = False
                    break

            except KeyboardInterrupt:
                print("\nExiting B-LOGGER...")
                self.running = False
                break

if __name__ == "__main__":
    logger = BLogger()
    logger.run()
