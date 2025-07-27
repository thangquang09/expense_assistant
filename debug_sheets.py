#!/usr/bin/env python3
"""
Debug Google Sheets Issues
Kiểm tra chi tiết các vấn đề với Google Sheets
"""

import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from dotenv import load_dotenv

# Load environment
load_dotenv()

def main():
    console = Console()
    
    console.print(Panel(
        "🔍 GOOGLE SHEETS DEBUG TOOL",
        subtitle="Kiểm tra chi tiết vấn đề Google Sheets",
        border_style="yellow"
    ))
    
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        # Get credentials path
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not creds_path or not os.path.exists(creds_path):
            console.print("[red]❌ Không tìm thấy credentials[/red]")
            return
        
        console.print(f"[green]✅ Credentials: {creds_path}[/green]")
        
        # Load and inspect credentials
        with open(creds_path, 'r') as f:
            import json
            cred_data = json.load(f)
            
        console.print(f"[cyan]📧 Service Account Email: {cred_data.get('client_email', 'N/A')}[/cyan]")
        console.print(f"[cyan]🏗️ Project ID: {cred_data.get('project_id', 'N/A')}[/cyan]")
        
        # Setup credentials with different approach
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credentials = Credentials.from_service_account_file(creds_path, scopes=scope)
        gc = gspread.authorize(credentials)
        
        console.print("[green]✅ Authentication successful[/green]")
        
        # Try different approaches
        console.print("\n[yellow]🧪 Testing different approaches...[/yellow]")
        
        # Approach 1: Try to list existing spreadsheets first
        try:
            console.print("1️⃣ Trying to list existing spreadsheets...")
            spreadsheets = gc.list_spreadsheet_files()
            console.print(f"[green]✅ Found {len(spreadsheets)} existing spreadsheets[/green]")
            
            # Show first few
            if spreadsheets:
                table = Table(show_header=True, header_style="bold cyan")
                table.add_column("Name", style="green")
                table.add_column("ID", style="yellow")
                
                for sheet in spreadsheets[:3]:  # Show first 3
                    table.add_row(sheet['name'], sheet['id'][:20] + "...")
                
                console.print(table)
                
                # Try to open an existing one
                existing_sheet = spreadsheets[0]
                test_sheet = gc.open_by_key(existing_sheet['id'])
                console.print(f"[green]✅ Successfully opened existing sheet: {existing_sheet['name']}[/green]")
                
        except Exception as e:
            console.print(f"[red]❌ Error listing spreadsheets: {e}[/red]")
        
        # Approach 2: Try to create with minimal permissions
        try:
            console.print("\n2️⃣ Trying to create minimal test spreadsheet...")
            test_name = "Expense Tracker Test Minimal"
            
            # Delete if exists first
            try:
                existing = gc.open(test_name)
                gc.del_spreadsheet_by_key(existing.id)
                console.print("🗑️ Deleted existing test spreadsheet")
            except:
                pass
            
            # Create new minimal sheet
            new_sheet = gc.create(test_name)
            console.print(f"[green]✅ Created test spreadsheet: {new_sheet.title}[/green]")
            console.print(f"[cyan]🔗 URL: https://docs.google.com/spreadsheets/d/{new_sheet.id}/edit[/cyan]")
            
            # Clean up
            import time
            time.sleep(1)
            gc.del_spreadsheet_by_key(new_sheet.id)
            console.print("[green]✅ Test successful - cleaned up test sheet[/green]")
            
            # If we get here, the problem was temporary or resolved
            console.print("\n[green]🎉 Google Sheets is working! The quota issue seems resolved.[/green]")
            console.print("[yellow]💡 Try running the main app again: ea \"test working 25k\"[/yellow]")
            
        except Exception as e:
            console.print(f"\n[red]❌ Still getting error: {e}[/red]")
            
            # Analyze the error
            analyze_error(console, str(e))
    
    except Exception as e:
        console.print(f"[red]❌ Setup error: {e}[/red]")


def analyze_error(console, error_str):
    """Phân tích chi tiết lỗi"""
    
    console.print("\n[yellow]🔍 Error Analysis:[/yellow]")
    
    if "quota" in error_str.lower() and "exceeded" in error_str.lower():
        if "storage" in error_str.lower():
            console.print("📊 This appears to be a Google Drive STORAGE quota issue")
            console.print("💡 Possible causes:")
            console.print("   • Service account might have different storage limits")
            console.print("   • Organization/project-level storage limits")
            console.print("   • Temporary Google API glitch")
            
        else:
            console.print("📊 This appears to be an API USAGE quota issue")
            console.print("💡 Possible causes:")
            console.print("   • Too many API calls in short time")
            console.print("   • Daily/hourly API quota exceeded")
            console.print("   • Project-level API limits")
    
    elif "403" in error_str:
        console.print("🔐 This is a permissions/access issue")
        console.print("💡 Possible causes:")
        console.print("   • Service account doesn't have Drive access")
        console.print("   • APIs not enabled properly")
        console.print("   • Project permissions issue")
    
    elif "400" in error_str:
        console.print("📝 This is a bad request issue")
        console.print("💡 Usually a formatting or parameter problem")
    
    # Suggestions
    console.print("\n[cyan]🛠️ Suggested solutions:[/cyan]")
    console.print("1. Wait 10-15 minutes and try again (temporary quota)")
    console.print("2. Check Google Cloud Console quotas")
    console.print("3. Try creating the service account in a fresh project")
    console.print("4. Use personal Google account instead of organization")


if __name__ == "__main__":
    main() 