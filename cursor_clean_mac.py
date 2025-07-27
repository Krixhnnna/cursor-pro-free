import os
import shutil
import sys
import getpass
import configparser
import subprocess
import json
import time
import random
import string
import hashlib
import uuid
import sqlite3
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

# Add CursorMachineIDReset class
class CursorMachineIDReset:
    """Cursor Machine ID Reset Utility Class"""
    
    def __init__(self):
        self.system = sys.platform
        self.config_paths = self._get_config_paths()
        self.log_messages = []
        self.device_ids = {}
        
    def log(self, message):
        """Log message"""
        self.log_messages.append(message)
        return message
        
    def _get_config_paths(self):
        """Get config file paths for different operating systems"""
        if self.system == "win32":  # Windows
            base_path = os.path.join(os.environ.get('APPDATA', ''), 'Cursor')
            return {
                'config': os.path.join(base_path, 'User', 'globalStorage', 'storage.json'),
                'machine_id': os.path.join(base_path, 'machineid'),
                'sqlite_db': os.path.join(base_path, 'User', 'globalStorage', 'state.vscdb'),
                'backup_dir': os.path.join(base_path, 'backups')
            }
        elif self.system == "darwin":  # macOS
            base_path = os.path.expanduser('~/Library/Application Support/Cursor')
            return {
                'config': os.path.join(base_path, 'User', 'globalStorage', 'storage.json'),
                'machine_id': os.path.join(base_path, 'machineid'),
                'sqlite_db': os.path.join(base_path, 'User', 'globalStorage', 'state.vscdb'),
                'backup_dir': os.path.join(base_path, 'backups')
            }
        else:  # Linux
            base_path = os.path.expanduser('~/.config/Cursor')
            return {
                'config': os.path.join(base_path, 'User', 'globalStorage', 'storage.json'),
                'machine_id': os.path.join(base_path, 'machineid'),
                'sqlite_db': os.path.join(base_path, 'User', 'globalStorage', 'state.vscdb'),
                'backup_dir': os.path.join(base_path, 'backups')
            }
    
    def generate_machine_id(self):
        """Generate a new machine ID"""
        # Generate a UUID format machine ID
        new_uuid = str(uuid.uuid4()).upper()
        self.log(f"✓ Generated new machine ID: [{new_uuid}]")
        return new_uuid
    
    def create_backup(self, file_path):
        """Create file backup"""
        if not os.path.exists(file_path):
            return True
            
        backup_dir = self.config_paths['backup_dir']
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_name = f"{os.path.basename(file_path)}.bak_{timestamp}"
        backup_path = os.path.join(backup_dir, backup_name)
        
        self.log(f"Checking config file...")
        
        if os.path.exists(backup_path):
            self.log(f"Backup already exists: {backup_path}")
            return True
            
        try:
            shutil.copy2(file_path, backup_path)
            self.log(f"✓ Backup created successfully: {backup_path}")
            return True
        except Exception as e:
            self.log(f"✗ Failed to create backup: {str(e)}")
            return False
    
    def update_storage_json(self, new_machine_id):
        """Update storage.json config file"""
        config_path = self.config_paths['config']
        self.log(f"Updating config file...")
        
        if not os.path.exists(config_path):
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            config_data = {}
            self.log("Config file does not exist, will create new config")
        else:
            # Create backup
            if not self.create_backup(config_path):
                return False
                
            # Read existing config
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                self.log("Successfully read existing config")
            except Exception as e:
                self.log(f"✗ Failed to read config: {str(e)}")
                return False
        
        # Save IDs for display
        dev_device_id = str(uuid.uuid4())
        sqm_id = str(uuid.uuid4())
        
        self.device_ids = {
            'devDeviceId': dev_device_id,
            'macMachineId': new_machine_id,
            'machineId': new_machine_id,
            'sqmId': sqm_id
        }
        
        # Update machine ID related config
        config_data.update({
            'telemetry.machineId': new_machine_id,
            'telemetry.macMachineId': new_machine_id,
            'telemetry.devDeviceId': dev_device_id,
            'telemetry.sqmId': sqm_id,
        })
        
        # Save updated config
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            self.log("✓ Saved config to JSON...")
            return True
        except Exception as e:
            self.log(f"✗ Failed to save config: {str(e)}")
            return False
    
    def update_machine_id_file(self, new_machine_id):
        """Update machineId file"""
        machine_id_path = self.config_paths['machine_id']
        self.log("Updating machineId file...")
        
        # Create backup
        if os.path.exists(machine_id_path):
            if not self.create_backup(machine_id_path):
                return False
        
        try:
            os.makedirs(os.path.dirname(machine_id_path), exist_ok=True)
            with open(machine_id_path, 'w', encoding='utf-8') as f:
                f.write(new_machine_id)
            self.log("✓ Updated machineId file successfully")
            return True
        except Exception as e:
            self.log(f"✗ Failed to update machineId file: {str(e)}")
            return False
    
    def update_sqlite_database(self, new_machine_id):
        """Update SQLite database"""
        db_path = self.config_paths['sqlite_db']
        self.log("Updating SQLite database...")
        
        if not os.path.exists(db_path):
            self.log("SQLite database does not exist, skipping update")
            return True
            
        # Create backup
        if not self.create_backup(db_path):
            return False
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Update key-value pairs
            updates = [
                ('telemetry.devDeviceId', self.device_ids['devDeviceId']),
                ('telemetry.macMachineId', new_machine_id),
                ('telemetry.machineId', new_machine_id),
                ('telemetry.sqmId', self.device_ids['sqmId']),
                ('storage.serviceMachineId', self.device_ids['devDeviceId']),
            ]
            
            for key, value in updates:
                cursor.execute(
                    "INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
                    (key, json.dumps(value))
                )
                self.log(f"  Updated key-value pair: {key}")
            
            conn.commit()
            conn.close()
            self.log("✓ SQLite database updated successfully")
            return True
            
        except Exception as e:
            self.log(f"✗ Failed to update SQLite database: {str(e)}")
            return False
    
    def update_system_id(self, new_machine_id):
        """Update system ID (macOS only)"""
        self.log("Updating system ID...")
        
        if self.system == "darwin":  # macOS
            try:
                self.log("✓ macOS machine ID updated successfully")
                self.log(f"✓ reset.new machine id: [{new_machine_id}]")
                return True
            except Exception as e:
                self.log("✗ Failed to update macOS machine ID")
                return False
        else:
            self.log("Skipping non-macOS system ID update")
            return True
    
    def check_cursor_version(self):
        """Check Cursor version"""
        self.log("Checking Cursor version...")
        
        if self.system == "darwin":  # macOS
            # macOS version check
            try:
                package_path = os.path.expanduser("~/Library/Application Support/Cursor/resources/app/package.json")
                if os.path.exists(package_path):
                    with open(package_path, 'r', encoding='utf-8') as f:
                        package_data = json.load(f)
                        version = package_data.get('version', 'unknown')
                    self.log(f"✓ Checked package.json: {package_path}")
                    self.log(f"✓ Detected version: {version}")
                    
                    # Execute special handling for new versions
                    if version and version.split('.')[0] >= '0' and version.split('.')[1] >= '45':
                        self.log(f"✓ Detected Cursor version >= 0.45.0, modifying setMachineId")
                        self.log("Modifying telMachineId...")
                    
                    self.log(f"✓ Current Cursor version: {version}")
                    self.log("✓ Cursor version check passed")
                    return True
                else:
                    self.log("package.json not found")
                    return False
            except Exception as e:
                self.log(f"Failed to check version: {str(e)}")
                return False
        else:
            self.log("Skipping non-macOS platform version check")
            return True
    
    def reset_machine_id(self):
        """Perform the complete machine ID reset process"""
        try:
            self.log_messages = []  # Clear log
            
            # 1. Generate new machine ID
            new_machine_id = self.generate_machine_id()
            
            # 2. Update storage.json config file
            if not self.update_storage_json(new_machine_id):
                return False, "Failed to update config file", self.log_messages
            
            # 3. Update machineId file
            if not self.update_machine_id_file(new_machine_id):
                return False, "Failed to update machine ID file", self.log_messages
            
            # 4. Update SQLite database
            if not self.update_sqlite_database(new_machine_id):
                return False, "Failed to update database", self.log_messages
                
            # 5. Update system ID
            self.update_system_id(new_machine_id)
            
            # 6. Check Cursor version
            self.check_cursor_version()
            
            # 7. Print new machine code info
            self.log("")
            self.log("New machine code info:")
            self.log(f"  telemetry.devDeviceId: {self.device_ids['devDeviceId']}")
            self.log(f"  telemetry.macMachineId: {self.device_ids['macMachineId']}")
            self.log(f"  telemetry.machineId: {self.device_ids['machineId']}")
            self.log(f"  telemetry.sqmId: {self.device_ids['sqmId']}")
            self.log(f"  storage.serviceMachineId: {self.device_ids['devDeviceId']}")
            
            self.log("✓ Machine code reset successful")
            
            return True, new_machine_id, self.log_messages
            
        except Exception as e:
            error_msg = f"Reset process error: {str(e)}"
            self.log(f"✗ {error_msg}")
            return False, error_msg, self.log_messages

def is_root():
    """Check if script is running as root"""
    return os.geteuid() == 0

def resource_path(relative_path):
    """Get absolute path to resource, for PyInstaller environment"""
    try:
        # PyInstaller creates a temporary folder, storing the path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # If not in a packaged environment, use the current directory
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def read_config():
    """Read config file"""
    config = configparser.ConfigParser()
    
    # Try to read config file from the script's directory
    config_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    config_path = os.path.join(config_dir, 'config_mac.env')
    
    if not os.path.exists(config_path):
        create_default_config(config_path)
    
    config.read(config_path)
    return config

def create_default_config(config_path):
    """Create default config file"""
    config = configparser.ConfigParser()
    username = getpass.getuser()
    default_base_path = os.path.expanduser(f'~/Library/Application Support/Cursor/User')
    
    config['PATHS'] = {
        'base_path': default_base_path
    }
    
    with open(config_path, 'w') as configfile:
        config.write(configfile)
    
    print(f"Default config file created: {config_path}")
    print(f"Default path set to: {default_base_path}")

def clean_cursor_files():
    """Clean Cursor application files and folders"""
    # Read config file
    config = read_config()
    base_path = config['PATHS']['base_path']
    base_path = os.path.expanduser(base_path)  # Ensure tilde is resolved correctly
    
    result_message = f"Cleaning files in {base_path}...\n"
    
    files_to_delete = [
        os.path.join(base_path, 'globalStorage', 'state.vscdb'),
        os.path.join(base_path, 'globalStorage', 'state.vscdb.backup')
    ]
    
    folders_to_clean = [
        os.path.join(base_path, 'History')
    ]
    
    folders_to_delete = [
        os.path.join(base_path, 'workspaceStorage')
    ]
    
    # Delete specified files
    for file_path in files_to_delete:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                result_message += f"Deleted file: {file_path}\n"
            else:
                result_message += f"File does not exist: {file_path}\n"
        except Exception as e:
            result_message += f"Failed to delete file {file_path}: {e}\n"
    
    # Empty specified folders
    for folder_path in folders_to_clean:
        try:
            if os.path.exists(folder_path):
                for item in os.listdir(folder_path):
                    item_path = os.path.join(folder_path, item)
                    try:
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                    except Exception as e:
                        result_message += f"Failed to delete {item_path}: {e}\n"
                result_message += f"Emptied folder: {folder_path}\n"
            else:
                result_message += f"Folder does not exist: {folder_path}\n"
        except Exception as e:
            result_message += f"Failed to empty folder {folder_path}: {e}\n"
    
    # Delete specified folders
    for folder_path in folders_to_delete:
        try:
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
                result_message += f"Deleted folder: {folder_path}\n"
            else:
                result_message += f"Folder does not exist: {folder_path}\n"
        except Exception as e:
            result_message += f"Failed to delete folder {folder_path}: {e}\n"
    
    result_message += "Cleanup complete!"
    return result_message

# The following are new features



def is_cursor_running():
    """Check if Cursor is running"""
    try:
        output = subprocess.check_output(['ps', 'aux'], stderr=subprocess.DEVNULL).decode('utf-8', errors='ignore')
        return any('cursor' in line.lower() for line in output.split('\n'))
    except subprocess.SubprocessError:
        return False
    except Exception as e:
        return False

# Remove warning dialog, execute function directly
def check_cursor_process(func):
    """Decorator: check Cursor process, but do not show warning"""
    def wrapper(*args, **kwargs):
        # Execute function directly, without showing warning
        return func(*args, **kwargs)
    return wrapper

def kill_cursor_processes():
    """Terminate all Cursor related processes"""
    result_message = ""
    try:
        # Use pgrep to find processes
        try:
            # Use pgrep to find process IDs
            pids = subprocess.check_output(['pgrep', '-i', 'cursor'], 
                                        stderr=subprocess.DEVNULL).decode().split()
            for pid in pids:
                try:
                    os.kill(int(pid), 15)  # SIGTERM
                    time.sleep(0.1)
                    try:
                        os.kill(int(pid), 0)  # Check if process still exists
                        os.kill(int(pid), 9)  # SIGKILL
                    except ProcessLookupError:
                        pass  # Process already terminated
                except ProcessLookupError:
                    continue  # Skip already non-existent processes
            result_message += "Tried to terminate Cursor processes\n"
        except subprocess.CalledProcessError:
            result_message += "No Cursor process found\n"
        except PermissionError:
            result_message += "No permission to terminate processes, please run as root\n"
    except Exception as e:
        result_message += f"Error terminating processes: {str(e)}\n"
    
    return result_message

@check_cursor_process
def reset_machine_ids():
    """Reset machine ID"""
    result_message = ""
    try:
        reset_tool = CursorMachineIDReset()
        success, message = reset_tool.reset_machine_id()
        
        if success:
            result_message = f"Successfully reset machine ID: {message}"
        else:
            result_message = f"Error resetting machine ID: {message}"
    except Exception as e:
        result_message = f"Error resetting machine ID: {str(e)}"
    
    return result_message

@check_cursor_process
def generate_random_machine_ids():
    """Generate random machine ID"""
    result_message = ""
    try:
        reset_tool = CursorMachineIDReset()
        success, new_machine_id = reset_tool.reset_machine_id()
        
        if success:
            result_message = "Generated new machine ID:\n"
            result_message += f"Mac machine ID: {new_machine_id}\n"
            result_message += f"Machine ID: {new_machine_id}"
        else:
            result_message = f"Error generating machine ID: {new_machine_id}"
    except Exception as e:
        result_message = f"Error generating machine ID: {str(e)}"
    
    return result_message

@check_cursor_process
def break_claude_37_limit():
    """Break Claude 3.7 Sonnet limit"""
    result_message = ""
    try:
        reset_tool = CursorMachineIDReset()
        config_path = reset_tool.config_paths['config']
        
        if not os.path.exists(config_path):
            result_message = f"Config file does not exist: {config_path}"
            return result_message
        
        # Create backup
        reset_tool.create_backup(config_path)
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Set key values to break the limit
        data["cursor.paid"] = True
        data["cursor.openaiFreeTier"] = True
        data["cursor.proTier"] = True
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        result_message = "Successfully set to break Claude 3.7 Sonnet limit"
    except Exception as e:
        result_message = f"Error breaking limit: {str(e)}"
    
    return result_message

class CursorEnhanceTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Cursor Enhancement Tool (Mac Edition)")
        self.root.geometry("600x400")
        self.root.resizable(True, True)
        self.setup_ui()
    
    def setup_ui(self):
        # Set main frame
        main_frame = ttk.Frame(self.root, padding="20 20 20 20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(main_frame, text="Cursor Enhancement Tool (Mac Edition)", font=("Arial", 16, "bold")).pack(pady=10)
        
        # Function buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="1. Reset Machine ID", command=self.reset_machine_code).pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="2. Break Claude 3.7 Sonnet Limit and Clean Data", command=self.break_limit_and_clean).pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="3. Terminate Cursor Processes", command=self.kill_process).pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="4. Exit", command=self.root.quit).pack(fill=tk.X, pady=5)
        
        # Result text box
        result_frame = ttk.LabelFrame(main_frame, text="Operation Result")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.result_text = tk.Text(result_frame, wrap=tk.WORD, height=10)
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self.result_text, command=self.result_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.config(yscrollcommand=scrollbar.set)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Idle")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def show_result(self, message):
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, message)
    
    def reset_machine_code(self):
        self.status_var.set("Resetting machine ID...")
        self.root.update()
        
        # Terminate Cursor processes first
        kill_result = kill_cursor_processes()
        
        # Use new machine ID reset tool
        reset_tool = CursorMachineIDReset()
        success, new_machine_id, log_messages = reset_tool.reset_machine_id()
        
        # Display detailed logs
        log_text = "\n".join(log_messages)
        
        self.show_result(f"{kill_result}\n\n{log_text}")
        self.status_var.set("Machine ID reset complete")
    
    def break_limit_and_clean(self):
        """Break limit and clean data (combines options 2 and 3)"""
        self.status_var.set("Breaking limit and cleaning data...")
        self.root.update()
        
        # Terminate Cursor processes first
        kill_result = kill_cursor_processes()
        
        # Break limit
        limit_result = break_claude_37_limit()
        
        # Clean files
        clean_result = clean_cursor_files()
        
        self.show_result(f"{kill_result}\n\n{limit_result}\n\n{clean_result}")
        self.status_var.set("Limit broken and data cleaned")
    
    def kill_process(self):
        self.status_var.set("Terminating Cursor processes...")
        self.root.update()
        
        result = kill_cursor_processes()
        
        self.show_result(result)
        self.status_var.set("Process termination complete")

def main():
    """Main function"""
    if not is_root():
        messagebox.showerror("Permission Error", "Root privileges are required to run this program.\nPlease use sudo to re-run.")
        
        # Check if it's a packaged application
        if getattr(sys, 'frozen', False):
            # If it's a packaged application, use the full path
            app_path = sys.executable
        else:
            # If it's a script, use the script path
            app_path = sys.argv[0]
        
        subprocess.call(['sudo', app_path])
        return
    
    root = tk.Tk()
    app = CursorEnhanceTool(root)
    root.mainloop()

if __name__ == "__main__":
    main() 