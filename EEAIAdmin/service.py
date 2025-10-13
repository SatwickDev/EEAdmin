import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import threading
from app import create_app

class FlaskService(win32serviceutil.ServiceFramework):
    _svc_name_ = "MyFlaskService"
    _svc_display_name_ = "My Flask Service"
    _svc_description_ = "Runs Flask using create_app() as a Windows Service"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.running = True

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.running = False
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        servicemanager.LogInfoMsg("Starting MyFlaskService...")
        threading.Thread(target=self.run_flask).start()
        win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)

    def run_flask(self):
        app = create_app()
        app.run(host="0.0.0.0", port=5000, debug=False)

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(FlaskService)
