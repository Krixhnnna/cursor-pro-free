import os
import shutil
import ctypes
import sys
import getpass
import configparser
import json
import time
import random
import string
import hashlib
import uuid
import subprocess
import sqlite3
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

# 添加CursorMachineIDReset类
class CursorMachineIDReset:
    """Cursor 机器ID重置工具类"""
    
    def __init__(self):
        self.system = sys.platform
        self.config_paths = self._get_config_paths()
        self.log_messages = []
        self.device_ids = {}
        
    def log(self, message):
        """记录日志消息"""
        self.log_messages.append(message)
        return message
        
    def _get_config_paths(self):
        """获取不同操作系统下的配置文件路径"""
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
        """生成新的机器ID"""
        # 生成UUID格式的机器ID
        new_uuid = str(uuid.uuid4()).upper()
        self.log(f"✓ 生成新机器ID: [{new_uuid}]")
        return new_uuid
    
    def create_backup(self, file_path):
        """创建文件备份"""
        if not os.path.exists(file_path):
            return True
            
        backup_dir = self.config_paths['backup_dir']
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_name = f"{os.path.basename(file_path)}.bak_{timestamp}"
        backup_path = os.path.join(backup_dir, backup_name)
        
        self.log(f"检查配置文件...")
        
        if os.path.exists(backup_path):
            self.log(f"备份已存在: {backup_path}")
            return True
            
        try:
            shutil.copy2(file_path, backup_path)
            self.log(f"✓ 创建备份成功: {backup_path}")
            return True
        except Exception as e:
            self.log(f"✗ 创建备份失败: {str(e)}")
            return False
    
    def update_storage_json(self, new_machine_id):
        """更新storage.json配置文件"""
        config_path = self.config_paths['config']
        self.log(f"更新配置文件...")
        
        if not os.path.exists(config_path):
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            config_data = {}
            self.log("配置文件不存在，将创建新配置")
        else:
            # 创建备份
            if not self.create_backup(config_path):
                return False
                
            # 读取现有配置
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                self.log("读取现有配置成功")
            except Exception as e:
                self.log(f"✗ 读取配置失败: {str(e)}")
                return False
        
        # 生成新的设备ID
        dev_device_id = str(uuid.uuid4())
        sqm_id = str(uuid.uuid4())
        
        # 保存ID以供显示
        self.device_ids = {
            'devDeviceId': dev_device_id,
            'macMachineId': new_machine_id,
            'machineId': new_machine_id,
            'sqmId': sqm_id
        }
        
        # 更新机器ID相关配置
        config_data.update({
            'telemetry.machineId': new_machine_id,
            'telemetry.macMachineId': new_machine_id,
            'telemetry.devDeviceId': dev_device_id,
            'telemetry.sqmId': sqm_id,
        })
        
        # 保存更新后的配置
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            self.log("✓ 保存配置到JSON...")
            return True
        except Exception as e:
            self.log(f"✗ 保存配置失败: {str(e)}")
            return False
    
    def update_machine_id_file(self, new_machine_id):
        """更新machineId文件"""
        machine_id_path = self.config_paths['machine_id']
        self.log("更新machineId文件...")
        
        # 创建备份
        if os.path.exists(machine_id_path):
            if not self.create_backup(machine_id_path):
                return False
        
        try:
            os.makedirs(os.path.dirname(machine_id_path), exist_ok=True)
            with open(machine_id_path, 'w', encoding='utf-8') as f:
                f.write(new_machine_id)
            self.log("✓ 更新machineId文件成功")
            return True
        except Exception as e:
            self.log(f"✗ 更新machineId文件失败: {str(e)}")
            return False
    
    def update_sqlite_database(self, new_machine_id):
        """更新SQLite数据库"""
        db_path = self.config_paths['sqlite_db']
        self.log("更新SQLite数据库...")
        
        if not os.path.exists(db_path):
            self.log("SQLite数据库不存在，跳过更新")
            return True
            
        # 创建备份
        if not self.create_backup(db_path):
            return False
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 更新键值对
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
                self.log(f"  更新键值对: {key}")
            
            conn.commit()
            conn.close()
            self.log("✓ SQLite数据库更新成功")
            return True
            
        except Exception as e:
            self.log(f"✗ 更新SQLite数据库失败: {str(e)}")
            return False
    
    def update_system_id(self, new_machine_id):
        """更新系统ID（仅适用于Windows）"""
        self.log("更新系统ID...")
        
        if self.system == "win32":
            try:
                import winreg
                # 尝试更新注册表中的机器GUID
                key_path = r"SOFTWARE\Microsoft\SQMClient"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, "MachineId", 0, winreg.REG_SZ, new_machine_id)
                self.log("✓ Windows机器ID更新成功")
                self.log(f"✓ reset.new machine id: [{new_machine_id}]")
                return True
            except Exception as e:
                self.log("✗ Windows机器ID更新失败")
                return False
        elif self.system == "darwin":
            self.log("macOS系统ID更新功能未实现")
            return True
        else:
            self.log("Linux系统ID更新功能未实现")
            return True
    
    def check_cursor_version(self):
        """检查Cursor版本"""
        self.log("检查Cursor版本...")
        
        if self.system == "win32":
            # Windows版本检查
            try:
                package_path = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Cursor', 'resources', 'app', 'package.json')
                if os.path.exists(package_path):
                    with open(package_path, 'r', encoding='utf-8') as f:
                        package_data = json.load(f)
                        version = package_data.get('version', 'unknown')
                    self.log(f"✓ 检测package.json: {package_path}")
                    self.log(f"✓ 检测版本号: {version}")
                    
                    # 为新版本执行特殊处理
                    if version and version.split('.')[0] >= '0' and version.split('.')[1] >= '45':
                        self.log(f"✓ 检测Cursor版本 >= 0.45.0, 修改setMachineId")
                        self.log("执行修改telMachineId...")
                    
                    self.log(f"✓ 当前Cursor版本: {version}")
                    self.log("✓ Cursor版本检测通过")
                    return True
                else:
                    self.log("未找到package.json")
                    return False
            except Exception as e:
                self.log(f"版本检测失败: {str(e)}")
                return False
        else:
            # macOS/Linux版本检查
            self.log("跳过非Windows平台版本检查")
            return True
    
    def reset_machine_id(self):
        """执行完整的机器ID重置流程"""
        try:
            self.log_messages = []  # 清空日志
            
            # 1. 生成新的机器ID
            new_machine_id = self.generate_machine_id()
            
            # 2. 更新storage.json配置文件
            if not self.update_storage_json(new_machine_id):
                return False, "更新配置文件失败", self.log_messages
            
            # 3. 更新machineId文件
            if not self.update_machine_id_file(new_machine_id):
                return False, "更新机器ID文件失败", self.log_messages
            
            # 4. 更新SQLite数据库
            if not self.update_sqlite_database(new_machine_id):
                return False, "更新数据库失败", self.log_messages
                
            # 5. 更新系统ID
            self.update_system_id(new_machine_id)
            
            # 6. 检查Cursor版本
            self.check_cursor_version()
            
            # 7. 打印新机器码信息
            self.log("")
            self.log("新机器码信息:")
            self.log(f"  telemetry.devDeviceId: {self.device_ids['devDeviceId']}")
            self.log(f"  telemetry.macMachineId: {self.device_ids['macMachineId']}")
            self.log(f"  telemetry.machineId: {self.device_ids['machineId']}")
            self.log(f"  telemetry.sqmId: {self.device_ids['sqmId']}")
            self.log(f"  storage.serviceMachineId: {self.device_ids['devDeviceId']}")
            
            self.log("✓ 机器码重置成功")
            
            return True, new_machine_id, self.log_messages
            
        except Exception as e:
            error_msg = f"重置进程错误: {str(e)}"
            self.log(f"✗ {error_msg}")
            return False, error_msg, self.log_messages

def is_admin():
    """检查脚本是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def read_config():
    """读取配置文件"""
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.env')
    
    if not os.path.exists(config_path):
        create_default_config(config_path)
    
    config.read(config_path)
    return config

def create_default_config(config_path):
    """创建默认配置文件"""
    config = configparser.ConfigParser()
    username = getpass.getuser()
    default_base_path = os.path.join('C:\\Users', username, 'AppData\\Roaming\\Cursor\\User')
    
    config['PATHS'] = {
        'base_path': default_base_path
    }
    
    with open(config_path, 'w') as configfile:
        config.write(configfile)
    
    print(f"已创建默认配置文件: {config_path}")
    print(f"默认路径设置为: {default_base_path}")

def clean_cursor_files():
    """清理Cursor应用的文件和文件夹"""
    # 读取配置文件
    config = read_config()
    base_path = config['PATHS']['base_path']
    
    result_message = f"清理 {base_path} 中的文件...\n"
    
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
    
    for file_path in files_to_delete:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                result_message += f"已删除文件: {file_path}\n"
            else:
                result_message += f"文件不存在: {file_path}\n"
        except Exception as e:
            result_message += f"删除文件 {file_path} 失败: {e}\n"
    
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
                        result_message += f"删除 {item_path} 失败: {e}\n"
                result_message += f"已清空文件夹: {folder_path}\n"
            else:
                result_message += f"文件夹不存在: {folder_path}\n"
        except Exception as e:
            result_message += f"清空文件夹 {folder_path} 失败: {e}\n"
    
    for folder_path in folders_to_delete:
        try:
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
                result_message += f"已删除文件夹: {folder_path}\n"
            else:
                result_message += f"文件夹不存在: {folder_path}\n"
        except Exception as e:
            result_message += f"删除文件夹 {folder_path} 失败: {e}\n"
    
    result_message += "清理完成！"
    return result_message



def is_cursor_running():
    """检查 Cursor 是否正在运行（不依赖第三方库）"""
    try:
        if sys.platform == "win32":
            # Windows
            output = subprocess.check_output('tasklist', shell=True, stderr=subprocess.DEVNULL).decode('utf-8', errors='ignore')
            return any(proc.lower().startswith('cursor') for proc in output.split('\n'))
        else:
            # Unix-like systems (Linux, macOS)
            output = subprocess.check_output(['ps', 'aux'], stderr=subprocess.DEVNULL).decode('utf-8', errors='ignore')
            return any('cursor' in line.lower() for line in output.split('\n'))
    except subprocess.SubprocessError:
        return False  # 如果执行命令失败，假设进程未运行
    except Exception as e:
        return False

# 移除警告对话框，直接执行函数
def check_cursor_process(func):
    """装饰器：检查 Cursor 进程，但不显示警告"""
    def wrapper(*args, **kwargs):
        # 直接执行函数，不显示警告
        return func(*args, **kwargs)
    return wrapper

def kill_cursor_processes():
    """终止所有 Cursor 相关进程"""
    result_message = ""
    try:
        if sys.platform == "win32":
            # Windows
            try:
                subprocess.run(['taskkill', '/F', '/IM', 'Cursor.exe'], 
                             check=False, 
                             stderr=subprocess.PIPE,
                             stdout=subprocess.PIPE)
                subprocess.run(['taskkill', '/F', '/IM', 'cursor.exe'], 
                             check=False,
                             stderr=subprocess.PIPE,
                             stdout=subprocess.PIPE)
            except subprocess.SubprocessError:
                result_message += "无法找到 Cursor 进程或没有权限终止进程\n"
        else:
            # Unix-like systems (Linux, macOS)
            try:
                # 使用 pgrep 查找进程
                pids = subprocess.check_output(['pgrep', '-i', 'cursor'], 
                                            stderr=subprocess.DEVNULL).decode().split()
                for pid in pids:
                    try:
                        os.kill(int(pid), 15)  # SIGTERM
                        time.sleep(0.1)
                        try:
                            os.kill(int(pid), 0)  # 检查进程是否还存在
                            os.kill(int(pid), 9)  # SIGKILL
                        except ProcessLookupError:
                            pass  # 进程已经终止
                    except ProcessLookupError:
                        continue  # 跳过已经不存在的进程
            except subprocess.CalledProcessError:
                result_message += "未找到 Cursor 进程\n"
            except PermissionError:
                result_message += "没有权限终止进程\n"
        
        result_message += "已尝试终止所有 Cursor 进程"
    except Exception as e:
        result_message += f"终止进程时出错: {str(e)}\n"
    
    return result_message

@check_cursor_process
def reset_machine_ids():
    """重置机器 ID"""
    result_message = ""
    try:
        reset_tool = CursorMachineIDReset()
        success, message = reset_tool.reset_machine_id()
        
        if success:
            result_message = f"已成功重置机器 ID: {message}"
        else:
            result_message = f"重置机器 ID 时出错: {message}"
    except Exception as e:
        result_message = f"重置机器 ID 时出错: {str(e)}"
    
    return result_message

@check_cursor_process
def generate_random_machine_ids():
    """生成随机的机器 ID"""
    result_message = ""
    try:
        reset_tool = CursorMachineIDReset()
        success, new_machine_id = reset_tool.reset_machine_id()
        
        if success:
            result_message = "已生成新的机器 ID：\n"
            result_message += f"Mac机器ID: {new_machine_id}\n"
            result_message += f"机器ID: {new_machine_id}"
        else:
            result_message = f"生成机器 ID 时出错: {new_machine_id}"
    except Exception as e:
        result_message = f"生成机器 ID 时出错: {str(e)}"
    
    return result_message

@check_cursor_process
def break_claude_37_limit():
    """突破Claude 3.7 Sonnet限制"""
    result_message = ""
    try:
        reset_tool = CursorMachineIDReset()
        config_path = reset_tool.config_paths['config']
        
        if not os.path.exists(config_path):
            result_message = f"配置文件不存在: {config_path}"
            return result_message
        
        # 创建备份
        reset_tool.create_backup(config_path)
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 设置突破限制的关键值
        data["cursor.paid"] = True
        data["cursor.openaiFreeTier"] = True
        data["cursor.proTier"] = True
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        result_message = "已成功设置突破 Claude 3.7 Sonnet 限制"
    except Exception as e:
        result_message = f"突破限制时出错: {str(e)}"
    
    return result_message

class CursorEnhanceTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Cursor 增强工具")
        self.root.geometry("600x400")
        self.root.resizable(True, True)
        self.setup_ui()
    
    def setup_ui(self):
        # 设置主框架
        main_frame = ttk.Frame(self.root, padding="20 20 20 20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        ttk.Label(main_frame, text="Cursor 增强工具", font=("Arial", 16, "bold")).pack(pady=10)
        
        # 功能按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="1. 重置机器码", command=self.reset_machine_code).pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="2. 突破 Claude 3.7 Sonnet 限制并清理数据", command=self.break_limit_and_clean).pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="3. 终止 Cursor 进程", command=self.kill_process).pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="4. 退出", command=self.root.quit).pack(fill=tk.X, pady=5)
        
        # 结果文本框
        result_frame = ttk.LabelFrame(main_frame, text="操作结果")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.result_text = tk.Text(result_frame, wrap=tk.WORD, height=10)
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(self.result_text, command=self.result_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.config(yscrollcommand=scrollbar.set)
        
        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def show_result(self, message):
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, message)
    
    def reset_machine_code(self):
        self.status_var.set("正在重置机器码...")
        self.root.update()
        
        # 先终止Cursor进程
        kill_result = kill_cursor_processes()
        
        # 使用新的机器码重置工具
        reset_tool = CursorMachineIDReset()
        success, new_machine_id, log_messages = reset_tool.reset_machine_id()
        
        # 显示详细日志
        log_text = "\n".join(log_messages)
        
        self.show_result(f"{kill_result}\n\n{log_text}")
        self.status_var.set("重置机器码完成")
    
    def break_limit_and_clean(self):
        """突破限制并清理数据（合并选项2和3）"""
        self.status_var.set("正在突破限制并清理数据...")
        self.root.update()
        
        # 先终止Cursor进程
        kill_result = kill_cursor_processes()
        
        # 突破限制
        limit_result = break_claude_37_limit()
        
        # 清理文件
        clean_result = clean_cursor_files()
        
        self.show_result(f"{kill_result}\n\n{limit_result}\n\n{clean_result}")
        self.status_var.set("突破限制和清理数据完成")
    
    def kill_process(self):
        self.status_var.set("正在终止 Cursor 进程...")
        self.root.update()
        
        result = kill_cursor_processes()
        
        self.show_result(result)
        self.status_var.set("进程终止完成")

def main():
    """主函数"""
    if not is_admin():
        messagebox.showerror("权限错误", "请以管理员权限运行此脚本")
        # 如果不是管理员权限，尝试以管理员权限重新运行
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        return
    
    root = tk.Tk()
    app = CursorEnhanceTool(root)
    root.mainloop()

if __name__ == "__main__":
    main() 