# selfhosted iOS Backups - with homeassistant automation
A flask wrapper for `libimobiledevice`to offer a simple API to be triggered by Homeassistant to never forget you're backup.

DISCLAIMER: Apple decided to ALWAYS ask for your PIN when starting a backup which is not in their iCloud. Right now there is no way around.

## Features
* create iOS Backup over Network
* Updates Home-Assistant entity 
    * create automation to sent push to mobile if there isn't a recent backup
## Requirements
* requires [libimobiledevice](https://github.com/libimobiledevice/libimobiledevice)
    * install from git or your package manager
* `usbmuxd2` see [How-To.md](How-To.md)
* requires a node to run this

* [Homeassistant](https://www.home-assistant.io/) (you can remove the code which uses homeassistant of course)

* `avahi-daemon`

## Automation & Context

I'm not happy storing my backups with a cloud, but also I tend to forget to create backups, if it doesn't happen automatically.
For Android there is SeedVault, there is no comparable implementation for Apple's iOS.

As I'm using [Homeassistant](https://www.home-assistant.io/) I wanted to trigger the automation, when I'm at home and the device is idle.
And I wanted to create one backup per day and get an alert if there is no recent backup for a week.

As Homeassistant triggers the events, but another machine handles the backups, this flask wrapper was created to offer an "API" for HASS.

## Setup
* clone Repo `cd /opt/ && git clone https://github.com/s256/ios-backup` & `cd ios-backup`
* create virtual environment with `virtualenv .venv` & `source .venv/bin/activate` & `pip install pipenv`
* install packages `pipenv install`
* connect iOS-Device via USB to Server/machine (only needed once for setup)
* pair device `idevicepair pair` & `idevicepair wifi on`
* enable encryption of backup `idevicebackup2 encryption on $MYSUPERSECRETPASSWORD`
    * BACKUP YOUR PASSWORD OR YOUR BACKUPS WILL BE INACCESSIBLE!
* deactivate cloud backup `idevicebackup2 backup cloud off`

* copy the `.service` file to your systemd service folder e.g. `/etc/systemd/system/`
* `systemctl daemon-reload`

### Reverse Proxy - NGINX
* install `nginx`
* copy the file from `reverseproxy/` to your nginx `sites-available`and enable it
    * `cp ./reverseproxy/*.conf /etc/nginx/site-available/ && ln -s /etc/nginx/sites-enabled/ios-backup.conf/ /etc/nginx/site-available/nginx-vhost.conf`
* adapt the nginx config file, it assumes you're using SSL with Let's encrypt. Set a vhost which fits your local setup.

### Firewall
* `libimobiledevice` is using `bonjour` so open `UDP 1900 & UDP 5353` on your machines firewall.

### Homeassistant

Add a `rest_command` to homeassistant to trigger the backup.

In your `configuration.yaml` add 
```
rest_command:
  iphone_backup:
    url: "https://iosbackup.example.com/backup"
    method: post
    content_type: "application/json"
```

Add a `Helper` of type `Date` so it becomes `input_datetime` but only accepts `Date`.

Add an Automation, to start the Backup if certain criterias are met, e.g. you are at home and the device is stationary, connected to your wifi and not on focus mode.

``` 
alias: "Backup: Start iPhone backup"
description: Backup iPhone
trigger:
  - platform: state
    entity_id:
      - sensor.XXX_iphone_mini_activity
    to: Stationary
    for:
      hours: 0
      minutes: 5
      seconds: 0
condition:
  - condition: state
    entity_id: sensor.XXX_iphone_mini_connection_type
    state: Wi-Fi
  - condition: state
    entity_id: binary_sensor.XXX_iphone_mini_focus
    state: "off"
  - condition: state
    entity_id: sensor.XXX_iphone_mini_ssid
    state: MYWIFISSIDNAME
action:
  - service: rest_command.iphone_mini_backup
    metadata: {}
    data: {}
mode: single
```

Create an "Alert" to inform you, when there was no recent backup in the last 7 days

```
alias: "Alert: Old Backup"
description: ""
trigger:
  - platform: state
    entity_id:
      - sensor.old_ios_backup
    to: "True"
condition: []
action:
  - service: notify.mobile_app_XXX_iphone_mini
    metadata: {}
    data:
      title: Run a fresh Backup of your phone!
      message: Last Backup is older than 1 week. Time for a new backup of your phone!
mode: single
```

### Config via `ENV` or `.env` 
Replace all config entries in the `.env` file or pass them as Environmentvariables, e.g. in the systemd file.


## To-Dos:
* API Authentication - This Setup was intended for your home network, where `zero trust`is a bit over the top and you need `avahi / bonjour` to discover the iOS device.
    * nevertheless: API Authentication is best pratice


## Credits

Inspired by https://valinet.ro/2021/01/20/Automatically-backup-the-iPhone-to-the-Raspberry-Pi.html


