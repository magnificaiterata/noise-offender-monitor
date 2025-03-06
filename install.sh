# Este script instala el monitor de ruido en el sistema
# Crea los directorios necesarios, copia los archivos necesarios y ajusta los permisos
# Agregar permisos de ejecución ---> chmod +x install.sh
# Ejecutar ---> sudo ./install.sh

#!/bin/bash

# Crear directorios necesarios
mkdir -p /var/log/noise-monitor/
mkdir -p /var/local/noise-monitor/audio_samples/
mkdir -p /var/local/noise-monitor/detection_uploads/
mkdir -p /usr/local/etc/noise-monitor/
mkdir -p /usr/local/lib/noise-monitor/models/

# Ajustar permisos para que el usuario pueda escribir en los directorios necesarios
chmod -R 777 /var/log/noise-monitor/
chmod -R 777 /var/local/noise-monitor/
chmod -R 777 /var/local/noise-monitor/audio_samples/
chmod -R 777 /var/local/noise-monitor/detection_uploads/
chmod -R 777 /usr/local/lib/noise-monitor/
chmod -R 777 /usr/local/etc/noise-monitor/

# Copiar el modelo y el perfil de ruido a la ubicación correcta
cp models/modelfile.eim /usr/local/lib/noise-monitor/models/
cp res/noise.prof /usr/local/lib/noise-monitor/
cp res/adafruit-io /usr/local/etc/noise-monitor/

# Crear archivo de estado del monitor si no existe
if [ ! -f /usr/local/etc/noise-monitor/monitor_status ]; then
    echo "on" > /usr/local/etc/noise-monitor/monitor_status
fi


echo "Instalación completada."