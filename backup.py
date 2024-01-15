from flask import Flask, jsonify
from datetime import date, datetime
import dotenv
import subprocess
import os
import requests

dotenv.load_dotenv()
config = {
    'device_uuid': os.getenv('DEVICE_UUID'),
    'backup_path': os.getenv('BACKUP_PATH'),
    'hass_backup_entity': os.getenv('HASS_BACKUP_ENTITY'),
    'hass_url': os.getenv('HASS_URL'),
    'hass_api_key': os.getenv('HASS_API_KEY'),
    'log_path': os.environ.get('LOG_PATH','.'),
    'idevicebackup2_bin': os.environ.get('BACKUP_BIN_PATH', '/usr/local/bin/idevicebackup2')
}

hass_api_headers = {
    "Authorization": f"Bearer {config['hass_api_key']}",
    "content-type": "application/json",
}

LATEST_PATH = "./latest-backup-date"
CURDATE = date.today().isoformat()

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



app = Flask(__name__)

@app.route('/backup', methods=['POST'])
def run_backup():
    print("Starting Backup procedure")

    log_file_path = config['log_path'] + '/backup_log_' + datetime.utcnow().strftime("%Y%m%d%H%M%S")

    api_path = config['hass_url'] + '/api/states/' + config['hass_backup_entity']
    if not is_last_backup_from_today(LATEST_PATH):
        print("[ibackup] No current backup exists, trying to run backup now")
        result = subprocess.run([config['idevicebackup2_bin'], "backup", config['backup_path'], "-n", "-u", config['device_uuid']], capture_output=True, text=True)
        if result.returncode == 0:
            with open(log_file_path, "w") as log_file:
                log_file.write(result.stdout)
            with open(LATEST_PATH, "w") as timestamp_file:
                timestamp_file.write(CURDATE)
            hass_payload = {
                'state': CURDATE
            }
            print('Updating state in Home-Assistant')
            try:
                hass_response = requests.post(url=api_path, headers=hass_api_headers, json=hass_payload)
                if hass_response.status_code != 200:
                    print(f'Failed to update Home-Assistant State with {hass_response.status_code} - {hass_response.json}')
                else:
                    return jsonify(
                        {
                            'date': CURDATE,
                            'message': 'Backup created'
                            }
                            )
            except OSError:
                print('Failed to update Home-Assistant State')
            return jsonify({'date': CURDATE})
        else:
            print("Backup failed with: " + result.stderr)
            with open(log_file_path, "w") as log_file:
                log_file.write(result.stdout)
                log_file.write(result.stderr)
            return f"Backup failed, see log file '{log_file}'", 503
    else:
        print("[ibackup] Backup for today exists.")
        return jsonify({
            'date': CURDATE,
            'message': 'Backup for today exists'})


if __name__ == '__main__':
    app.run()