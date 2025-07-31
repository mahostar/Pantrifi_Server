import json
import os
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import IntPrompt
from rich.text import Text
from rich import box
from rich.align import Align

class ScheduleConfigurator:
    def __init__(self):
        self.console = Console()
        self.base_path = Path(__file__).resolve().parent
        self.config_file = self.base_path / "schedule_config.json"
        self.running = True
    
    def display_current_time(self):
        """Display current system time with rich formatting."""
        current_time = datetime.now()
        
        time_table = Table(show_header=False, box=box.ROUNDED, expand=False)
        time_table.add_column("Info", style="cyan", width=20)
        time_table.add_column("Value", style="bright_white", width=30)
        
        time_table.add_row("🕐 Current Date", current_time.strftime("%A, %B %d, %Y"))
        time_table.add_row("⏰ Current Time", current_time.strftime("%I:%M:%S %p"))
        time_table.add_row("🌍 24-Hour Format", current_time.strftime("%H:%M:%S"))
        
        panel = Panel(
            time_table,
            title="[bold blue]🕒 System Time Information[/bold blue]",
            border_style="blue"
        )
        
        self.console.print(panel)
    
    def get_time_input(self) -> Optional[datetime]:
        """Interactive time selection with rich interface."""
        self.console.print("\n[bold yellow]⏰ Set Your Daily Trigger Time[/bold yellow]")
        
        format_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
        format_table.add_column("Option", style="cyan")
        format_table.add_column("Description", style="white")
        format_table.add_row("1", "12-hour format (e.g., 7:30 AM)")
        format_table.add_row("2", "24-hour format (e.g., 07:30)")
        
        self.console.print(Panel(format_table, title="Time Format Options", border_style="green"))
        
        try:
            format_choice = IntPrompt.ask(
                "[bold green]Choose time format[/bold green]",
                choices=["1", "2"],
                default=1
            )
        except KeyboardInterrupt:
            self.console.print("\n[red]Operation cancelled.[/red]")
            return None
        
        if format_choice == 1:
            return self._get_12_hour_time()
        else:
            return self._get_24_hour_time()
    
    def _get_time_from_user(self, is_12_hour: bool) -> Optional[datetime]:
        """A unified function to get time input from the user."""
        prompt_style = "12-hour" if is_12_hour else "24-hour"
        self.console.print(f"\n[bold cyan]📝 Enter time in {prompt_style} format[/bold cyan]")
        
        while self.running:
            try:
                if is_12_hour:
                    hour = IntPrompt.ask("[green]Hour (1-12)[/green]", choices=[str(i) for i in range(1, 13)])
                else:
                    hour = IntPrompt.ask("[green]Hour (0-23)[/green]", choices=[str(i) for i in range(0, 24)])
                
                minute = IntPrompt.ask("[green]Minute (0-59)[/green]", choices=[str(i) for i in range(0, 60)], default=0)
                
                hour_24, display_time = hour, f"{hour:02d}:{minute:02d}"

                if is_12_hour:
                    period_choice = IntPrompt.ask("[green]Select period (1 for AM, 2 for PM)[/green]", choices=["1", "2"])
                    period = "AM" if period_choice == 1 else "PM"
                    display_time = f"{hour}:{minute:02d} {period}"
                    
                    if period == "AM" and hour == 12: hour_24 = 0
                    elif period == "PM" and hour != 12: hour_24 = hour + 12
                    else: hour_24 = hour

                now = datetime.now()
                scheduled_time = now.replace(hour=hour_24, minute=minute, second=0, microsecond=0)
                
                if scheduled_time <= now:
                    scheduled_time += timedelta(days=1)
                
                self._confirm_time_selection(scheduled_time, display_time)
                return scheduled_time
                
            except KeyboardInterrupt:
                self.console.print("\n[red]Operation cancelled.[/red]")
                return None
            except Exception as e:
                self.console.print(f"[red]Invalid input: {e}. Please try again.[/red]")
        return None

    def _get_12_hour_time(self) -> Optional[datetime]:
        return self._get_time_from_user(is_12_hour=True)

    def _get_24_hour_time(self) -> Optional[datetime]:
        return self._get_time_from_user(is_12_hour=False)

    def _confirm_time_selection(self, scheduled_time: datetime, display_time: str):
        """Confirm the selected time with the user."""
        confirmation_table = Table(show_header=False, box=box.ROUNDED)
        confirmation_table.add_column("Detail", style="cyan", no_wrap=True)
        confirmation_table.add_column("Value", style="bright_white")
        
        confirmation_table.add_row("⏰ Selected Time", display_time)
        confirmation_table.add_row("📅 Next Execution", scheduled_time.strftime("%A, %B %d, %Y at %I:%M %p"))
        
        panel = Panel(
            confirmation_table,
            title="[bold green]✅ Time Confirmation[/bold green]",
            border_style="green"
        )
        self.console.print(panel)
    
    def save_schedule_config(self, scheduled_time: datetime):
        """Save the scheduled time to a JSON configuration file."""
        config_data = {
            "scheduled_hour": scheduled_time.hour,
            "scheduled_minute": scheduled_time.minute,
            "last_updated": datetime.now().isoformat(),
            "next_execution": scheduled_time.isoformat()
        }
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2)
            
            self.console.print(f"\n[bold green]✅ Schedule configuration saved to {self.config_file}[/bold green]")
            self.console.print(f"[dim]Next execution: {scheduled_time.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
            
        except Exception as e:
            self.console.print(f"[bold red]❌ Error saving configuration: {e}[/bold red]")
    
    def load_existing_config(self):
        """Load and display existing configuration if it exists."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                existing_table = Table(show_header=False, box=box.ROUNDED)
                existing_table.add_column("Setting", style="cyan")
                existing_table.add_column("Value", style="bright_white")
                
                existing_table.add_row("⏰ Current Schedule", f"{config_data['scheduled_hour']:02d}:{config_data['scheduled_minute']:02d}")
                existing_table.add_row("📅 Last Updated", config_data.get('last_updated', 'Unknown'))
                
                panel = Panel(
                    existing_table,
                    title="[bold yellow]📋 Existing Configuration[/bold yellow]",
                    border_style="yellow"
                )
                self.console.print(panel)
                return True
                
            except Exception as e:
                self.console.print(f"[red]Error reading existing config: {e}[/red]")
        return False
    
    def start(self):
        """Start the configuration application."""
        try:
            welcome_text = Text("🍽️ PANTRIFI SCHEDULE CONFIGURATOR 🍽️", style="bold magenta")
            self.console.print(Panel(Align.center(welcome_text), box=box.DOUBLE, border_style="magenta"))
            
            self.display_current_time()
            
            # Show existing configuration if available
            has_existing = self.load_existing_config()
            if has_existing:
                self.console.print("\n[yellow]You can update the existing schedule or keep the current one.[/yellow]")
            
            scheduled_time = self.get_time_input()
            if scheduled_time is None or not self.running:
                self.console.print("[yellow]No time configured. Exiting.[/yellow]")
                return
            
            self.save_schedule_config(scheduled_time)
        
        except KeyboardInterrupt:
            self.console.print("\n[red]🛑 Configuration cancelled by user.[/red]")
        except Exception as e:
            self.console.print(f"\n[bold red]❌ A fatal error occurred: {e}[/bold red]")
        finally:
            self.console.print("[dim]👋 Configuration complete![/dim]")

def main():
    """Main entry point"""
    configurator = ScheduleConfigurator()
    configurator.start()

if __name__ == "__main__":
    main()