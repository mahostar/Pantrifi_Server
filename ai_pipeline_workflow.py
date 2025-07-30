import os
import json
import shutil
import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from google import genai
import PyPDF2
import io
from urllib.parse import urlparse
import time
import ntplib
from datetime import datetime, timezone
import threading
from concurrent.futures import ThreadPoolExecutor
from supabase import create_client, Client
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Load environment variables
load_dotenv()

class EmailSender:
    def __init__(self):
        # Get SendGrid API key from environment
        self.api_key = os.getenv('SENDGRID_API_KEY')
        if not self.api_key:
            raise ValueError("SENDGRID_API_KEY not found in .env file")
        
        self.sg = SendGridAPIClient(api_key=self.api_key)
        print("INFO: SendGrid client initialized successfully!")
    
    def get_pantrifi_alert_template(self, expired_items=85, will_expire_soon=12, alert_date="7/12/2025"):
        """
        Returns the HTML template for Pantrifi Alert email with email-client-compatible design
        
        Args:
            expired_items (int): Number of expired items
            will_expire_soon (int): Number of items that will expire soon
            alert_date (str): Date of the alert
        """
        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Pantrifi Alert Email</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f8fffe;">
            <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: #f8fffe;">
                <tr>
                    <td align="center" style="padding: 20px;">
                        <!-- Main Container -->
                        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600" style="max-width: 600px; background-color: white; border: 2px solid #000000;">
                            <tr>
                                <!-- Left Section (Green) -->
                                <td width="280" style="background-color: #10b981; color: white; padding: 40px 32px; vertical-align: middle;">
                                    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
                                        <tr>
                                            <td style="font-size: 26px; font-weight: bold; color: white; margin-bottom: 16px; line-height: 1.2;">
                                                pantrifi
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="font-size: 22px; font-weight: bold; color: white; padding-top: 16px; padding-bottom: 12px; line-height: 1.2;">
                                                Pantrifi Alert
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="font-size: 14px; color: rgba(255,255,255,0.8); line-height: 1.4;">
                                                You received a new alert for {alert_date}
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                                
                                <!-- Right Section (White) -->
                                <td width="320" style="background-color: white; padding: 40px 32px; vertical-align: middle;">
                                    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
                                        <tr>
                                            <td style="font-size: 18px; font-weight: bold; color: #111827; margin-bottom: 16px; padding-bottom: 16px;">
                                                You have:
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="padding-bottom: 24px;">
                                                <!-- Stats Table -->
                                                <table role="presentation" cellpadding="0" cellspacing="0" border="2" width="100%" style="border-collapse: collapse; border: 2px solid #000000;">
                                                    <tr>
                                                        <td style="padding: 16px; border: 1px solid #000000; background-color: #f0fdf4; font-weight: 500; color: #374151;">
                                                            Expired items
                                                        </td>
                                                        <td style="padding: 16px; border: 1px solid #000000; background-color: #f0fdf4; font-size: 18px; font-weight: bold; color: #dc2626; text-align: right;">
                                                            {expired_items}
                                                        </td>
                                                    </tr>
                                                    <tr>
                                                        <td style="padding: 16px; border: 1px solid #000000; background-color: #f0fdf4; font-weight: 500; color: #374151;">
                                                            Will expire soon
                                                        </td>
                                                        <td style="padding: 16px; border: 1px solid #000000; background-color: #f0fdf4; font-size: 18px; font-weight: bold; color: #dc2626; text-align: right;">
                                                            {will_expire_soon}
                                                        </td>
                                                    </tr>
                                                </table>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="color: #6b7280; font-size: 15px; line-height: 1.4; padding-bottom: 24px;">
                                                For more details check the full AI analysis in Pantrifi.com
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="padding-bottom: 24px;">
                                                <a href="https://www.pantrifi.com/dashboard" style="background-color: #10b981; color: white; padding: 12px 24px; text-decoration: none; font-weight: bold; display: inline-block; border: 2px solid #10b981;">
                                                    More details
                                                </a>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="color: #9ca3af; font-size: 14px; padding-top: 16px;">
                                                — The Pantrifi AI
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        return html_template
    
    def send_email(self, to_email, subject, message=None, from_email=("alert@pantrifi.com", "Pantrifi"), 
                   use_custom_template=False, expired_items=85, will_expire_soon=12, alert_date="7/12/2025"):
        """
        Send an email using SendGrid
        
        Args:
            to_email (str): Recipient email address
            subject (str): Email subject
            message (str): Email message content (ignored if use_custom_template=True)
            from_email (str): Sender email address (must be verified in SendGrid)
            use_custom_template (bool): Whether to use the custom Pantrifi Alert template
            expired_items (int): Number of expired items (for template)
            will_expire_soon (int): Number of items that will expire soon (for template)
            alert_date (str): Date of the alert (for template)
        """
        try:
            # Choose content based on template preference
            if use_custom_template:
                html_content = self.get_pantrifi_alert_template(
                    expired_items=expired_items,
                    will_expire_soon=will_expire_soon,
                    alert_date=alert_date
                )
                plain_text_content = f"Pantrifi Alert - {alert_date}. You have {expired_items} expired items and {will_expire_soon} items that will expire soon. Visit pantrifi.com for details."
            else:
                html_content = f"<p>{message}</p>" if message else "<p>No message content</p>"
                plain_text_content = message if message else "No message content"
            
            # Create the email
            mail = Mail(
                from_email=from_email,
                to_emails=to_email,
                subject=subject,
                html_content=html_content,
                plain_text_content=plain_text_content
            )
            
            # Send the email
            response = self.sg.send(mail)
            
            if response.status_code == 202:
                print(f"SUCCESS: Email sent to {to_email}")
                print(f"Status Code: {response.status_code}")
                return True
            else:
                print(f"WARNING: Unexpected status code: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"ERROR: Failed to send email: {e}")
            return False

class GeminiAPIManager:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Load API keys from environment
        self.api_keys = self._load_api_keys()
        self.max_retries_per_key = 3
        self.retry_delay = 2  # seconds
        
        if not self.api_keys:
            raise ValueError("ERROR: No GEMINI_API_KEY found in .env file")
        
        print(f"INFO: Loaded {len(self.api_keys)} API key(s)")
        
    def _load_api_keys(self):
        """Load API keys from environment variables."""
        api_keys = []
        
        # Try to load multiple API keys (GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc.)
        i = 1
        while True:
            key_name = f"GEMINI_API_KEY_{i}" if i > 1 else "GEMINI_API_KEY"
            api_key = os.getenv(key_name)
            if api_key:
                api_keys.append(api_key)
                i += 1
            else:
                break
        
        return api_keys
    
    def _try_single_key(self, key_index, model, contents, **kwargs):
        """Try a single API key with its own retry attempts."""
        api_key = self.api_keys[key_index]
        client = genai.Client(api_key=api_key)
        
        for attempt in range(1, self.max_retries_per_key + 1):
            try:
                print(f"INFO: Using API key #{key_index + 1} (Attempt {attempt}/{self.max_retries_per_key})")
                
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    **kwargs
                )
                
                print(f"SUCCESS: Request completed with API key #{key_index + 1}")
                return response
                
            except Exception as error:
                error_message = str(error)
                print(f"WARNING: API Error (Attempt {attempt}/{self.max_retries_per_key}): {error_message}")
                
                # If this is the last attempt for this key, don't wait
                if attempt < self.max_retries_per_key:
                    # Check if it's a rate limit (429) - if so, wait before retry
                    if "429" in error_message or "RESOURCE_EXHAUSTED" in error_message:
                        wait_time = self.retry_delay * attempt
                        print(f"INFO: Rate limit detected - waiting {wait_time} seconds before retry")
                        time.sleep(wait_time)
                    else:
                        # For other errors, just a short delay
                        time.sleep(1)
        
        print(f"ERROR: API key #{key_index + 1} failed after {self.max_retries_per_key} attempts")
        return None
    
    def generate_content(self, model="gemini-2.5-flash", contents="", **kwargs):
        """Generate content by trying each API key sequentially."""
        
        # Try each API key one by one
        for key_index in range(len(self.api_keys)):
            print(f"\nINFO: Trying API key #{key_index + 1}")
            
            result = self._try_single_key(key_index, model, contents, **kwargs)
            
            if result is not None:
                return result
            
            print(f"INFO: Moving to next API key...")
        
        # If we get here, all keys failed
        raise Exception(f"ERROR: All {len(self.api_keys)} API keys failed after {self.max_retries_per_key} attempts each")

class AIPipelineWorkflow:
    def __init__(self):
        # Initialize Gemini API Manager (replaces single API key)
        try:
            self.gemini_manager = GeminiAPIManager()
            print("INFO: Gemini API Manager initialized successfully!")
        except ValueError as e:
            raise ValueError(f"Gemini API initialization failed: {e}")
        
        # Initialize Email Sender
        try:
            self.email_sender = EmailSender()
            print("INFO: Email sender initialized successfully!")
        except ValueError as e:
            print(f"WARNING: Email sender initialization failed: {e}")
            print("WARNING: Email notifications will be disabled")
            self.email_sender = None
        
        # Initialize Supabase client
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        self.workspace_path = Path(os.getcwd())
        self.cleanup_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="cleanup")
        
        print("INFO: AI Pipeline Workflow initialized successfully!")
        print("INFO: Supabase connection established!")

    def get_ntp_time(self):
        """Get current time from NTP server"""
        try:
            # Connect to NTP server
            ntp_client = ntplib.NTPClient()
            response = ntp_client.request('pool.ntp.org')
            
            # Convert NTP timestamp to datetime
            ntp_time = datetime.fromtimestamp(response.tx_time, tz=timezone.utc)
            
            return ntp_time
        except Exception as e:
            print(f"WARNING: Error getting NTP time: {e}")
            print("INFO: Falling back to system time")
            return datetime.now(timezone.utc)
    
    def load_filtered_users(self, file_path="filtered_users_with_sheets.json"):
        """Load users from the filtered JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('users_with_sheets_or_csv', [])
        except FileNotFoundError:
            print(f"ERROR: {file_path} not found")
            return []
        except json.JSONDecodeError:
            print(f"ERROR: Invalid JSON in {file_path}")
            return []
    
    def create_user_folder(self, user_name):
        """Create or recreate user folder"""
        # Clean user name for folder creation
        clean_name = "".join(c for c in user_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        clean_name = clean_name.replace(' ', '_')
        
        folder_path = self.workspace_path / clean_name
        
        # Remove existing folder if it exists
        if folder_path.exists():
            shutil.rmtree(folder_path)
            print(f"INFO: Removed existing folder: {clean_name}")
        
        # Create new folder
        folder_path.mkdir(exist_ok=True)
        print(f"INFO: Created folder: {clean_name}")
        
        return folder_path
    
    def download_file(self, url, file_path):
        """Download file from URL"""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"SUCCESS: Downloaded: {file_path.name}")
            return True
        except Exception as e:
            print(f"ERROR: Failed to download {url}: {e}")
            return False
    
    def download_google_sheet_as_csv(self, sheet_url, file_path):
        """Convert Google Sheets URL to CSV download URL and download"""
        try:
            # Extract sheet ID from URL
            if '/d/' in sheet_url:
                sheet_id = sheet_url.split('/d/')[1].split('/')[0]
                csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
                
                return self.download_file(csv_url, file_path)
            else:
                print(f"ERROR: Invalid Google Sheets URL format: {sheet_url}")
                return False
        except Exception as e:
            print(f"ERROR: Failed to process Google Sheets URL {sheet_url}: {e}")
            return False
    
    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF file"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        except Exception as e:
            print(f"ERROR: Failed to extract text from PDF {pdf_path}: {e}")
            return ""
    
    def extract_text_from_csv(self, csv_path):
        """Extract text from CSV file"""
        try:
            df = pd.read_csv(csv_path)
            return df.to_string(index=False)
        except Exception as e:
            print(f"ERROR: Failed to extract text from CSV {csv_path}: {e}")
            return ""
    
    def process_user_data(self, user, folder_path):
        """Download and process all user data"""
        user_data = {
            "user_id": user.get('user_id', ''),  # Added user_id
            "name": user.get('name', ''),
            "email": user.get('email', ''),
            "google_sheets_text": [],
            "csv_files_text": [],
            "menu_files_text": []
        }
        
        # Process Google Sheets
        for i, sheet_url in enumerate(user.get('google_sheets_urls', [])):
            csv_file_path = folder_path / f"google_sheet_{i+1}.csv"
            if self.download_google_sheet_as_csv(sheet_url, csv_file_path):
                text = self.extract_text_from_csv(csv_file_path)
                if text:
                    user_data["google_sheets_text"].append({
                        "file_name": f"google_sheet_{i+1}.csv",
                        "content": text
                    })
        
        # Process CSV files
        for i, csv_file in enumerate(user.get('csv_file_urls', [])):
            csv_file_path = folder_path / f"csv_file_{i+1}.csv"
            if self.download_file(csv_file['file_url'], csv_file_path):
                text = self.extract_text_from_csv(csv_file_path)
                if text:
                    user_data["csv_files_text"].append({
                        "file_name": csv_file.get('file_name', f"csv_file_{i+1}.csv"),
                        "content": text
                    })
        
        # Process Menu files (PDFs)
        for i, menu_file in enumerate(user.get('menu_file_urls', [])):
            menu_file_path = folder_path / f"menu_{i+1}.pdf"
            if self.download_file(menu_file['file_url'], menu_file_path):
                text = self.extract_text_from_pdf(menu_file_path)
                if text:
                    user_data["menu_files_text"].append({
                        "file_name": menu_file.get('file_name', f"menu_{i+1}.pdf"),
                        "content": text
                    })
        
        # Save user data as JSON
        json_file_path = folder_path / "user_data.json"
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, indent=2, ensure_ascii=False)
        
        print(f"INFO: Saved user data to: {json_file_path}")
        return user_data
    
    def generate_ai_report(self, user_data):
        """Generate AI report using Gemini with JSON correction and API key rotation"""
        try:
            # Get current time for accurate analysis
            current_time = self.get_ntp_time()
            current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S UTC")
            local_time_str = current_time.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
            
            # Prepare data for AI analysis
            inventory_data = ""
            menu_data = ""
            
            # Combine all inventory data (Google Sheets + CSV)
            all_inventory = user_data["google_sheets_text"] + user_data["csv_files_text"]
            for item in all_inventory:
                inventory_data += f"\n--- {item['file_name']} ---\n{item['content']}\n"
            
            # Combine all menu data
            for item in user_data["menu_files_text"]:
                menu_data += f"\n--- {item['file_name']} ---\n{item['content']}\n"
            
            # Check if menu data is available
            has_menu = bool(menu_data.strip())
            
            # Create AI prompt with current time and JSON output format
            prompt = f"""
You are a restaurant/cafe management AI assistant. 

CURRENT TIME INFORMATION:
- Current UTC Time: {current_time_str}
- Local Time: {local_time_str}

IMPORTANT: Use this current time information to accurately determine which items are expired or expiring soon. When analyzing expiration dates, compare them against the current time provided above.

Analyze the following data for {user_data['name']} (ID: {user_data.get('user_id', 'N/A')}, Email: {user_data['email']}):

INVENTORY DATA:
{inventory_data}

MENU DATA:
{menu_data}

You MUST respond with VALID JSON format only. Do NOT add any additional text, explanations, or markdown formatting. Return only the raw JSON object with the following exact structure:

{{
  "current_date": "{current_time_str}",
  "expired_items": [
    {{
      "item_name": "string",
      "expiration_date": "MM/DD/YYYY",
      "days_overdue": number,
      "alert_level": "⚫"
    }}
  ],
  "items_expiring_soon": [
    {{
      "item_name": "string", 
      "expiration_date": "MM/DD/YYYY",
      "days_until_expiry": number,
      "alert_level": "🔴 Emergency" or "🟠 Critical" or "🟢 Informative"
    }}
  ],
  "ai_suggestions": [
    "suggestion 1",
    "suggestion 2",
    "suggestion 3"
  ],
  "potential_money_saved": "estimated amount in $ for expiring soon items",
  "summary_stats": {{
    "items_expiring_soon_count": number,
    "expired_items_count": number,
    "estimated_money_saved": "amount in $"
  }}
}}
- Always put "$" in the "estimated_money_saved" amount 
Alert Level Guidelines:
- 🔴 Emergency: 0-1 days until expiry
- 🟠 Critical: 2-4 days until expiry  
- 🟢 Informative: 5-7 days until expiry
- ⚫: All expired items

{"Include AI suggestions based on menu data if available, otherwise provide general food waste prevention suggestions." if has_menu else "DON'T provide any suggestions since no menu data is available and remind the user to upload his menu data."}

Return ONLY the JSON object, no other text or formatting.
"""
            
            print(f"INFO: Using current time: {current_time_str}")
            print("INFO: Generating AI report...")
            
            # Use the new API manager instead of direct client call
            response = self.gemini_manager.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            # Parse and validate JSON response with correction
            try:
                # Clean the response by removing markdown code blocks if present
                response_text = response.text.strip()
                if response_text.startswith('```json'):
                    response_text = response_text[7:]  # Remove ```json
                    if response_text.endswith('```'):
                        response_text = response_text[:-3]  # Remove closing ```
                elif response_text.startswith('```'):
                    response_text = response_text[3:]
                    if response_text.endswith('```'):
                        response_text = response_text[:-3]
                
                response_text = response_text.strip()
                
                # First try normal JSON parsing
                try:
                    report_json = json.loads(response_text)
                    print("SUCCESS: AI returned valid JSON")
                    return report_json
                except json.JSONDecodeError as e:
                    print(f"WARNING: AI returned invalid JSON, attempting repair: {e}")
                    
                    # Try to repair the JSON (if json-repair is available)
                    try:
                        from json_repair import repair_json
                        repaired_json_str = repair_json(response_text)
                        if repaired_json_str:  # repair_json returns empty string if super broken
                            report_json = json.loads(repaired_json_str)
                            print("INFO: Successfully repaired malformed JSON")
                            return report_json
                        else:
                            print("ERROR: JSON was too broken to repair")
                            raise json.JSONDecodeError("JSON too broken to repair", response_text, 0)
                    except ImportError:
                        print("WARNING: json-repair not available, using fallback")
                        raise e  # Re-raise original error
                    except Exception as repair_error:
                        print(f"ERROR: JSON repair failed: {repair_error}")
                        raise e  # Re-raise original error
                        
            except json.JSONDecodeError as e:
                print(f"WARNING: Final JSON parsing failed: {e}")
                print(f"Raw response: {response.text[:200]}...")
                # Return a fallback JSON structure
                return {
                    "current_date": current_time_str,
                    "expired_items": [],
                    "items_expiring_soon": [],
                    "ai_suggestions": ["Unable to process inventory due to JSON parsing error"],
                    "potential_money_saved": "$0",
                    "summary_stats": {
                        "items_expiring_soon_count": 0,
                        "expired_items_count": 0,
                        "estimated_money_saved": "$0"
                    },
                    "error": f"JSON parsing failed: {str(e)}"
                }
            
        except Exception as e:
            print(f"ERROR: Error generating AI report: {e}")
            # Return error in JSON format
            return {
                "current_date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "expired_items": [],
                "items_expiring_soon": [],
                "ai_suggestions": [],
                "potential_money_saved": "$0",
                "summary_stats": {
                    "items_expiring_soon_count": 0,
                    "expired_items_count": 0,
                    "estimated_money_saved": "$0"
                },
                "error": f"Error generating AI report: {str(e)}"
            }

    def send_alert_email(self, user_email, user_name, ai_analysis_json):
        """Send alert email to user based on AI analysis"""
        if not self.email_sender:
            print("WARNING: Email sender not available, skipping email notification")
            return False
        
        try:
            # Extract data from AI analysis
            summary_stats = ai_analysis_json.get('summary_stats', {})
            expired_count = summary_stats.get('expired_items_count', 0)
            expiring_soon_count = summary_stats.get('items_expiring_soon_count', 0)
            
            # Get current date for email
            current_time = self.get_ntp_time()
            alert_date = current_time.strftime("%m/%d/%Y")
            
            # Prepare email details
            email_subject = f"Pantrifi Alert - {alert_date}"
            
            print(f"INFO: Sending alert email to {user_email} ({user_name})")
            print(f"INFO: Email details - Expired: {expired_count}, Expiring Soon: {expiring_soon_count}")
            
            # Send email with custom template
            success = self.email_sender.send_email(
                to_email=user_email,
                subject=email_subject,
                from_email=("alert@pantrifi.com", "Pantrifi"),
                use_custom_template=True,
                expired_items=expired_count,
                will_expire_soon=expiring_soon_count,
                alert_date=alert_date
            )
            
            if success:
                print(f"SUCCESS: Alert email sent to {user_email}")
                return True
            else:
                print(f"ERROR: Failed to send alert email to {user_email}")
                return False
                
        except Exception as e:
            print(f"ERROR: Error sending alert email to {user_email}: {e}")
            return False

    def cleanup_user_folder(self, folder_path):
        """Delete user folder after processing with retry mechanism"""
        def _cleanup_with_retry(path, max_retries=3, delay=1):
            for attempt in range(max_retries):
                try:
                    if path.exists():
                        # Force close any open file handles
                        import gc
                        gc.collect()
                        
                        # Wait a bit for any file handles to be released
                        time.sleep(0.5)
                        
                        shutil.rmtree(path, ignore_errors=False)
                        print(f"INFO: Successfully cleaned up folder: {path.name}")
                        return True
                except PermissionError as e:
                    if attempt < max_retries - 1:
                        print(f"WARNING: Cleanup attempt {attempt + 1} failed, retrying in {delay}s...")
                        time.sleep(delay)
                        delay *= 2  # Exponential backoff
                    else:
                        print(f"ERROR: Failed to cleanup folder {path} after {max_retries} attempts: {e}")
                except Exception as e:
                    print(f"ERROR: Unexpected error during cleanup of {path}: {e}")
                    break
            return False
        
        return _cleanup_with_retry(folder_path)
    
    def cleanup_user_folder_threaded(self, folder_path):
        """Submit cleanup task to thread pool for non-blocking execution"""
        def cleanup_task():
            try:
                # Small delay to ensure all file operations are complete
                time.sleep(1)
                self.cleanup_user_folder(folder_path)
            except Exception as e:
                print(f"ERROR: Threaded cleanup failed for {folder_path}: {e}")
        
        # Submit cleanup to thread pool
        future = self.cleanup_executor.submit(cleanup_task)
        print(f"INFO: Cleanup scheduled for: {folder_path.name}")
        return future
    
    def save_alert_to_supabase(self, user_id, ai_analysis_json):
        """Save AI analysis alert to Supabase alerts table"""
        try:
            # Convert JSON to string for storage
            ai_analysis_text = json.dumps(ai_analysis_json, indent=2, ensure_ascii=False)
            
            # Prepare alert data
            alert_data = {
                "user_id": user_id,
                "ai_analysis": ai_analysis_text,
                "alert_date": datetime.now(timezone.utc).isoformat()
            }
            
            # Insert into Supabase
            result = self.supabase.table("alerts").insert(alert_data).execute()
            
            if result.data:
                print(f"SUCCESS: Alert saved to database for user {user_id}")
                return True
            else:
                print(f"ERROR: Failed to save alert to database for user {user_id}")
                return False
                
        except Exception as e:
            print(f"ERROR: Error saving alert to Supabase for user {user_id}: {e}")
            return False
    
    def format_alert_summary(self, ai_analysis_json, user_name):
        """Format a readable summary of the alert for terminal display"""
        try:
            summary = f"\n--- ALERT SUMMARY FOR {user_name.upper()} ---\n"
            summary += "=" * 60 + "\n"
            
            # Summary stats
            stats = ai_analysis_json.get('summary_stats', {})
            summary += f"QUICK STATS:\n"
            summary += f"   - Expired Items: {stats.get('expired_items_count', 0)}\n"
            summary += f"   - Items Expiring Soon: {stats.get('items_expiring_soon_count', 0)}\n"
            summary += f"   - Potential Money Saved: {stats.get('estimated_money_saved', '$0')}\n\n"
            
            # Expired items
            expired_items = ai_analysis_json.get('expired_items', [])
            if expired_items:
                summary += "EXPIRED ITEMS:\n"
                for item in expired_items:
                    summary += f"   - {item.get('item_name', 'Unknown')} - Expired {item.get('days_overdue', 0)} days ago\n"
            else:
                summary += "No expired items found\n"
            
            summary += "\n"
            
            # Items expiring soon
            expiring_items = ai_analysis_json.get('items_expiring_soon', [])
            if expiring_items:
                summary += "ITEMS EXPIRING SOON:\n"
                for item in expiring_items:
                    alert_level = item.get('alert_level', '')
                    if "Emergency" in alert_level:
                        alert_tag = "[EMERGENCY]"
                    elif "Critical" in alert_level:
                        alert_tag = "[CRITICAL]"
                    else:
                        alert_tag = "[INFO]"
                    summary += f"   {alert_tag} {item.get('item_name', 'Unknown')} - {item.get('days_until_expiry', 0)} days left\n"
            else:
                summary += "No items expiring soon\n"
            
            summary += "\n" + "=" * 60
            
            return summary
            
        except Exception as e:
            return f"ERROR: Error formatting alert summary: {e}"
    
    def run_pipeline(self):
        """Run the complete AI pipeline workflow"""
        print("INFO: Starting AI Pipeline Workflow...")
        print("=" * 60)
        
        # Load filtered users
        users = self.load_filtered_users()
        
        if not users:
            print("ERROR: No users found to process")
            return
        
        print(f"INFO: Found {len(users)} users to process")
        cleanup_futures = []
        
        for i, user in enumerate(users, 1):
            user_name = user.get('name', f'User_{i}')
            user_email = user.get('email', 'No email')
            user_id = user.get('user_id', 'No ID')
            
            print(f"\n{'=' * 60}")
            print(f"INFO: Processing User {i}/{len(users)}: {user_name} (ID: {user_id}, Email: {user_email})")
            print(f"{'=' * 60}")
            
            # Create user folder
            folder_path = self.create_user_folder(user_name)
            
            try:
                # Process user data
                print("\nINFO: Downloading and processing user data...")
                user_data = self.process_user_data(user, folder_path)
                
                # Generate AI report
                print("\nINFO: Generating AI analysis report...")
                ai_analysis = self.generate_ai_report(user_data)
                
                # Save alert to Supabase database
                print("\nINFO: Saving alert to database...")
                database_save_success = self.save_alert_to_supabase(user_id, ai_analysis)
                
                # Send email notification
                if user_email and user_email != 'No email':
                    print("\nINFO: Sending email notification...")
                    email_success = self.send_alert_email(user_email, user_name, ai_analysis)
                    if email_success:
                        print(f"SUCCESS: Email notification sent to {user_email}")
                    else:
                        print(f"WARNING: Failed to send email notification to {user_email}")
                else:
                    print("WARNING: No valid email address found, skipping email notification")
                
                # Display formatted summary in terminal
                if database_save_success:
                    summary = self.format_alert_summary(ai_analysis, user_name)
                    print(summary)
                else:
                    print(f"WARNING: Database save failed, showing analysis anyway:")
                    print(f"\nAI ANALYSIS FOR {user_name.upper()} (ID: {user_id}):")
                    print("=" * 60)
                    print(json.dumps(ai_analysis, indent=2, ensure_ascii=False))
                    print("=" * 60)
                
                # Wait a moment before processing next user
                time.sleep(1)
                
            except Exception as e:
                print(f"ERROR: Error processing user {user_name}: {e}")
            
            finally:
                # Schedule cleanup in separate thread (non-blocking)
                print("\nINFO: Scheduling cleanup...")
                cleanup_future = self.cleanup_user_folder_threaded(folder_path)
                cleanup_futures.append(cleanup_future)
        
        # Wait for all cleanup tasks to complete before finishing
        print("\nINFO: Waiting for all cleanup tasks to complete...")
        for i, future in enumerate(cleanup_futures, 1):
            try:
                future.result(timeout=30)  # 30 second timeout per cleanup
                print(f"INFO: Cleanup {i}/{len(cleanup_futures)} completed")
            except Exception as e:
                print(f"WARNING: Cleanup {i}/{len(cleanup_futures)} had issues: {e}")
        
        # Shutdown the cleanup executor
        self.cleanup_executor.shutdown(wait=True)
        print("\nSUCCESS: AI Pipeline Workflow completed!")
        print("INFO: All alerts have been saved to the database and email notifications sent.")

    def __del__(self):
        """Ensure cleanup executor is properly shutdown"""
        if hasattr(self, 'cleanup_executor'):
            self.cleanup_executor.shutdown(wait=False)

def main():
    """Main function to run the AI pipeline"""
    try:
        pipeline = AIPipelineWorkflow()
        pipeline.run_pipeline()
    except Exception as e:
        print(f"ERROR: Failed to initialize pipeline: {e}")
        print("Please make sure your .env file contains:")
        print("- GEMINI_API_KEY=your_api_key_here")
        print("- SUPABASE_URL=your_supabase_url")
        print("- SUPABASE_ANON_KEY=your_supabase_anon_key")
        print("- SENDGRID_API_KEY=your_sendgrid_api_key_here (optional, for email notifications)")

if __name__ == "__main__":
    main()