import cv2
import numpy as np
import os
import pickle
import json
from collections import deque
from datetime import datetime
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import warnings
warnings.filterwarnings('ignore')

os.environ["QT_QPA_PLATFORM"] = "xcb"

# ============================================================
# PARTE 1: CONFIGURAÇÃO DA CENA (MESA E REDE)
# ============================================================

class SceneConfigurator:
    def __init__(self):
        self.table_corners = []      # 4 pontos da mesa
        self.net_points = []         # 2 pontos da rede
        self.calibrated = False
        
    def configure_scene(self, frame):
        print("\n" + "="*70)
        print("🎯 CONFIGURAÇÃO DA CENA")
        print("="*70)
        
        print("\n🔷 Clique nos 4 VÉRTICES da mesa (canto sup-esq, sup-dir, inf-dir, inf-esq)")
        self.table_corners = self._collect_points(frame, num_points=4, color=(0, 255, 0),
                                                   window_name="Config - Vertices da Mesa")
        
        if len(self.table_corners) != 4:
            h, w = frame.shape[:2]
            self.table_corners = [(0, 0), (w, 0), (w, h), (0, h)]
        
        print("\n🔴 Clique nos 2 pontos da rede (esquerda e direita)")
        self.net_points = self._collect_points(frame, num_points=2, color=(0, 0, 255),
                                                window_name="Config - Pontos da Rede")
        
        self.calibrated = True
        self._visualize_configuration(frame)
        return True
    
    def _collect_points(self, frame, num_points, color, window_name):
        points = []
        cv2.namedWindow(window_name)
        cv2.imshow(window_name, frame)
        cv2.waitKey(1)
        
        def mouse_callback(event, x, y, flags, param):
            nonlocal points
            if event == cv2.EVENT_LBUTTONDOWN and len(points) < num_points:
                points.append((x, y))
                display = frame.copy()
                for i, pt in enumerate(points):
                    cv2.circle(display, pt, 8, color, -1)
                    cv2.putText(display, f"{i+1}", (pt[0]+10, pt[1]-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                if len(points) > 1:
                    for i in range(len(points)-1):
                        cv2.line(display, points[i], points[i+1], color, 3)
                cv2.putText(display, f"Pontos: {len(points)}/{num_points} | ENTER=ok", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
                cv2.imshow(window_name, display)
                print(f"   Ponto {len(points)}: ({x}, {y})")
        
        cv2.setMouseCallback(window_name, mouse_callback)
        
        while True:
            key = cv2.waitKey(10) & 0xFF
            if key == 13 and len(points) == num_points:
                break
            elif key == 27:
                break
            elif key == ord('q'):
                cv2.destroyAllWindows()
                exit()
        
        cv2.destroyWindow(window_name)
        return points
    
    def _visualize_configuration(self, frame):
        vis = frame.copy()
        if len(self.table_corners) == 4:
            pts = np.array(self.table_corners, np.int32)
            cv2.polylines(vis, [pts], True, (0, 255, 0), 3)
            for i, pt in enumerate(self.table_corners):
                cv2.circle(vis, pt, 8, (0, 255, 0), -1)
                cv2.putText(vis, f"M{i+1}", (pt[0]+10, pt[1]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        if len(self.net_points) == 2:
            cv2.line(vis, self.net_points[0], self.net_points[1], (0, 0, 255), 4)
            for pt in self.net_points:
                cv2.circle(vis, pt, 8, (0, 0, 255), -1)
                cv2.putText(vis, f"Rede", (pt[0]+10, pt[1]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        cv2.putText(vis, "CONFIGURACAO CONCLUIDA - Pressione ENTER", (10, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.imshow("Cena Configurada", vis)
        cv2.waitKey(0)
        cv2.destroyWindow("Cena Configurada")
    
    def get_table_mask(self, frame_shape):
        mask = np.zeros(frame_shape[:2], dtype=np.uint8)
        if len(self.table_corners) == 4:
            pts = np.array(self.table_corners, np.int32)
            cv2.fillPoly(mask, [pts], 255)
        else:
            mask[:] = 255
        return mask
    
    def draw_scene(self, frame):
        result = frame.copy()
        if len(self.table_corners) == 4:
            pts = np.array(self.table_corners, np.int32)
            cv2.polylines(result, [pts], True, (0, 255, 0), 2)
        if len(self.net_points) == 2:
            cv2.line(result, self.net_points[0], self.net_points[1], (0, 0, 255), 3)
        return result
    
    def transform_to_table_view(self, point):
        """Converte ponto da câmera para vista superior da mesa (proporção correta)"""
        if len(self.table_corners) != 4:
            return point
        
        # Dimensões oficiais da mesa: 274cm x 152.5cm
        # Vamos usar uma imagem de 800 x 445 pixels (proporção 1.8:1)
        table_width = 800
        table_height = int(800 * (152.5 / 274))  # ~445 pixels
        
        src_pts = np.array(self.table_corners, dtype=np.float32)
        dst_pts = np.array([
            [0, 0],
            [table_width, 0],
            [table_width, table_height],
            [0, table_height]
        ], dtype=np.float32)
        
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        point_array = np.array([[[float(point[0]), float(point[1])]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(point_array, M)
        return (int(transformed[0][0][0]), int(transformed[0][0][1]), table_width, table_height)


# ============================================================
# PARTE 2: EXTRATOR DE FEATURES
# ============================================================

class FeatureExtractor:
    def __init__(self, window_frames=3, neighbor_size=7):
        self.window_frames = window_frames
        self.neighbor_size = neighbor_size
        self.total_frames = 2 * window_frames + 1
        
    def extract_patch(self, image, center, size):
        h, w = image.shape[:2]
        x, y = center
        s = size // 2
        x1, x2 = max(0, x - s), min(w, x + s + 1)
        y1, y2 = max(0, y - s), min(h, y + s + 1)
        patch = image[y1:y2, x1:x2]
        if patch.size != size * size:
            patch = cv2.resize(patch, (size, size))
        return patch.flatten()
    
    def extract_features_for_point(self, frames, masks, center):
        features = []
        half_window = self.window_frames
        frame_idx = half_window
        
        for offset in range(-half_window, half_window + 1):
            idx = frame_idx + offset
            if 0 <= idx < len(frames):
                frame = frames[idx]
                mask = masks[idx]
                img_patch = self.extract_patch(frame, center, self.neighbor_size)
                mask_patch = self.extract_patch(mask, center, self.neighbor_size)
                features.extend(img_patch)
                features.extend(mask_patch)
            else:
                patch_size = self.neighbor_size * self.neighbor_size
                features.extend([0] * patch_size * 2)
        return features


# ============================================================
# PARTE 3: COLETOR DE DADOS
# ============================================================

class DataCollector:
    def __init__(self, window_frames=3, neighbor_size=7):
        self.window_frames = window_frames
        self.neighbor_size = neighbor_size
        self.feature_extractor = FeatureExtractor(window_frames, neighbor_size)
        self.training_data = []
        
    def collect_from_video(self, video_path, scene_config, num_samples=30):
        cap = cv2.VideoCapture(video_path)
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        frame_buffer = deque(maxlen=2*self.window_frames + 1)
        mask_buffer = deque(maxlen=2*self.window_frames + 1)
        
        bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=50, varThreshold=25)
        table_mask = scene_config.get_table_mask((height, width))
        
        print("\n" + "="*70)
        print(f"📸 COLETA DE DADOS - {num_samples} amostras")
        print("="*70)
        print("CLIQUE na bolinha + ENTER = POSITIVO")
        print("ESC = NEGATIVO")
        print("="*70)
        
        frame_num = 0
        collected = 0
        negatives = 0
        
        while len(frame_buffer) < 2*self.window_frames + 1 and frame_num < total_frames:
            ret, frame = cap.read()
            if not ret:
                break
            masked = cv2.bitwise_and(frame, frame, mask=table_mask)
            fgmask = bg_subtractor.apply(masked)
            fgmask = cv2.medianBlur(fgmask, 5)
            fgmask = cv2.dilate(fgmask, None, iterations=2)
            frame_buffer.append(frame)
            mask_buffer.append(fgmask)
            frame_num += 1
        
        while collected < num_samples and frame_num < total_frames:
            central_frame = list(frame_buffer)[self.window_frames]
            central_mask = list(mask_buffer)[self.window_frames]
            
            contours, _ = cv2.findContours(central_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            candidates = []
            for c in contours:
                area = cv2.contourArea(c)
                if 10 < area < 300:
                    x, y, w, h = cv2.boundingRect(c)
                    candidates.append((x + w//2, y + h//2, area))
            
            display = scene_config.draw_scene(central_frame)
            for cx, cy, area in candidates:
                cv2.circle(display, (cx, cy), 8, (255, 0, 0), 2)
                cv2.putText(display, f"{area}", (cx+5, cy-5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
            
            cv2.putText(display, f"Coletados: {collected}/{num_samples} | Neg: {negatives}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(display, "Clique na BOLA + ENTER | ESC = negativo", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            cv2.imshow("Coleta", display)
            
            clicked = None
            def mouse_cb(event, x, y, flags, param):
                nonlocal clicked
                if event == cv2.EVENT_LBUTTONDOWN:
                    min_dist = 30
                    for cx, cy, area in candidates:
                        if abs(x - cx) < min_dist and abs(y - cy) < min_dist:
                            clicked = (cx, cy)
                            break
            
            cv2.setMouseCallback("Coleta", mouse_cb)
            
            decision = None
            while decision is None:
                temp = display.copy()
                if clicked:
                    cv2.circle(temp, clicked, 10, (0, 255, 0), 2)
                    cv2.putText(temp, "BOLA", (clicked[0]-20, clicked[1]-10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                cv2.imshow("Coleta", temp)
                
                key = cv2.waitKey(10) & 0xFF
                if key == 13 and clicked:
                    decision = "positive"
                elif key == 27:
                    decision = "negative"
                elif key == ord('q'):
                    cap.release()
                    cv2.destroyAllWindows()
                    return False
            
            if decision == "positive":
                features = self.feature_extractor.extract_features_for_point(
                    list(frame_buffer), list(mask_buffer), clicked)
                self.training_data.append((features, 1))
                collected += 1
                print(f"   ✅ {collected}/{num_samples} - POSITIVO")
            else:
                if candidates:
                    cx, cy, _ = candidates[0]
                    features = self.feature_extractor.extract_features_for_point(
                        list(frame_buffer), list(mask_buffer), (cx, cy))
                    self.training_data.append((features, 0))
                    negatives += 1
                    print(f"   ⚠️ NEGATIVO ({negatives})")
            
            ret, frame = cap.read()
            if not ret:
                break
            
            masked = cv2.bitwise_and(frame, frame, mask=table_mask)
            fgmask = bg_subtractor.apply(masked)
            fgmask = cv2.medianBlur(fgmask, 5)
            fgmask = cv2.dilate(fgmask, None, iterations=2)
            
            frame_buffer.append(frame)
            mask_buffer.append(fgmask)
            frame_num += 1
            clicked = None
        
        cap.release()
        cv2.destroyAllWindows()
        
        pos = sum(1 for _, l in self.training_data if l == 1)
        neg = sum(1 for _, l in self.training_data if l == 0)
        print(f"\n📊 Coleta: {pos} positivos, {neg} negativos")
        
        return len(self.training_data) > 0
    
    def save_data(self, path):
        with open(path, 'wb') as f:
            pickle.dump(self.training_data, f)
        print(f"💾 Dados salvos: {path}")
    
    def load_data(self, path):
        if os.path.exists(path):
            with open(path, 'rb') as f:
                self.training_data = pickle.load(f)
            print(f"📂 Carregados {len(self.training_data)} dados")
            return True
        return False


# ============================================================
# PARTE 4: CLASSIFICADOR
# ============================================================

class BallClassifier:
    def __init__(self):
        self.model = None
        self.scaler = None
        
    def train(self, training_data):
        X = np.array([item[0] for item in training_data])
        y = np.array([item[1] for item in training_data])
        
        print(f"\n🚀 TREINANDO CLASSIFICADOR")
        print(f"   Amostras: {len(X)}")
        print(f"   Features: {X.shape[1]}")
        print(f"   Positivos: {np.sum(y==1)}")
        print(f"   Negativos: {np.sum(y==0)}")
        
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        X_train, X_val, y_train, y_val = train_test_split(X_scaled, y, test_size=0.2, random_state=42, stratify=y)
        
        self.model = RandomForestClassifier(n_estimators=100, max_depth=15, random_state=42)
        self.model.fit(X_train, y_train)
        
        train_acc = self.model.score(X_train, y_train)
        val_acc = self.model.score(X_val, y_val)
        
        print(f"\n📈 RESULTADOS:")
        print(f"   Acurácia treino: {train_acc:.2%}")
        print(f"   Acurácia validação: {val_acc:.2%}")
        
        y_pred = self.model.predict(X_val)
        print(f"\n   Relatório (validação):")
        print(classification_report(y_val, y_pred, target_names=['NÃO-BOLA', 'BOLA']))
        
        return val_acc
    
    def save(self, path):
        with open(path, 'wb') as f:
            pickle.dump({'model': self.model, 'scaler': self.scaler}, f)
        print(f"💾 Modelo salvo: {path}")
    
    def load(self, path):
        if os.path.exists(path):
            with open(path, 'rb') as f:
                data = pickle.load(f)
                self.model = data['model']
                self.scaler = data['scaler']
            return True
        return False
    
    def predict(self, features):
        if self.model is None:
            return 0, 0.0
        features_scaled = self.scaler.transform([features])
        prob = self.model.predict_proba(features_scaled)[0][1]
        return 1 if prob > 0.5 else 0, prob


# ============================================================
# PARTE 5: PROCESSADOR COM TRÊS JANELAS (MESA PROPORCIONAL - CORRIGIDO)
# ============================================================

class VideoProcessor:
    def __init__(self, classifier, feature_extractor, scene_config):
        self.classifier = classifier
        self.feature_extractor = feature_extractor
        self.scene_config = scene_config
        self.bounces = []           # Lista COMPLETA de pontos de toque
        self.bounce_times = []      # Lista de tempos (frames) de cada toque
        self.last_bounce_side = None
        self.last_bounce_frame = -100  # Último frame com toque registrado
        self.min_frames_between_bounces = 30  # ~1 segundo (assumindo 30fps)
        
        # Dimensões da mesa
        self.table_width = int(800 * (152.5 / 274))
        self.table_height = 800
        
        self.perspective_matrix = None
        self._calculate_perspective_matrix()
    
    def get_bounce_side(self, point):
        """Retorna em qual lado da mesa ocorreu o toque"""
        x, y = point
        net_y = self.table_height // 2
        return 'left' if y < net_y else 'right'
    
    def is_valid_bounce(self, point, current_frame):
        """
        Verifica se o toque é válido:
        - Se o lado mudou (passou pela rede) -> ACEITA
        - Se é mesmo lado, mas passou tempo suficiente (> 1 segundo) -> ACEITA
        - Se é mesmo lado e muito próximo no tempo -> IGNORA
        """
        current_side = self.get_bounce_side(point)
        time_since_last = current_frame - self.last_bounce_frame
        
        # Primeiro toque
        if self.last_bounce_side is None:
            self.last_bounce_side = current_side
            self.last_bounce_frame = current_frame
            return True
        
        # Mudou de lado (passou pela rede) -> ACEITA
        if current_side != self.last_bounce_side:
            self.last_bounce_side = current_side
            self.last_bounce_frame = current_frame
            return True
        
        # Mesmo lado, mas passou tempo suficiente -> ACEITA
        if time_since_last >= self.min_frames_between_bounces:
            self.last_bounce_side = current_side
            self.last_bounce_frame = current_frame
            return True
        
        # Mesmo lado e muito próximo -> IGNORA
        return False
    
    def _calculate_perspective_matrix(self):
        """Pré-calcula a matriz de transformação de perspectiva"""
        if len(self.scene_config.table_corners) == 4:
            src_pts = np.array(self.scene_config.table_corners, dtype=np.float32)
            dst_pts = np.array([
                [0, 0],
                [self.table_width, 0],
                [self.table_width, self.table_height],
                [0, self.table_height]
            ], dtype=np.float32)
            self.perspective_matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
            print(f"✅ Matriz de perspectiva calculada: {self.table_width}x{self.table_height}")
    
    def create_table_display(self):
        """Cria visualização da mesa - APENAS mesa, rede e bolinhas"""
        # Cria imagem da mesa
        table_img = np.zeros((self.table_height, self.table_width, 3), dtype=np.uint8)
        
        # Fundo da mesa (verde)
        table_img[:, :] = (34, 139, 34)
        
        # Bordas brancas
        cv2.rectangle(table_img, (0, 0), (self.table_width-1, self.table_height-1), (255, 255, 255), 2)
        
        # Rede (linha branca no meio)
        net_y = self.table_height // 2
        cv2.line(table_img, (0, net_y), (self.table_width, net_y), (255, 255, 255), 3)
        
        # Desenha as bolinhas (amarelo para antigas, vermelho para recentes)
        total = len(self.bounces)
        for i, (x, y) in enumerate(self.bounces):
            if 0 <= x < self.table_width and 0 <= y < self.table_height:
                # Quanto mais recente, mais vermelho
                progress = i / total if total > 0 else 1
                r = 255
                g = int(255 * (1 - progress))
                b = 0
                color = (b, g, r)
                radius = 4 if progress > 0.8 else 2
                cv2.circle(table_img, (x, y), radius, color, -1)
        
        return table_img
    
    def transform_point_to_table(self, point):
        """Converte ponto da câmera para coordenadas na vista superior"""
        if self.perspective_matrix is None:
            return None
        
        point_array = np.array([[[float(point[0]), float(point[1])]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(point_array, self.perspective_matrix)
        x = int(transformed[0][0][0])
        y = int(transformed[0][0][1])
        
        if 0 <= x < self.table_width and 0 <= y < self.table_height:
            return (x, y)
        return None
    
    def process_video(self, video_path, output_path="output_final.mp4"):
        cap = cv2.VideoCapture(video_path)
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
        
        bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=50, varThreshold=25)
        table_mask = self.scene_config.get_table_mask((height, width))  # <-- DEFINIDO AQUI
        
        frame_buffer = deque(maxlen=2*self.feature_extractor.window_frames + 1)
        mask_buffer = deque(maxlen=2*self.feature_extractor.window_frames + 1)
        
        frame_num = 0
        detections = 0
        
        # Preenche buffers
        while len(frame_buffer) < 2*self.feature_extractor.window_frames + 1 and frame_num < total_frames:
            ret, frame = cap.read()
            if not ret:
                break
            masked = cv2.bitwise_and(frame, frame, mask=table_mask)
            fgmask = bg_subtractor.apply(masked)
            fgmask = cv2.medianBlur(fgmask, 5)
            fgmask = cv2.dilate(fgmask, None, iterations=2)
            frame_buffer.append(frame)
            mask_buffer.append(fgmask)
            frame_num += 1
        
        print("\n🎥 Processando vídeo...")
        
        # Cria janelas
        cv2.namedWindow("1. Deteccao", cv2.WINDOW_NORMAL)
        cv2.namedWindow("2. Mascara de Movimento", cv2.WINDOW_NORMAL)
        cv2.namedWindow("3. Mesa - Vista Superior", cv2.WINDOW_NORMAL)
        
        cv2.resizeWindow("2. Mascara de Movimento", 400, 300)
        cv2.resizeWindow("3. Mesa - Vista Superior", self.table_width, self.table_height)
        
        while frame_num < total_frames:
            central_frame = list(frame_buffer)[self.feature_extractor.window_frames]
            central_mask = list(mask_buffer)[self.feature_extractor.window_frames]
            
            # Encontra candidatos
            contours, _ = cv2.findContours(central_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            best_ball = None
            best_prob = 0
            best_center = None
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if 10 < area < 300:
                    x, y, w, h = cv2.boundingRect(contour)
                    cx, cy = x + w//2, y + h//2
                    
                    features = self.feature_extractor.extract_features_for_point(
                        list(frame_buffer), list(mask_buffer), (cx, cy))
                    
                    _, prob = self.classifier.predict(features)
                    
                    if prob > best_prob:
                        best_prob = prob
                        best_ball = contour
                        best_center = (cx, cy)
            
            # JANELA 1: Detecção
            display = self.scene_config.draw_scene(central_frame)
            
            if best_ball is not None and best_prob > 0.6:
                detections += 1
                x, y, w, h = cv2.boundingRect(best_ball)
                cv2.rectangle(display, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.circle(display, best_center, 5, (0, 0, 255), -1)
                cv2.putText(display, f"BOLA ({best_prob:.0%})", (x, y-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                # CORREÇÃO: table_mask já está definida no escopo superior
                if table_mask[best_center[1], best_center[0]] == 255:
                    table_point = self.transform_point_to_table(best_center)
                    if table_point is not None:
                        # PASSA O FRAME ATUAL para validação
                        if self.is_valid_bounce(table_point, frame_num):
                            self.bounces.append(table_point)
                            self.bounce_times.append(frame_num)
                            print(f"   ✅ Toque registrado: lado {self.last_bounce_side} no frame {frame_num}")
                        else:
                            print(f"   ⏭️ Toque ignorado (mesmo lado, muito próximo: frame {frame_num})")
            
            cv2.putText(display, f"Frame: {frame_num} | Detecções: {detections}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            cv2.imshow("1. Deteccao", display)
            out.write(display)
            
            # JANELA 2: Máscara de movimento
            mask_display = cv2.cvtColor(central_mask, cv2.COLOR_GRAY2BGR)
            cv2.putText(mask_display, "Mascara de Movimento", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            if best_ball is not None:
                x, y, w, h = cv2.boundingRect(best_ball)
                cv2.rectangle(mask_display, (x, y), (x+w, y+h), (0, 0, 255), 2)
            cv2.imshow("2. Mascara de Movimento", mask_display)
            
            # JANELA 3: Mesa com histórico
            table_display = self.create_table_display()
            cv2.imshow("3. Mesa - Vista Superior", table_display)
            
            # Avança
            ret, frame = cap.read()
            if not ret:
                break
            
            masked = cv2.bitwise_and(frame, frame, mask=table_mask)
            fgmask = bg_subtractor.apply(masked)
            fgmask = cv2.medianBlur(fgmask, 5)
            fgmask = cv2.dilate(fgmask, None, iterations=2)
            
            frame_buffer.append(frame)
            mask_buffer.append(fgmask)
            frame_num += 1
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                cv2.imwrite("mesa_historico.png", table_display)
                print("📸 Screenshot da mesa salvo!")
        
        cap.release()
        out.release()
        cv2.destroyAllWindows()
        
        print(f"\n✅ Processado: {frame_num} frames")
        print(f"✅ Detecções: {detections}")
        print(f"✅ Toques na mesa: {len(self.bounces)}")

        self.save_detailed_history()
        
        return self.bounces

    def save_detailed_history(self, filename="historico_detalhado.png"):
        # Cria a visualização da mesa (igual à janela)
        table_display = self.create_table_display()
        
        # Salva a imagem
        cv2.imwrite(filename, table_display)
        print(f"💾 Histórico salvo em: {filename}")

# ============================================================
# PARTE 6: PIPELINE PRINCIPAL
# ============================================================

def main():
    video_path = "examples/example.mp4"
    config_path = "scene_config.pkl"
    data_path = "training_data.pkl"
    model_path = "ball_model.pkl"
    
    # PARÂMETROS CONFIGURÁVEIS
    WINDOW_FRAMES = 3      # Frames antes/depois (total = 7)
    NEIGHBOR_SIZE = 7      # Tamanho da vizinhança (7x7)
    NUM_SAMPLES = 30       # Número de amostras para coletar
    
    if not os.path.exists(video_path):
        print(f"❌ Vídeo não encontrado: {video_path}")
        return
    
    # 1. Configura cena
    print("\n" + "="*70)
    print("🎯 SISTEMA DE DETECÇÃO DE BOLINHA")
    print("="*70)
    
    scene_config = SceneConfigurator()
    
    if os.path.exists(config_path):
        reconfigure = input("Reconfigurar cena? (s/n): ").lower()
        if reconfigure != 's':
            with open(config_path, 'rb') as f:
                data = pickle.load(f)
                scene_config.table_corners = data.get('table_corners', [])
                scene_config.net_points = data.get('net_points', [])
                scene_config.calibrated = True
            print("✅ Configuração carregada")
    
    if not scene_config.calibrated:
        cap = cv2.VideoCapture(video_path)
        ret, frame = cap.read()
        cap.release()
        if ret:
            scene_config.configure_scene(frame)
            with open(config_path, 'wb') as f:
                pickle.dump({
                    'table_corners': scene_config.table_corners,
                    'net_points': scene_config.net_points
                }, f)
            print("💾 Configuração salva")
    
    # 2. Coleta dados
    collector = DataCollector(window_frames=WINDOW_FRAMES, neighbor_size=NEIGHBOR_SIZE)
    
    if os.path.exists(data_path):
        use_existing = input(f"Usar dados existentes ({data_path})? (s/n): ").lower()
        if use_existing == 's':
            collector.load_data(data_path)
    
    if len(collector.training_data) == 0:
        collector.collect_from_video(video_path, scene_config, num_samples=NUM_SAMPLES)
        collector.save_data(data_path)
    
    # 3. Treina modelo
    classifier = BallClassifier()
    
    if os.path.exists(model_path):
        use_existing = input(f"Usar modelo existente ({model_path})? (s/n): ").lower()
        if use_existing == 's':
            classifier.load(model_path)
    
    if classifier.model is None:
        classifier.train(collector.training_data)
        classifier.save(model_path)
    
    # 4. Processa vídeo
    feature_extractor = FeatureExtractor(window_frames=WINDOW_FRAMES, neighbor_size=NEIGHBOR_SIZE)
    processor = VideoProcessor(classifier, feature_extractor, scene_config)
    
    processor.process_video(video_path, output_path="./outputs/output_final.mp4")
    
    print("\n✅ PIPELINE CONCLUÍDO!")
    print(f"📹 Vídeo processado: ./outputs/output_final.mp4")
    print(f"📊 Toques na mesa: {len(processor.bounces)}")


if __name__ == "__main__":
    main()