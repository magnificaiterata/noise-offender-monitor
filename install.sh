
# Este script instala el monitor de ruido en el sistema
# Crea los directorios necesarios, copia los archivos necesarios y ajusta los permisos

#!/bin/bash

# Crear directorios necesarios
mkdir -p /var/log/noise-monitor/
mkdir -p /etc/noise-monitor/
mkdir -p /var/local/noise-monitor/audio_samples/
mkdir -p /usr/local/lib/noise-monitor/models/

# Copiar el modelo y el perfil de ruido a la ubicación correcta
cp models/modelfile.eim /usr/local/lib/noise-monitor/models/
cp res/noise.prof /usr/local/lib/noise-monitor/
cp res/adafruit-io /var/local/noise-monitor/

# Crear archivo de estado del monitor si no existe
if [ ! -f /etc/noise-monitor/monitor_status ]; then
    echo "on" > /etc/noise-monitor/monitor_status
fi

# Ajustar permisos para que el usuario pueda escribir en los directorios necesarios
chmod -R 777 /var/log/noise-monitor/
chmod -R 777 /var/local/noise-monitor/
chmod -R 777 /var/local/noise-monitor/audio_samples/
chmod -R 777 /etc/noise-monitor/

echo "Instalación completada."