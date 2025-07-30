import os
from dotenv import load_dotenv
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
    
    def send_email(self, to_email, subject, message=None, from_email="your-email@example.com", 
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

def main():
    """Main function to demonstrate email sending"""
    try:
        # Initialize email sender
        email_sender = EmailSender()
        
        # Email configuration variables - MODIFY THESE
        recipient_email = "medwassimmbarek@gmail.com"  # Change this to the email you want to send to
        email_subject = "Pantrifi Alert - 7/12/2025"
        sender_email = ("alert@pantrifi.com", "Pantrifi")  
        
        # Alert data - MODIFY THESE VALUES AS NEEDED
        expired_count = 85  # Number of expired items
        expiring_soon_count = 12  # Number of items expiring soon
        alert_date = "7/12/2025"  # Alert date
        
        # Send the email with custom template
        print(f"INFO: Sending Pantrifi Alert email to {recipient_email}...")
        success = email_sender.send_email(
            to_email=recipient_email,
            subject=email_subject,
            from_email=sender_email,
            use_custom_template=True,  # This enables the custom Pantrifi Alert template
            expired_items=expired_count,
            will_expire_soon=expiring_soon_count,
            alert_date=alert_date
        )
        
        if success:
            print("INFO: Pantrifi Alert email sent successfully!")
        else:
            print("ERROR: Failed to send email")
            
    except ValueError as e:
        print(f"ERROR: Configuration Error: {e}")
        print("\nINFO: Please add your SendGrid API key to the .env file:")
        print("SENDGRID_API_KEY=SG.your_api_key_here")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()