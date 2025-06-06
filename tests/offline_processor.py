import os
import datetime
import subprocess
import csv
import re
import math
from edgeimpulse_audio import AudioFileProcessor

# Ruta del modelo
MODEL_PATH = os.path.expanduser("~/coding/noise-offender-monitor/models/modelfile.eim")

def log_message(message):
    print(f"{datetime.datetime.now()} - {message}")

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

def process_audio_sample_lowpass(input_file, output_file):
    command = [
        "sox", input_file, output_file, 
        "lowpass", "1600", 
        "compand", "0.1,1", "6:-70,-60,-10", "-1", "-90", "0.2",
        "norm", "-3"
    ]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log_message(f"Processed and saved: {output_file}")

def save_to_csv(records, output_file):
    if not records:
        log_message("No records to save.")
        return

    file_exists = os.path.isfile(output_file)
    
    with open(output_file, "a", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=records[0].keys())
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerows(records)

def process_audio_files(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    true_dir = os.path.join(output_dir, "True")
    false_dir = os.path.join(output_dir, "False")
    os.makedirs(true_dir, exist_ok=True)
    os.makedirs(false_dir, exist_ok=True)

    records = []
    csv_file = os.path.join(os.getcwd(), "audio_analysis_results.csv")

    for audio_file in os.listdir(input_dir):
        if not audio_file.endswith((".mp3", ".wav")):
            continue

        input_file = os.path.join(input_dir, audio_file)

        # Convert MP3 to WAV if needed
        is_temp_wav = False
        wav_file = input_file
        if input_file.endswith(".mp3"):
            wav_file = "/tmp/tmp_audio.wav"
            result = subprocess.run(["ffmpeg", "-y", "-i", input_file, "-acodec", "pcm_s16le", wav_file],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if not os.path.exists(wav_file):
                log_message(f"Error converting {input_file} to WAV. Skipping.")
                continue
            is_temp_wav = True

        try:
            features = extract_audio_features(wav_file)
            label, score = classify_audio(MODEL_PATH, wav_file)
        except Exception as e:
            log_message(f"Error processing {wav_file}: {e}")
            if is_temp_wav and os.path.exists(wav_file):
                os.remove(wav_file)
            continue

        features["Label"] = label
        features["Score"] = score
        features["File"] = input_file
        records.append(features)

        # Nombre de salida con extensión .wav
        output_name = os.path.splitext(audio_file)[0] + ".wav"
        out_path = os.path.join(true_dir if label in ["One", "One-debil", "One-hifreq"] else false_dir, output_name)

        process_audio_sample_lowpass(wav_file, out_path)

        # Elimina WAV temporal si fue creado desde MP3
        if is_temp_wav and os.path.exists(wav_file):
            os.remove(wav_file)

    save_to_csv(records, csv_file)
    log_message("Finished processing all audio files.")

# Ejemplo de uso
process_audio_files(os.path.expanduser("~/ruido/samples"), os.path.expanduser("~/ruido/output"))
