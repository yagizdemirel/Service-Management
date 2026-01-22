import os
import platform
import subprocess
import time
import random
from flask import Flask, jsonify, render_template, request
import psutil

app = Flask(__name__)

# İşletim sistemi kontrolü
IS_MACOS = platform.system() == 'Darwin'
IS_LINUX = platform.system() == 'Linux'

class ServiceManager:
    @staticmethod
    def get_system_stats():
        """Sistem CPU ve RAM kullanımını döndürür."""
        return {
            'cpu_percent': psutil.cpu_percent(interval=None),
            'ram_percent': psutil.virtual_memory().percent,
            'boot_time': int(psutil.boot_time())
        }

    @staticmethod
    def get_all_services():
        """Tüm servisleri listeler."""
        if IS_MACOS:
            return ServiceManager._get_mock_services()
        
        try:
            # Linux'ta tüm servisleri listele
            cmd = ['systemctl', 'list-units', '--type=service', '--all', '--no-ask-password', '--no-legend', '--plain']
            result = subprocess.check_output(cmd).decode('utf-8')
            services = []
            
            for line in result.splitlines():
                parts = line.split()
                if len(parts) >= 4:
                    # systemctl çıktısı: unit load active sub description...
                    name = parts[0]
                    active_state = parts[2] # active / inactive
                    sub_state = parts[3]    # running / dead / exited
                    description = " ".join(parts[4:]) if len(parts) > 4 else ""
                    
                    status = 'unknown'
                    if active_state == 'active' and sub_state == 'running':
                        status = 'running'
                    elif active_state == 'failed':
                        status = 'failed'
                    elif sub_state == 'exited':
                        status = 'exited'
                    else:
                        status = 'stopped'

                    services.append({
                        'name': name,
                        'status': status,
                        'description': description
                    })
            return services
        except Exception as e:
            return [{'name': 'Error', 'status': 'failed', 'description': str(e)}]

    @staticmethod
    def get_service_logs(service_name, lines=50):
        """Bir servisin loglarını getirir."""
        if IS_MACOS:
            return ServiceManager._get_mock_logs(service_name)

        try:
            cmd = ['journalctl', '-u', service_name, '-n', str(lines), '--no-pager']
            result = subprocess.check_output(cmd).decode('utf-8')
            return result
        except Exception as e:
            return f"Error retrieving logs: {str(e)}"

    @staticmethod
    def control_service(service_name, action):
        """Servisi başlatır, durdurur veya yeniden başlatır."""
        valid_actions = ['start', 'stop', 'restart']
        if action not in valid_actions:
            return False, "Invalid action"

        if IS_MACOS:
            # macOS Mock Simülasyonu: Başarılı gibi davran
            time.sleep(1) # İşlem süresini simüle et
            return True, f"Mock: Service {service_name} {action}ed successfully"
        
        try:
            # Linux Production Komutu
            # Not: Bu işlemin çalışması için uygulamanın sudo yetkisiyle çalışması gerekir
            cmd = ['sudo', 'systemctl', action, service_name]
            subprocess.check_call(cmd)
            return True, f"Service {service_name} {action}ed successfully"
        except subprocess.CalledProcessError as e:
            return False, str(e)

    # --- MOCK DATA METHODS FOR MACOS DEV ---
    @staticmethod
    def _get_mock_services():
        """macOS geliştirmesi için sahte servis listesi."""
        statuses = ['running', 'stopped', 'failed', 'running', 'running', 'exited']
        services = [
            {'name': 'nginx.service', 'description': 'A high performance web server and a reverse proxy server'},
            {'name': 'postgresql.service', 'description': 'PostgreSQL RDBMS'},
            {'name': 'docker.service', 'description': 'Docker Application Container Engine'},
            {'name': 'ssh.service', 'description': 'OpenBSD Secure Shell server'},
            {'name': 'cron.service', 'description': 'Regular background program processing daemon'},
            {'name': 'networking.service', 'description': 'Raise network interfaces'},
            {'name': 'firewalld.service', 'description': 'firewalld - dynamic firewall daemon'},
            {'name': 'redis.service', 'description': 'Redis persistent key-value database'},
        ]
        
        # Rastgelelik ekle ama tutarlı olsun (Session boyunca sabit kalsın istersen random seed kullanabilirsin ama şimdilik her çağrıda değişmesin, 
        # sadece status'leri random atayalım demo için)
        results = []
        for i, s in enumerate(services):
            # Basit bir deterministic status ataması (demo için sabit kalması daha iyi UI test ederken)
            # ama canlı hissi vermek için refresh'te değişmesi istenebilir. Şimdilik sabit yapıyorum.
            stat = 'running'
            if 'nginx' in s['name']: stat = 'running'
            elif 'firewall' in s['name']: stat = 'failed'
            elif 'redis' in s['name']: stat = 'stopped'
            else: stat = 'running'
            
            results.append({
                'name': s['name'],
                'status': stat,
                'description': s['description']
            })
        return results

    @staticmethod
    def _get_mock_logs(service_name):
        lines = []
        timestamp = time.strftime("%b %d %H:%M:%S")
        host = "ubuntu-server"
        process = service_name.replace('.service', '')
        
        reasons = [
            "Started " + service_name,
            "Listening on port 80",
            "Connection received from 192.168.1.105",
            "Processing request /api/v1/data",
            "Error: Connection timed out",
            "Configuration loaded successfully",
            "Worker process started",
            "Stopping " + service_name
        ]
        
        for i in range(20):
            msg = random.choice(reasons)
            lines.append(f"{timestamp} {host} {process}[{random.randint(1000,9999)}]: {msg}")
            
        return "\n".join(lines)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def api_stats():
    return jsonify(ServiceManager.get_system_stats())

@app.route('/api/services')
def api_services():
    return jsonify(ServiceManager.get_all_services())

@app.route('/api/services/<path:service_name>/logs')
def api_service_logs(service_name):
    logs = ServiceManager.get_service_logs(service_name)
    return jsonify({'logs': logs})

@app.route('/api/services/<service_name>/control', methods=['POST'])
def api_control_service(service_name):
    data = request.json
    action = data.get('action')
    success, message = ServiceManager.control_service(service_name, action)
    if success:
        return jsonify({'status': 'success', 'message': message})
    else:
        return jsonify({'status': 'error', 'message': message}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5001)
