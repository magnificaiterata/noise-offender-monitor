#!/usr/bin/env python3

import os
import time
import datetime
import subprocess
import csv
import re
import math
import requests
import argparse
from edgeimpulse_audio import AudioFileProcessor

# Definición de rutas
LOG_DIR = "/var/log/noise-monitor/"
LOG_FILE_PATH = os.path.join(LOG_DIR, "noise-monitor.log")
RECORD_PATH = "/var/local/noise-monitor/"
AUDIO_DIR = "/var/local/noise-monitor/audio_samples/"
DETECTIONS_DIR = "/var/local/noise-monitor/detection_uploads/"
MODEL_PATH = "/usr/local/lib/noise-monitor/models/modelfile.eim"
NOISE_PROFILE_PATH = "/usr/local/lib/noise-monitor/noise.prof"
MONITOR_STATUS_FILE = "/usr/local/etc/noise-monitor/monitor_status"
ADAFRUIT_IO_PATH = "/usr/local/etc/noise-monitor/adafruit-io"
ADA_URL = ""
GDRIVE_PATH = "gdrive:noise-monitor-uploads"

# Cargar valores de Adafruit IO
def load_aio_data(aio_data_path):
    with open(aio_data_path, "r") as f:
        lines = f.readlines()
        aio_data = {}
        for line in lines:
            key, value = map(str.strip, line.split("=", 1))
            aio_data[key] = value.strip('"')
    return aio_data

aio_data = load_aio_data(ADAFRUIT_IO_PATH)
ADAFRUIT_IO_USERNAME = aio_data["ADAFRUIT_IO_USERNAME"]
ADAFRUIT_IO_KEY = aio_data["ADAFRUIT_IO_KEY"]
ADA_URL = aio_data["ADAFRUIT_IO_URL"]

def log_message(message):
    # Crear el directorio si no existe
    os.makedirs(LOG_DIR, exist_ok=True)

    with open(LOG_FILE_PATH, "a") as log_file:
        log_file.write(f"{datetime.datetime.now()} - {message}\n")


def check_monitor_status():
    try:
        with open(MONITOR_STATUS_FILE, "r") as f:
            status = f.readline().strip().lower()
            log_message(f"✅ Archivo '{MONITOR_STATUS_FILE}' abierto correctamente.")
            log_message(f"📖 Contenido leído: '{status}'")
            return status == "on"
    except FileNotFoundError:
        log_message(f"⚠️ Archivo '{MONITOR_STATUS_FILE}' no encontrado.")
        
        # Crear el directorio si no existe
        os.makedirs(os.path.dirname(MONITOR_STATUS_FILE), exist_ok=True)
        
        # Crear el archivo con estado "on"
        with open(MONITOR_STATUS_FILE, "w") as f:
            f.write("on\n")
        log_message(f"✅ Archivo '{MONITOR_STATUS_FILE}' creado con estado 'on'.")
        
        return True
    except Exception as e:
        log_message(f"❌ Error al manejar el archivo '{MONITOR_STATUS_FILE}': {e}")
        return False


def capture_audio(device, duration, output_file):
    command = [
        "ffmpeg", "-f", "alsa", "-channels", "1", "-sample_rate", "44100", "-i", device,
        "-t", str(duration), "-acodec", "libmp3lame", "-q:a", "2", output_file
    ]
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)



def convert_to_wav(input_file, output_file):
    command = ["ffmpeg", "-i", input_file, "-acodec", "pcm_s16le", output_file]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def extract_audio_features(audio_file):
    command = ["sox", audio_file, "-n", "stat"]
    result = subprocess.run(command, stderr=subprocess.PIPE, text=True)

    features = {
        "RMS Amplitude": 0.0,
        "Rough Frequency": 0.0,
        "Volume Adjustment": 0.0,
        "Maximum Amplitude": 0.0,
        "Minimum Amplitude": 0.0
    }

    rms_match = re.search(r'RMS\s*amplitude:\s*([-+]?[0-9]*\.?[0-9]+)', result.stderr)
    freq_match = re.search(r'Rough\s*frequency:\s*(\d+)', result.stderr)
    vol_match = re.search(r'Volume\s*adjustment:\s*([-+]?[0-9]*\.?[0-9]+)', result.stderr)
    max_amp_match = re.search(r'Maximum\s*amplitude:\s*([-+]?[0-9]*\.?[0-9]+)', result.stderr)
    min_amp_match = re.search(r'Minimum\s*amplitude:\s*([-+]?[0-9]*\.?[0-9]+)', result.stderr)

    if rms_match:
        features["RMS Amplitude"] = float(rms_match.group(1))
    if freq_match:
        features["Rough Frequency"] = float(freq_match.group(1))
    if vol_match:
        features["Volume Adjustment"] = float(vol_match.group(1))
    if max_amp_match:
        features["Maximum Amplitude"] = float(max_amp_match.group(1))
    if min_amp_match:
        features["Minimum Amplitude"] = float(min_amp_match.group(1))

    features["NPS_dB"] = 20 * math.log10(features["RMS Amplitude"]) + 100 if features["RMS Amplitude"] > 0 else 0
    features["Peak"] = max(abs(features["Maximum Amplitude"]), abs(features["Minimum Amplitude"]))

    now = datetime.datetime.now()
    features["DayOfWeek"] = now.strftime("%A")
    features["Hour"] = now.strftime("%H:%M")

    return features


def classify_audio(model_path, audio_file):
    processor = AudioFileProcessor(model_path)
    processor.init_model()
    best_label, best_score = processor.process_audio(audio_file)
    return best_label, best_score

def process_audio_sample(input_file, output_file, noise_profile):
    command = [
        "sox", input_file, output_file, 
        "noisered", noise_profile, "0.3", 
        "highpass", "100", "lowpass", "10000", 
        "compand", "0.3,1", "6:-70,-60,-20", "-5", "-90", "0.2",
        "norm", "-3"
    ]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log_message(f"Processed and saved: {output_file}")


def save_to_csv(record_path, records):
    # Asegurar que el directorio existe
    os.makedirs(record_path, exist_ok=True)
    
    # Buscar archivos existentes con el sufijo noise-monitor_records_
    existing_files = [f for f in os.listdir(record_path) if f.startswith("noise-monitor_records_")]
    
    if existing_files:
        # Usar el archivo más reciente encontrado
        existing_files.sort()
        record_file = existing_files[-1]
    else:
        # Crear un nuevo archivo con el formato especificado
        record_file = f"noise-monitor_records_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
    
    record_path = os.path.join(record_path, record_file)
    file_exists = os.path.isfile(record_path)
    
    with open(record_path, "a", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=records[0].keys())
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerows(records)


def post_to_adafruit(value):
    headers = {
        "Content-Type": "application/json",
        "X-AIO-Key": ADAFRUIT_IO_KEY
    }
    data = {"value": value}
    try:
        requests.post(ADA_URL, json=data, headers=headers)
    except Exception as e:
        log_message(f"Error posting to Adafruit: {e}")


def upload_to_gdrive(file_path):
    try:
        command = ["rclone", "copy", file_path, GDRIVE_PATH]
        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log_message(f"Uploaded {file_path} to Google Drive.")
    except Exception as e:
        log_message(f"Error uploading to Google Drive: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in_device", default="hw:1,0", help="Input audio device")
    parser.add_argument("--sample_interval", type=int, default=120, help="Interval between samples (s)")
    parser.add_argument("--sample_time", type=int, default=10, help="Sample duration (s)")
    parser.add_argument("--n_samples", type=int, default=3, help="Number of samples per run")
    parser.add_argument("--noise_prof", default=NOISE_PROFILE_PATH, help="Noise profile path")

    args = parser.parse_args()

    if not check_monitor_status():
        return

    os.makedirs(AUDIO_DIR, exist_ok=True)

    detected_music = True
    records = []

    concatenated_mp3_file = None

    for i in range(args.n_samples):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        mp3_file = os.path.join(AUDIO_DIR, f"{timestamp}_{i + 1:02d}.mp3")
        wav_file = mp3_file.replace(".mp3", ".wav")

        capture_audio(args.in_device, args.sample_time, mp3_file)
        convert_to_wav(mp3_file, wav_file)

        features = extract_audio_features(wav_file)
        label, score = classify_audio(MODEL_PATH, wav_file)

        os.remove(wav_file)

        features["Label"] = label
        features["Score"] = score
        features["File"] = mp3_file

        records.append(features)


        if label not in ["One", "One-debil", "One-hifreq"]:
            detected_music = False
            break

        if concatenated_mp3_file is None:
            concatenated_mp3_file = os.path.join(AUDIO_DIR, f"{timestamp}.mp3")
            subprocess.run(["ffmpeg", "-i", mp3_file, "-c", "copy", concatenated_mp3_file])
        else:
            temp_file = os.path.join(AUDIO_DIR, f"temp_{timestamp}.mp3")
            subprocess.run(["ffmpeg", "-i", f"concat:{concatenated_mp3_file}|{mp3_file}", "-c", "copy", temp_file])
            os.replace(temp_file, concatenated_mp3_file)

        if i < args.n_samples - 1:
            time.sleep(args.sample_interval)

    if detected_music and concatenated_mp3_file:
        process_detected = False
        if process_detected:
            # Procesar el archivo concatenado realce de ganancia, reducción de ruido y normalización
            processed_file = os.path.join(DETECTIONS_DIR, os.path.basename(concatenated_mp3_file))
            process_audio_sample(concatenated_mp3_file, processed_file, args.noise_prof)
        else:
            # Si no se procesa, usar el archivo concatenado directamente
            processed_file = concatenated_mp3_file

        # Subir el archivo procesado o concatenado a Google Drive
        upload_to_gdrive(processed_file)
    elif concatenated_mp3_file:
        os.remove(concatenated_mp3_file)

    save_to_csv(RECORD_PATH, records)

    avg_nps = sum(r["NPS_dB"] for r in records) / len(records) if detected_music else 0
    post_to_adafruit(avg_nps)

    log_message(f"Finished processing. Music detected: {detected_music}")


if __name__ == "__main__":
    main()