# Noise Offender Monitor

A real-time monitoring system designed to detect, record, and log when your neighbors' music reaches unbearable levels using a microphone and audio analysis algorithms classifies the captured sounds. The analysis results are saved in a CSV file and uploaded to Google Drive. Data is also sent to Adafruit IO.

## Requisitos

- Python 3
- ffmpeg
- sox
- rclone
- Git

## Instalación

1. Clonar el repositorio:

    ```bash
    git clone https://github.com/tu-usuario/noise-offender-monitor.git
    cd noise-offender-monitor
    ```

2. Ejecutar el script de instalación con privilegios de administrador:

    ```bash
    sudo bash install.sh
    ```

3. Instalar las dependencias de Python:

    ```bash
    pip install -r requirements.txt
    ```

## Uso

Para ejecutar el programa, usa el siguiente comando:

```bash
python3 tests/noffmon.py --in_device hw:1,0 --sample_interval 120 --sample_time 10 --n_samples 3 --noise_prof /usr/local/lib/noise-monitor/noise.prof

Argumentos
--in_device: Dispositivo de entrada de audio (por defecto: hw:1,0)
--sample_interval: Intervalo entre muestras en segundos (por defecto: 120)
--sample_time: Duración de cada muestra en segundos (por defecto: 10)
--n_samples: Número de muestras por ejecución (por defecto: 3)
--noise_prof: Ruta del perfil de ruido (por defecto: /usr/local/lib/noise-monitor/noise.prof)