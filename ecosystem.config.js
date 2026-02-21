module.exports = {
  apps: [
    {
      name: "whatsapp-watcher",
      script: "whatsapp_playwright_watcher.py",
      interpreter: "D:\\AI_Employee_Vault\\.venv\\Scripts\\pythonw.exe",
      cwd: "D:/AI_Employee_Vault",
      watch: false,
      autorestart: true,
      restart_delay: 10000,   // crash ke baad 10s wait karke restart
      max_restarts: 10,
      log_file: "D:/AI_Employee_Vault/Logs/whatsapp_watcher.log",
      error_file: "D:/AI_Employee_Vault/Logs/whatsapp_watcher_error.log",
      time: true,             // timestamps log mein
    },
    {
      name: "file-watcher",
      script: "watcher.py",
      interpreter: "D:\\AI_Employee_Vault\\.venv\\Scripts\\pythonw.exe",
      cwd: "D:/AI_Employee_Vault",
      watch: false,
      autorestart: true,
      restart_delay: 5000,
      max_restarts: 10,
      log_file: "D:/AI_Employee_Vault/Logs/file_watcher.log",
      error_file: "D:/AI_Employee_Vault/Logs/file_watcher_error.log",
      time: true,
    }
  ]
};
