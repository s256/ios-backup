from flask import Flask, jsonify
from datetime import date, datetime
import subprocess
import dotenv
import os
import requests
import logging

dotenv.load_dotenv()
config = {
    'device_uuid': os.getenv('DEVICE_UUID'),
    'backup_path': os.getenv('BACKUP_PATH'),
    'hass_state_entity': os.getenv('HASS_STATE_ENTITY'),
    'hass_url': os.getenv('HASS_URL'),
    'hass_api_key': os.getenv('HASS_API_KEY'),
    'log_path': os.environ.get('LOG_PATH', '.'),
    'state_file_path': os.environ.get('STATE_FILE_PATH', '.'),
    'idevicebackup2_bin': os.environ.get('BACKUP_BIN_PATH', '/usr/local/bin/idevicebackup2')
}

hass_api_headers = {
    "Authorization": f"Bearer {config['hass_api_key']}",
    "content-type": "application/json",
}

api_path = config['hass_url'] + \
    '/api/states/' + config['hass_state_entity']

LATEST_PATH = f"{config['state_file_path']}/latest-backup-date"
CURDATE = date.today().isoformat()

log_file_path = config['log_path'] + '/ios-backup.log'

logging.basicConfig(
    level=logging.INFO,
    filename=log_file_path,
    filemode="a",
    encoding="utf-8",
)

for k, v in config.items():
    if v == None:
        raise Exception(f'Missing Setting (env var) for "{k}"')


def is_last_backup_from_today(last_backup_timestamp_file):
    try:
        with open(last_backup_timestamp_file, 'r') as f:
            last_backup = f.readline()
    except OSError:
        last_backup = None
    today = date.today().isoformat()
    return (last_backup == today)


def is_last_backup_from_today_hass(api_path: str, api_headers: str):
    try:
        response = requests.get(url=api_path, headers=api_headers)
        last_backup = response.json()['state']
    except:
        last_backup = None
    today = date.today().isoformat()
    return (last_backup == today)


app = Flask(__name__)


@app.route('/', methods=['GET'])
def health_check():
    return jsonify({'message': 'Healthcheck'})


@app.route('/backup', methods=['POST'])
def run_backup():

    logging.info("Starting Backup procedure at " +
                 datetime.utcnow().isoformat())

    if not is_last_backup_from_today_hass(
            api_headers=hass_api_headers, api_path=api_path):
        logging.info(
            "[ibackup] No current backup exists, trying to run backup now")
        args = [config['idevicebackup2_bin'], "backup",
                config['backup_path'], "-n", "-u", config['device_uuid']]
        process = subprocess.Popen(
            args=args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        while True:
            output = process.stdout.readline()
            if process.poll() is not None:
                break
            if output:
                logging.info(output.strip())
        rc = process.poll()
        if rc == 0:
            # with open(LATEST_PATH, "w") as timestamp_file:
            #     timestamp_file.write(CURDATE)
            hass_payload = {
                'state': CURDATE
            }
            logging.info('Updating state in Home-Assistant')
            try:
                hass_response = requests.post(
                    url=api_path, headers=hass_api_headers, json=hass_payload)
            except Exception as e:
                logging.error(f'Failed to update Home-Assistant State - ' + e)
                return 1
            if hass_response.status_code != 200:
                logging.error('Failed to update Home-Assistant State with ' +
                              str(hass_response.status_code))
                logging.error(hass_response.json())
                return 1
            logging.info('Backup process ended')
            return jsonify(
                {
                    'date': CURDATE,
                    'message': 'Backup created'
                }
            )
        else:
            logging.info("Backup failed with: " + output)
            return f"Backup failed, see log file '{log_file_path}'", 503
    else:
        logging.info("[ibackup] Backup for today exists.")
        return jsonify({
            'date': CURDATE,
            'message': 'Backup for today exists'})


if __name__ == '__main__':
    app.run()
