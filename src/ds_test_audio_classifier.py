import cv2
import numpy as np
import os
import subprocess
import librosa
import pickle

os.environ["QT_QPA_PLATFORM"] = "xcb"

class AudioTester:
    def __init__(self, model_file):
        with open(model_file, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.classes = data.get('classes', ['R', 'M', 'N'])
        
        self.audio_data = None
        self.sr = None
        self.fps = None
        
    def load_audio_from_video(self, video_path):
        audio_path = video_path.replace('.mp4', '_audio.wav')
        
        if not os.path.exists(audio_path):
            cmd = f"ffmpeg -i {video_path} -ab 160k -ac 1 -ar 22050 {audio_path} -y"
            subprocess.run(cmd, shell=True, capture_output=True)
        
        if os.path.exists(audio_path):
            self.audio_data, self.sr = librosa.load(audio_path, sr=22050)
            return True
        return False
    
    def extract_audio_window(self, frame_num, fps, window_ms=150):
        if self.audio_data is None:
            return None
        
        samples_per_frame = self.sr // fps
        center_sample = frame_num * samples_per_frame
        
        window_samples = int(window_ms * self.sr / 1000)
        start = max(0, center_sample - window_samples // 2)
        end = min(len(self.audio_data), center_sample + window_samples // 2)
        
        if end > start:
            window = self.audio_data[start:end]
            if len(window) < window_samples:
                window = np.pad(window, (0, window_samples - len(window)))
            return window
        return None
    
    def extract_features(self, audio_window):
        if audio_window is None or len(audio_window) < 100:
            return None
        
        try:
            mfcc = librosa.feature.mfcc(y=audio_window, sr=self.sr, n_mfcc=13)
            mfcc_mean = np.mean(mfcc, axis=1)
            mfcc_std = np.std(mfcc, axis=1)
        except:
            mfcc_mean = np.zeros(13)
            mfcc_std = np.zeros(13)
        
        rms = np.sqrt(np.mean(audio_window**2))
        zcr = np.mean(librosa.feature.zero_crossing_rate(audio_window))
        
        try:
            fft = np.abs(np.fft.rfft(audio_window))
            freqs = np.fft.rfftfreq(len(audio_window), 1/self.sr)
            if len(fft) > 1:
                peak_freq = freqs[np.argmax(fft[1:]) + 1] if len(fft) > 1 else 0
            else:
                peak_freq = 0
        except:
            peak_freq = 0
        
        features = list(mfcc_mean) + list(mfcc_std) + [rms, zcr, peak_freq]
        return features
    
    def predict_frame(self, frame_num, fps):
        window = self.extract_audio_window(frame_num, fps, window_ms=150)
        features = self.extract_features(window)
        
        if features is None:
            return 'N', 0.0
        
        features = np.array(features).reshape(1, -1)
        proba = self.model.predict_proba(features)[0]
        pred_idx = np.argmax(proba)
        
        return self.classes[pred_idx], proba[pred_idx]


def main():
    video_path = "examples/example.mp4"
    model_file = "audio_classifier.pkl"
    
    if not os.path.exists(video_path):
        print(f"❌ Video nao encontrado: {video_path}")
        return
    
    if not os.path.exists(model_file):
        print(f"❌ Modelo nao encontrado: {model_file}")
        print("   Primeiro treine o modelo (opção 2)")
        return
    
    print("🎥 TESTANDO CLASSIFICADOR DE ÁUDIO EM TEMPO REAL")
    print("="*60)
    
    # Carrega modelo
    tester = AudioTester(model_file)
    
    # Carrega áudio
    if not tester.load_audio_from_video(video_path):
        print("❌ Não foi possível carregar áudio")
        return
    
    # Abre vídeo
    cap = cv2.VideoCapture(video_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"📹 Vídeo: {frame_count} frames, {fps} fps")
    print("\n🎮 Pressione 'q' para sair")
    print("   O classificador vai mostrar em tempo real:")
    print("   🔴 VERMELHO = REBATIDA (raquete)")
    print("   🟡 AMARELO = MESA")
    print("   🟢 VERDE = NADA")
    print("="*60)
    
    frame_num = 0
    history = []  # Para suavização
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Prediz a cada 5 frames (para não ficar muito pesado)
        if frame_num % 5 == 0:
            pred_class, confidence = tester.predict_frame(frame_num, fps)
            history.append((pred_class, confidence))
            if len(history) > 3:
                history.pop(0)
        
        # Suavização: usa a classe mais comum nos últimos 3 frames
        if history:
            from collections import Counter
            most_common = Counter([h[0] for h in history]).most_common(1)[0][0]
            avg_conf = np.mean([h[1] for h in history])
            pred_class = most_common
            confidence = avg_conf
        else:
            pred_class, confidence = 'N', 0.0
        
        # Define cor e label
        if pred_class == 'R':
            color = (0, 0, 255)  # Vermelho
            label = "RAQUETE"
            y_pos = 100
        elif pred_class == 'M':
            color = (0, 255, 255)  # Amarelo
            label = "MESA"
            y_pos = 100
        else:
            color = (0, 255, 0)  # Verde
            label = "NADA"
            y_pos = 100
        
        # Desenha no frame
        # Quadro principal
        cv2.rectangle(frame, (10, y_pos - 25), (250, y_pos + 15), color, -1)
        cv2.putText(frame, f"CLASSIFICACAO: {label}", (15, y_pos),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        
        # Barra de confiança
        bar_width = int(confidence * 200)
        cv2.rectangle(frame, (15, y_pos + 20), (15 + bar_width, y_pos + 30), color, -1)
        cv2.putText(frame, f"Confianca: {confidence:.1%}", (15, y_pos + 45),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # Informações do frame
        cv2.putText(frame, f"Frame: {frame_num}/{frame_count}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Barra de progresso
        progress = frame_num / frame_count
        bar_width = int(progress * width)
        cv2.rectangle(frame, (0, height - 5), (bar_width, height), (0, 255, 0), -1)
        
        # Mostra
        cv2.imshow('Classificador de Audio - Tempo Real', frame)
        
        if cv2.waitKey(30) & 0xFF == ord('q'):
            break
        
        frame_num += 1
    s
    cap.release()
    cv2.destroyAllWindows()
    print("\n✅ Teste concluído!")


if __name__ == "__main__":
    main()