import os
import sys
import logging
from datetime import datetime, timedelta

# Use this script to check the renogy.log file and restart the Pi if the log is stale
# Put this script in /home/pi or change the BASE_FOLDER variable below
# You can run this script from cron or as a service in System Control

# Define the base folder as a global variable
BASE_FOLDER = "/home/pi"  # Change this to your desired path

# Set up logging to a file in BASE_FOLDER
logging.basicConfig(
    filename=os.path.join(BASE_FOLDER, 'checkRestartPi.log'),
    level=logging.INFO,
    format='%(asctime)s-%(levelname)s: %(message)s'
)

def restart_pi():
    try:
        logging.info("Restarting Raspberry Pi...")
        os.system("sudo reboot")
    except Exception as e:
        logging.error(f"Error: {e}")
        sys.exit(1)

def restartPiIfNeeded(log_file):
    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
            if not lines:
                logging.warning("Log file is empty.")
                return None
            last_line = lines[-1].strip()
            # Assuming the date is at the start of the line, e.g. "2024-06-10 12:34:56, Some log message"
            date_str = last_line.split(',', 1)[0].strip()
            try:
                log_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                logging.debug(f"Last log date: {date_str}  -  Delta: {datetime.now() - log_date}")
                if datetime.now() - log_date > timedelta(minutes=30):
                    logging.warning("Log date is more than 30 minutes in the past. Restarting Pi.")
                    restart_pi()
            except ValueError:
                logging.error("Could not parse date from log line.")
            return date_str
    except Exception as e:
        logging.error(f"Error reading log file: {e}")
        return None

if __name__ == "__main__":
    log_file_path = os.path.join(BASE_FOLDER, "renogy.log")
    restartPiIfNeeded(log_file_path)

