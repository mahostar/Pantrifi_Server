import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from supabase import create_client, Client
from rich.console import Console
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_supabase_client() -> Client:
    """Initialize and return Supabase client."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")  # or SUPABASE_SERVICE_ROLE_KEY for service role
    
    if not url or not key:
        raise ValueError("Please set SUPABASE_URL and SUPABASE_ANON_KEY environment variables")
    
    return create_client(url, key)

def load_users_data(json_file: str = "extract_users_subscriptions.json") -> List[Dict[str, Any]]:
    """Load and filter users from the JSON file for subscribed/trialing users only."""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Filter for only subscribed and trialing users
        subscribed_users = []
        for user in data.get('users', []):
            status = user.get('subscription_status', '').lower()
            if status in ['active', 'trialing']:
                subscribed_users.append(user)
        
        return subscribed_users
    
    except FileNotFoundError:
        raise FileNotFoundError(f"File '{json_file}' not found. Please run extract_users_subscriptions.py first.")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON format in '{json_file}'")

def fetch_user_sheets(supabase: Client, user_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Fetch Google Sheets data for the given user IDs."""
    try:
        # Get sheets for all user IDs in one query
        response = supabase.table("sheet_table").select("*").in_("user_id", user_ids).eq("is_active", True).execute()
        sheets_data = response.data
        
        # Group sheets by user_id
        user_sheets = {}
        for sheet in sheets_data:
            user_id = sheet['user_id']
            if user_id not in user_sheets:
                user_sheets[user_id] = []
            user_sheets[user_id].append({
                'sheet_id': sheet['id'],
                'sheet_name': sheet['sheet_name'],
                'sheet_url': sheet['sheet_url'],
                'description': sheet['description'],
                'created_at': sheet['created_at'],
                'updated_at': sheet['updated_at']
            })
        
        # Sort sheets by creation date (newest first) and limit to 3 per user
        for user_id in user_sheets:
            user_sheets[user_id].sort(key=lambda x: x['created_at'], reverse=True)
            user_sheets[user_id] = user_sheets[user_id][:3]  # Max 3 sheets per user
        
        return user_sheets
    
    except Exception as e:
        print(f"Error fetching sheets data: {e}")
        return {}

def fetch_user_menus(supabase: Client, user_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Fetch menu data for the given user IDs."""
    try:
        # Get menus for all user IDs in one query
        response = supabase.table("menu").select("*").in_("user_id", user_ids).execute()
        menus_data = response.data
        
        # Group menus by user_id
        user_menus = {}
        for menu in menus_data:
            user_id = menu['user_id']
            if user_id not in user_menus:
                user_menus[user_id] = []
            user_menus[user_id].append({
                'menu_id': menu['id'],
                'file_name': menu['file_name'],
                'file_url': menu['file_url']
            })
        
        return user_menus
    
    except Exception as e:
        print(f"Error fetching menu data: {e}")
        return {}

def fetch_user_csv_files(supabase: Client, user_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Fetch CSV files data from Supabase csv table for the given user IDs."""
    try:
        # Get CSV files for all user IDs from the csv table
        response = supabase.table("csv").select("*").in_("user_id", user_ids).execute()
        csv_data = response.data
        
        # Group CSV files by user_id
        user_csv_files = {}
        for csv_file in csv_data:
            user_id = csv_file['user_id']
            if user_id not in user_csv_files:
                user_csv_files[user_id] = []
            user_csv_files[user_id].append({
                'csv_id': csv_file['id'],
                'file_name': csv_file['file_name'],
                'file_url': csv_file['file_url'],
                'created_at': csv_file.get('created_at', ''),
                'updated_at': csv_file.get('updated_at', '')
            })
        
        # Sort CSV files by creation date if available (newest first) and limit to 3 per user
        for user_id in user_csv_files:
            if user_csv_files[user_id] and user_csv_files[user_id][0].get('created_at'):
                user_csv_files[user_id].sort(key=lambda x: x.get('created_at', ''), reverse=True)
            user_csv_files[user_id] = user_csv_files[user_id][:3]  # Max 3 CSV files per user
        
        return user_csv_files
    
    except Exception as e:
        print(f"Error fetching CSV files data: {e}")
        return {}

def generate_user_notes(sheets_count: int, menus_count: int, csv_count: int) -> str:
    """Generate personalized notes based on what the user has uploaded."""
    has_sheets = sheets_count > 0
    has_menus = menus_count > 0
    has_csv = csv_count > 0
    has_data = has_sheets or has_csv
    
    if has_data and has_menus:
        # User has both data sources and menu - everything is set up
        return "Great! You have uploaded both your menu and inventory data. The AI can now provide comprehensive suggestions and alerts."
    elif has_data and not has_menus:
        # User has data but no menu
        return "Please upload your menu for better AI suggestions."
    elif not has_data and has_menus:
        # User has menu but no data
        return "Please upload at least one Google sheet or CSV file so the AI can do data analysis and provide you with alerts."
    else:
        # User has neither
        return "Please upload your menu and your inventory items in the AI memories section."

def combine_user_data(users: List[Dict[str, Any]], user_sheets: Dict[str, List[Dict]], user_menus: Dict[str, List[Dict]], user_csv_files: Dict[str, List[Dict]]) -> List[Dict[str, Any]]:
    """Combine user data with their sheets, menus, and CSV files."""
    combined_data = []
    
    for user in users:
        user_id = user['user_id']
        
        # Get user's sheets (up to 3)
        sheets = user_sheets.get(user_id, [])
        
        # Get user's menus
        menus = user_menus.get(user_id, [])
        
        # Get user's CSV files (up to 3)
        csv_files = user_csv_files.get(user_id, [])
        
        # Generate personalized notes
        notes = generate_user_notes(len(sheets), len(menus), len(csv_files))
        
        combined_user = {
            'user_id': user_id,
            'name': user['name'],
            'email': user['email'],
            'subscription_status': user['subscription_status'],
            'current_period_start': user.get('current_period_start'),
            'current_period_end': user.get('current_period_end'),
            'trial_end': user.get('trial_end'),
            'user_created_at': user['user_created_at'],
            'google_sheets': sheets,
            'menu_files': menus,
            'csv_files': csv_files,
            'sheets_count': len(sheets),
            'menus_count': len(menus),
            'csv_count': len(csv_files),
            'notes': notes
        }
        
        combined_data.append(combined_user)
    
    return combined_data

def export_to_json(data: List[Dict[str, Any]], summary_stats: Dict[str, Any], filename: str = "fetch_subscribed_users_data.json"):
    """Export combined data to JSON file."""
    json_output = {
        "export_info": {
            "timestamp": datetime.now().isoformat(),
            "source_file": "extract_users_subscriptions.json",
            "total_subscribed_users": len(data)
        },
        "summary": summary_stats,
        "subscribed_users": data
    }
    
    # Write to JSON file (overwrites existing file)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(json_output, f, indent=2, ensure_ascii=False)
    
    return filename

def calculate_summary_stats(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate summary statistics for the subscribed users."""
    total_users = len(data)
    active_users = len([user for user in data if user['subscription_status'] == 'active'])
    trialing_users = len([user for user in data if user['subscription_status'] == 'trialing'])
    
    total_sheets = sum(user['sheets_count'] for user in data)
    users_with_sheets = len([user for user in data if user['sheets_count'] > 0])
    users_without_sheets = total_users - users_with_sheets
    
    total_menus = sum(user['menus_count'] for user in data)
    users_with_menus = len([user for user in data if user['menus_count'] > 0])
    users_without_menus = total_users - users_with_menus
    
    total_csv_files = sum(user['csv_count'] for user in data)
    users_with_csv = len([user for user in data if user['csv_count'] > 0])
    users_without_csv = total_users - users_with_csv
    
    # User setup status categories (considering both sheets and CSV as data sources)
    users_with_data = len([user for user in data if user['sheets_count'] > 0 or user['csv_count'] > 0])
    users_fully_setup = len([user for user in data if (user['sheets_count'] > 0 or user['csv_count'] > 0) and user['menus_count'] > 0])
    users_need_menu_only = len([user for user in data if (user['sheets_count'] > 0 or user['csv_count'] > 0) and user['menus_count'] == 0])
    users_need_data_only = len([user for user in data if user['sheets_count'] == 0 and user['csv_count'] == 0 and user['menus_count'] > 0])
    users_need_both = len([user for user in data if user['sheets_count'] == 0 and user['csv_count'] == 0 and user['menus_count'] == 0])
    
    return {
        "total_subscribed_users": total_users,
        "active_subscriptions": active_users,
        "trialing_subscriptions": trialing_users,
        "total_google_sheets": total_sheets,
        "users_with_sheets": users_with_sheets,
        "users_without_sheets": users_without_sheets,
        "total_menu_files": total_menus,
        "users_with_menus": users_with_menus,
        "users_without_menus": users_without_menus,
        "total_csv_files": total_csv_files,
        "users_with_csv": users_with_csv,
        "users_without_csv": users_without_csv,
        "users_with_data": users_with_data,
        "setup_status": {
            "fully_setup": users_fully_setup,
            "need_menu_only": users_need_menu_only,
            "need_data_only": users_need_data_only,
            "need_both": users_need_both
        }
    }

def main():
    """Main function to process subscribed users data."""
    console = Console()
    
    try:
        # Load users data from JSON file
        console.print("[bold blue]Loading users data from extract_users_subscriptions.json...[/bold blue]")
        subscribed_users = load_users_data()
        
        if not subscribed_users:
            console.print("[yellow]No subscribed or trialing users found.[/yellow]")
            return
        
        console.print(f"[green]Found {len(subscribed_users)} subscribed/trialing users[/green]")
        
        # Initialize Supabase client
        console.print("[bold blue]Connecting to Supabase...[/bold blue]")
        supabase = get_supabase_client()
        
        # Get user IDs for database queries
        user_ids = [user['user_id'] for user in subscribed_users]
        
        # Fetch sheets, menus, and CSV files data
        console.print("[bold blue]Fetching Google Sheets data...[/bold blue]")
        user_sheets = fetch_user_sheets(supabase, user_ids)
        
        console.print("[bold blue]Fetching menu data...[/bold blue]")
        user_menus = fetch_user_menus(supabase, user_ids)
        
        console.print("[bold blue]Fetching CSV files data...[/bold blue]")
        user_csv_files = fetch_user_csv_files(supabase, user_ids)
        
        # Combine all data
        console.print("[bold blue]Combining user data...[/bold blue]")
        combined_data = combine_user_data(subscribed_users, user_sheets, user_menus, user_csv_files)
        
        # Calculate summary statistics
        summary_stats = calculate_summary_stats(combined_data)
        
        # Export to JSON
        console.print("[bold blue]Exporting to JSON file...[/bold blue]")
        json_filename = export_to_json(combined_data, summary_stats)
        
        # Display summary
        console.print("\n[bold green]✓ Export completed successfully![/bold green]")
        console.print(f"[green]Output file: {json_filename}[/green]")
        console.print(f"\n[bold cyan]📊 Subscription Summary:[/bold cyan]")
        console.print(f"[cyan]Total subscribed/trialing users: {summary_stats['total_subscribed_users']}[/cyan]")
        console.print(f"[cyan]Active subscriptions: {summary_stats['active_subscriptions']}[/cyan]")
        console.print(f"[cyan]Trialing subscriptions: {summary_stats['trialing_subscriptions']}[/cyan]")
        
        console.print(f"\n[bold cyan]📈 Content Summary:[/bold cyan]")
        console.print(f"[cyan]Total Google Sheets: {summary_stats['total_google_sheets']}[/cyan]")
        console.print(f"[cyan]Total menu files: {summary_stats['total_menu_files']}[/cyan]")
        console.print(f"[cyan]Total CSV files: {summary_stats['total_csv_files']}[/cyan]")
        console.print(f"[cyan]Users with data (sheets or CSV): {summary_stats['users_with_data']}[/cyan]")
        
        console.print(f"\n[bold cyan]⚙️  Setup Status:[/bold cyan]")
        setup = summary_stats['setup_status']
        console.print(f"[green]✅ Fully setup (data + menu): {setup['fully_setup']}[/green]")
        console.print(f"[yellow]📋 Need menu only: {setup['need_menu_only']}[/yellow]")
        console.print(f"[yellow]📊 Need data only: {setup['need_data_only']}[/yellow]")
        console.print(f"[red]❌ Need both: {setup['need_both']}[/red]")
        
    except FileNotFoundError as e:
        console.print(f"[red]File Error: {e}[/red]")
        console.print("[yellow]Please run 'python extract_users_subscriptions.py' first.[/yellow]")
    except ValueError as e:
        console.print(f"[red]Configuration Error: {e}[/red]")
        console.print("[yellow]Please check your .env file and JSON file format.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    main()