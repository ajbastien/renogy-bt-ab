import logging
import configparser
import os
import sys
import time
from renogybt import ShuntClient, DCChargerClient, InverterClient, RoverClient, RoverHistoryClient, BatteryClient, DataLogger, Utils

# Configure the logger
logging.basicConfig(level=logging.WARNING)
#logging.basicConfig(
#    filename='renogy.log',  # Specify the log file name
#    level=logging.INFO,  # Set the logging level (e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL)
#    format='%(asctime)s - %(levelname)s - %(message)s' # Define the log message format
#)

# the callback func when you receive data
def on_data_received(client, data, config):
    data_logger: DataLogger = DataLogger(config)
    filtered_data = Utils.filter_fields(data, config['data']['fields'])
    logging.warning(f"{client.ble_manager.device.name} => {filtered_data}")
    if config['remote_logging'].getboolean('enabled'):
        data_logger.log_remote(json_data=filtered_data)
    if config['mqtt'].getboolean('enabled'):
        data_logger.log_mqtt(json_data=filtered_data)
    if config['pvoutput'].getboolean('enabled') and config['device']['type'] == 'RNG_CTRL':
        data_logger.log_pvoutput(json_data=filtered_data)
    if not config['data'].getboolean('enable_polling'):
        client.stop()

# error callback
def on_error(client, error):
    logging.error(f"on_error: {error}")

# Process the configuration file
def process_config(config_file):
    config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), config_file)
    config = configparser.ConfigParser(inline_comment_prefixes=('#'))
    config.read(config_path)

    logging.warning(f"Processing {config_file}...")

    # start client
    if config['device']['type'] == 'RNG_CTRL':
        RoverClient(config, on_data_received, on_error).start()
    elif config['device']['type'] == 'RNG_CTRL_HIST':
        RoverHistoryClient(config, on_data_received, on_error).start()
    elif config['device']['type'] == 'RNG_BATT':
        BatteryClient(config, on_data_received, on_error).start()
    elif config['device']['type'] == 'RNG_INVT':
        InverterClient(config, on_data_received, on_error).start()
    elif config['device']['type'] == 'RNG_DCC':
        DCChargerClient(config, on_data_received, on_error).start()
    elif config['device']['type'] == 'RNG_SHNT':
        ShuntClient(config, on_data_received, on_error).start()
    else:
        logging.error("unknown device type")

loopvalue = 0
loopcount = 1  # -1 means infinite loop
count = 1

if len(sys.argv) > 1:
    try:
        while loopcount < 0 or count <= loopcount:
            for arg in sys.argv[1:]:
                if arg.startswith('-lt:'):
                    try:
                        loopvalue = int(arg[4:])
                    except ValueError:
                        print("Invalid loop value. Please provide a valid integer.")
                        sys.exit(1)
                elif arg.startswith('-lc:'):
                    try:
                        loopcount = int(arg[4:])
                    except ValueError:
                        print("Invalid loop count. Please provide a valid integer.")
                        sys.exit(1)
                elif os.path.isfile(arg):
                    process_config(arg)
                else:
                    print(f"File not found: {arg}")
                    sys.exit(1)

            time.sleep(loopvalue)
            count += 1

    except KeyboardInterrupt:
        print("\nCtrl+C detected. Performing cleanup...")

else:
    print("Usage: <options> python renogyProcessor.py <config_file1> <config_file2> ...")
    print("   Options: -lt:nn (loop every nn secs)")
    print("            -lc:nn (max number of loops)")

