import yaml
import docker
from flask import Flask, render_template, redirect, url_for
import os
import sys

app = Flask(__name__)
client = docker.from_env()

# Load apps from apps.yaml
def load_apps():
    # Determine if the application is running as a pyinstaller executable
    if getattr(sys, 'frozen', False):
        # If the application is running as a pyinstaller executable, the apps.yaml file is in the same directory as the executable
        # so we can use sys._MEIPASS to get the path to the directory
        application_path = sys._MEIPASS
    else:
        # running as a normal python script
        application_path = os.path.dirname(os.path.abspath(__file__))
    
    # construct the full path to the apps.yaml file
    apps_path = os.path.join(application_path, 'apps.yaml')

    with open(apps_path, 'r') as file:
        apps = yaml.safe_load(file)
        print(apps)
    return apps

# demo apps's data structure is like this:

demo_apps = load_apps()
print(demo_apps)

@app.route('/')
def index():
    container_status = {}
    for key in demo_apps.keys():
        try:
            container = client.containers.get(key)
            container_status[key] = container.status
        except docker.errors.NotFound:
            container_status[key] = "stopped"
    return render_template('index.html', demo_apps = demo_apps, container_status = container_status)


@app.route('/start/<app_name>')
def start_app(app_name):
    app_info = demo_apps[app_name]
    try:
        # check if container is already running
        container = client.containers.get(app_name)
        if container.status == "exited":
            container.start()
    except docker.errors.NotFound:
        # run the container if it doesn't exist
        ports = {}
        for port_mapping in app_info.get("ports", []):
            # port mapping is like this: 8081:80, so we need to split it into host_port and container_port
            host_port, container_port = port_mapping.split(':')
            # convert host_port to int, tcp is the protocol
            ports[int(container_port)] = int(host_port)
        # run the container with the specified image and ports
        client.containers.run(
            image = app_info["image"],
            name = app_name,
            command = app_info.get("command", ""),
            ports = ports,
            detach = True,
            environment = app_info.get('env'),
            volumes = app_info.get('volumes')
        )
    # if the container is running, redirect to the index page
    return redirect(url_for('index'))

@app.route('/stop/<app_name>')
def stop_app(app_name):
    if app_name in demo_apps:
        try:
            container = client.containers.get(app_name)
            container.stop()
        # if the container is not running, do nothing
        except docker.errors.NotFound:
            pass
    # if the container is stopped, redirect to the index page
    return redirect(url_for('index'))

# run the app if the file is executed directly
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
