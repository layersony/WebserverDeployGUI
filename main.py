from flask import Flask, render_template, request, redirect, jsonify, flash
import subprocess, re, logging, json, os
from flask_bootstrap import Bootstrap

app = Flask(__name__)
app.secret_key = 'my_secret_key'
bootstrap = Bootstrap(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/setupproj', methods=['GET', 'POST'])
def setupproj():
    return render_template('setup.html')

@app.route('/createservice', methods=['POST'])
def createservice():
    with open(f'{os.getcwd()}importantdocs/config.json', 'r') as file:
        data = json.load(file)

    # clone project params
    pGitRepo = request.form.get('pGitRepo')


    # execute command params
    port = request.form.get('port')
    execCommand = request.form.get('execCommand')

    # create service params
    description = request.form.get('description')

    # create live file params
    domainUrl = request.form.get('domainUrl')

    if port == 'select':
        flash("Select Port")
        return redirect('setupproj')
    elif port == '':
        flash("Port Already Assigned")
        return redirect('setupproj')

    if any(x == '' for x in [pGitRepo, execCommand, description, domainUrl]):
        flash(f'Fields must not be empty')
        return redirect('setupproj')

    pname = re.split(r"[/,.\s]\s*", pGitRepo)[-2]

    # Clone Project
    subprocess.run(['git', '-C', f'{data.get("filePath")}', 'clone', f'{pGitRepo}'], check=True)    

    # execute file
    exeFile = f"""#!/usr/bin/bash

clear
/home/ecp/.cache/pypoetry/virtualenvs/homa-bay-diocese--4uMdtugC-py3.9/bin/python /var/www/html/machini/Homa-Bay-Diocese/manage.py runserver 0.0.0.0:{port}

exit 0
    """

    with open(f'{data.get("execFilePath")}/{pname}.sh', 'w') as f:
        f.write(exeFile)

    # Assign port
    with open(f'{os.getcwd()}importantdocs/ports.json', 'r') as f:
        dataPort = json.load(f)
    
    for d in dataPort:
        if d['port'] == port:
            d['assign'] = True

    with open(f'{os.getcwd()}importantdocs/ports.json', 'w') as f:
        json.dump(dataPort, f)

    # Unit File
    unit_file = f'''[Unit]
Description={description}
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=ecp
Restart=always
WorkingDirectory={data.get("filePath")}/{pname}
ExecStart={data.get("execFilePath")}/{pname}.sh
Environment="TERM=xterm-256color"

[Install]
WantedBy=multi-user.target
'''

    with open(f'{data.get("servicePath")}/{pname}.service', 'w') as f:
        f.write(unit_file)

    subprocess.run(['sudo', 'systemctl', 'daemon-reload'])
    subprocess.run(['sudo', 'systemctl', 'restart', f'{pname}.service'])

    # live file (Apache)
    liveFile = f"""<VirtualHost *:80>
    ServerName {domainUrl}
    ServerAlias www.{domainUrl}

    ServerAdmin {data.get("serverAdminEmail")}
    DocumentRoot {data.get("filePath")}/{pname}
    ProxyPreserveHost On

    ProxyPass / http://127.0.0.1:{port}/ 

    ErrorLog ${{APACHE_LOG_DIR}}/error.log
    CustomLog ${{APACHE_LOG_DIR}}/access.log combined

</VirtualHost>

# vim: syntax=apache ts=4 sw=4 sts=4 sr noet
    """

    with open(f'{data.get("apachePath")}/{pname}.conf', 'w') as f:
        f.write(liveFile)

    return redirect('/')

@app.route('/securesite', methods=['GET'])
def securesite():
    return render_template('secure.html')

@app.route('/config', methods=['GET'])
def config():
    with open(f'{os.getcwd()}importantdocs/config.json', 'r') as file:
        data = json.load(file)
    return render_template('config.html', data=data)

@app.route('/configSetup', methods=['POST'])
def configSetup():
    execFilePath = request.form.get("execFilePath")
    filePath = request.form.get("filePath")
    apachePath = request.form.get("apachePath")
    servicePath = request.form.get("servicePath")
    workingDir = request.form.get("workingDir")
    serverAdminEmail = request.form.get("serverAdminEmail")

    if any(x == '' for x in [execFilePath, filePath, apachePath, servicePath, workingDir, serverAdminEmail]):
        return redirect('configSetup')

    with open(f'{os.getcwd()}importantdocs/config.json', 'r') as f:
        data = json.load(f)

    data["execFilePath"] = execFilePath
    data["filePath"] = filePath
    data["apachePath"] = apachePath
    data["servicePath"] = servicePath
    data["workingDir"] = workingDir
    data["serverAdminEmail"] = serverAdminEmail

    with open(f'{os.getcwd()}importantdocs/config.json', 'w') as file:
        json.dump(data, file)

    return render_template('config.html', data=data)

@app.route('/sitehealth', methods=['GET'])
def sitehealth():
    return render_template('health.html')

@app.route('/ports', methods=['GET'])
def ports():
    with open(f'{os.getcwd()}importantdocs/ports.json', 'r') as f:
        data = json.load(f)
    return jsonify(data)

if __name__ == '__main__':
    if os.geteuid() != 0:
        print("You need to have root privileges to run this command.")
        exit()
    else:
        app.run(debug=True, host='0.0.0.0', port=9010)
