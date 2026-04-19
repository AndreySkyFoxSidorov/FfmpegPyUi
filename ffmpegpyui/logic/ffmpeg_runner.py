import subprocess
import threading
import sys
import re

class FfmpegRunner:
    def __init__(self, update_callback, completion_callback, progress_callback=None):
        self.update_callback = update_callback
        self.completion_callback = completion_callback
        self.progress_callback = progress_callback
        self.process = None
        self.running = False
        self.stopped = False

    def run_commands(self, commands, durations=None):
        """
        Executes a list of commands (each command is a list of args).
        durations: Optional list of total durations (in seconds) for each command.
        """
        self.running = True
        self.stopped = False
        threading.Thread(target=self._worker, args=(commands, durations), daemon=True).start()

    def stop(self):
        self.stopped = True
        if self.process:
            self.process.terminate()
        self.running = False

    def _parse_time(self, line):
        # time=00:00:09.60
        match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
        if match:
            h, m, s = map(float, match.groups())
            return h * 3600 + m * 60 + s
        return None

    def _worker(self, commands, durations):
        total_tasks = len(commands)
        
        for i, cmd in enumerate(commands):
            if self.stopped: break
            
            cmd_str = " ".join(cmd)
            self.update_callback(f"[{i+1}/{total_tasks}] Running: {cmd_str}\n")
            
            current_duration = durations[i] if durations and i < len(durations) else None
            
            # Reset progress for new task
            if self.progress_callback:
                self.progress_callback(0.0)

            try:
                # Use Popen to capture realtime output
                # Using shell=False is safer, subprocess expects list
                # Hide window on Windows
                startupinfo = None
                if sys.platform == "win32":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                self.process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    universal_newlines=True,
                    startupinfo=startupinfo,
                    shell=False
                )
                
                for line in self.process.stdout:
                    if self.stopped: 
                        self.process.terminate()
                        break
                    
                    self.update_callback(line)
                    
                    # Progress parsing
                    if self.progress_callback and current_duration:
                        time_sec = self._parse_time(line)
                        if time_sec is not None:
                            percent = min(max(time_sec / current_duration, 0.0), 1.0)
                            self.progress_callback(percent)
                
                self.process.wait()
                
                if self.process.returncode != 0 and not self.stopped:
                    self.update_callback(f"\n[ERROR] Command failed with code {self.process.returncode}\n")
            
            except Exception as e:
                self.update_callback(f"\n[EXCEPTION] {str(e)}\n")

        self.running = False
        self.completion_callback(not self.stopped)
