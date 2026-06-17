import cv2
import numpy as np
from collections import deque
import os
import pickle
import joblib
from sklearn.preprocessing import RobustScaler
from sklearn.model_selection import train_test_split
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')

os.environ["QT_QPA_PLATFORM"] = "xcb"

class SceneConfigurator:
    def __init__(self):
        self.table_corners = []
        self.net_points = []
        self.inclusion_polygon = []
        self.calibrated = False
        
    def configure_from_frame(self, frame):
        print("\n" + "="*80)
        print("🎯 CONFIGURAÇÃO DA CENA")
        print("="*80)
        
        print("\n🔷 PARTE 1: Clique nos 4 vértices da mesa (apenas referência visual)")
        self.table_corners = self._collect_points(frame, num_points=4, color=(0, 255, 0), 
                                                   window_name="Config - Mesa (Referencia)")
        
        if len(self.table_corners) != 4:
            h, w = frame.shape[:2]
            self.table_corners = [(0, 0), (w, 0), (w, h), (0, h)]
        
        print("\n🔴 PARTE 2: Clique nos 2 pontos da rede (apenas referência visual)")
        self.net_points = self._collect_points(frame, num_points=2, color=(0, 0, 255),
                                                window_name="Config - Pontos da Rede")
        
        print("\n🟢 PARTE 3: Desenhe o POLÍGONO DE INCLUSÃO (onde está o SEU jogo)")
        print("   Tudo DENTRO deste polígono será processado")
        print("   Tudo FORA será ignorado (preto)")
        self.inclusion_polygon = self._draw_inclusion_polygon(frame)
        
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
                    cv2.circle(display, pt, 6, color, -1)
                    cv2.putText(display, f"{i+1}", (pt[0]+8, pt[1]-8), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                if len(points) > 1:
                    for i in range(len(points)-1):
                        cv2.line(display, points[i], points[i+1], color, 2)
                cv2.putText(display, f"Ponto {len(points)}/{num_points} (ENTER confirma)", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
                cv2.imshow(window_name, display)
        
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
    
    def _draw_inclusion_polygon(self, frame):
        polygon = []
        window_name = "Config - Poligono de INCLUSAO (desenhe seu jogo)"
        cv2.namedWindow(window_name)
        display = frame.copy()
        cv2.putText(display, "Clique para adicionar pontos do poligono (seu jogo)", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
        cv2.putText(display, "ENTER = fechar poligono | ESC = pular (usa mesa toda)", 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,200), 1)
        cv2.putText(display, "R = reset | U = undo", 
                   (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,200), 1)
        cv2.imshow(window_name, display)
        cv2.waitKey(1)
        
        def mouse_callback(event, x, y, flags, param):
            nonlocal polygon, display
            if event == cv2.EVENT_LBUTTONDOWN:
                polygon.append((x, y))
                display = frame.copy()
                if len(polygon) > 0:
                    pts = np.array(polygon, np.int32)
                    cv2.polylines(display, [pts], False, (0, 255, 0), 2)
                    overlay = display.copy()
                    cv2.fillPoly(overlay, [pts], (0, 255, 0))
                    cv2.addWeighted(overlay, 0.3, display, 0.7, 0, display)
                    for i, pt in enumerate(polygon):
                        cv2.circle(display, pt, 5, (0, 255, 0), -1)
                        cv2.putText(display, f"{i+1}", (pt[0]+8, pt[1]-8), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                cv2.putText(display, f"Pontos: {len(polygon)} | ENTER=fechar", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
                cv2.imshow(window_name, display)
        
        cv2.setMouseCallback(window_name, mouse_callback)
        
        while True:
            key = cv2.waitKey(10) & 0xFF
            if key == 13 and len(polygon) >= 3:
                print(f"   ✅ Polígono de inclusão com {len(polygon)} pontos")
                break
            elif key == 27:
                print("   ⚠️ Nenhum polígono definido. Usando a mesa toda.")
                if len(self.table_corners) == 4:
                    polygon = self.table_corners.copy()
                else:
                    h, w = frame.shape[:2]
                    polygon = [(0, 0), (w, 0), (w, h), (0, h)]
                break
            elif key == ord('r'):
                polygon = []
                display = frame.copy()
                cv2.putText(display, "Poligono resetado. Clique para adicionar pontos.", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
                cv2.imshow(window_name, display)
                print("   Resetado.")
            elif key == ord('u'):
                if polygon:
                    polygon.pop()
                    display = frame.copy()
                    if len(polygon) > 0:
                        pts = np.array(polygon, np.int32)
                        cv2.polylines(display, [pts], False, (0, 255, 0), 2)
                        overlay = display.copy()
                        cv2.fillPoly(overlay, [pts], (0, 255, 0))
                        cv2.addWeighted(overlay, 0.3, display, 0.7, 0, display)
                        for i, pt in enumerate(polygon):
                            cv2.circle(display, pt, 5, (0, 255, 0), -1)
                    cv2.putText(display, f"Pontos: {len(polygon)} | ENTER=fechar", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
                    cv2.imshow(window_name, display)
                    print(f"   Desfeito. {len(polygon)} pontos.")
            elif key == ord('q'):
                cv2.destroyAllWindows()
                exit()
        
        cv2.destroyWindow(window_name)
        return polygon
    
    def _visualize_configuration(self, frame):
        vis = frame.copy()
        if len(self.table_corners) == 4:
            pts = np.array(self.table_corners, np.int32)
            cv2.polylines(vis, [pts], True, (0, 255, 0), 2)
        if len(self.net_points) == 2:
            cv2.line(vis, self.net_points[0], self.net_points[1], (0, 0, 255), 2)
        if len(self.inclusion_polygon) >= 3:
            pts = np.array(self.inclusion_polygon, np.int32)
            overlay = vis.copy()
            cv2.fillPoly(overlay, [pts], (0, 255, 0))
            cv2.addWeighted(overlay, 0.3, vis, 0.7, 0, vis)
            cv2.polylines(vis, [pts], True, (0, 255, 0), 3)
        
        cv2.putText(vis, "VERDE = area que sera processada (seu jogo)", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        cv2.putText(vis, "Pressione ENTER para continuar", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.imshow("Visualizacao Final", vis)
        cv2.waitKey(0)
        cv2.destroyWindow("Visualizacao Final")
    
    def apply_inclusion_mask(self, frame):
        if not self.calibrated or len(self.inclusion_polygon) < 3:
            return frame
        mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        pts = np.array(self.inclusion_polygon, np.int32)
        cv2.fillPoly(mask, [pts], 255)
        return cv2.bitwise_and(frame, frame, mask=mask)
    
    def is_point_inside(self, point):
        if len(self.inclusion_polygon) < 3:
            return True
        x, y = point
        result = cv2.pointPolygonTest(np.array(self.inclusion_polygon, np.int32), (float(x), float(y)), False)
        return result >= 0


class BallCalibrator:
    def __init__(self):
        self.training_data = []
        self.feature_names = []
        
    def extract_features(self, contour, frame_shape, original_frame):
        area = cv2.contourArea(contour)
        if area < 10:
            return None
        
        perimeter = cv2.arcLength(contour, True)
        if perimeter == 0:
            return None
        
        circularity = 4 * np.pi * area / (perimeter * perimeter)
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = w / h if h > 0 else 1
        extent = area / (w * h) if w * h > 0 else 0
        
        moments = cv2.moments(contour)
        if moments['m00'] != 0:
            hu = cv2.HuMoments(moments).flatten()
            hu = -np.sign(hu) * np.log10(np.abs(hu) + 1e-10)
        else:
            hu = np.zeros(7)
        
        cx, cy = x + w/2, y + h/2
        rel_x = cx / frame_shape[1]
        rel_y = cy / frame_shape[0]
        
        features = {
            'area': area, 
            'circularity': circularity, 
            'aspect_ratio': aspect_ratio,
            'extent': extent, 
            'rel_x': rel_x, 
            'rel_y': rel_y,
            'hu1': hu[0], 'hu2': hu[1], 'hu3': hu[2]
        }
        self.feature_names = list(features.keys())
        return list(features.values())
    
    def collect_training_data(self, video_path, scene_config, num_balls_needed=30):
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        print("\n" + "="*80)
        print(f"🎾 COLETA DE DADOS - Precisamos de {num_balls_needed} bolinhas")
        print("="*80)
        print("📌 REGRAS:")
        print("   1. Clique na BOLA e pressione ENTER -> Bola registrada")
        print("   2. TODOS os outros candidatos do frame serão NEGATIVOS")
        print("   3. ESC -> TODOS os candidatos do frame serão NEGATIVOS")
        print("   4. q -> Sair")
        print("="*80)
        
        bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=200, varThreshold=30, detectShadows=False)
        
        balls_collected = 0
        frames_processed = 0
        
        while balls_collected < num_balls_needed:
            frame_num = np.random.randint(0, total_frames)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            if not ret:
                continue
            
            frames_processed += 1
            
            masked_frame = scene_config.apply_inclusion_mask(frame)
            
            fgmask = bg_subtractor.apply(masked_frame)
            fgmask = cv2.medianBlur(fgmask, 5)
            fgmask = cv2.dilate(fgmask, None, iterations=2)
            contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            candidates = []
            for i, contour in enumerate(contours):
                features = self.extract_features(contour, frame.shape, masked_frame)
                if features:
                    x, y, w, h = cv2.boundingRect(contour)
                    candidates.append({
                        'id': i, 'bbox': (x, y, w, h), 'features': features,
                        'center': (x + w//2, y + h//2), 'area': w * h
                    })
            
            if not candidates:
                continue
            
            candidates.sort(key=lambda c: c['area'], reverse=True)
            
            window_name = f"Calibracao - {balls_collected}/{num_balls_needed} bolinhas"
            display = masked_frame.copy()
            
            if len(scene_config.inclusion_polygon) >= 3:
                pts = np.array(scene_config.inclusion_polygon, np.int32)
                cv2.polylines(display, [pts], True, (0, 255, 0), 2)
            
            for cand in candidates:
                x, y, w, h = cand['bbox']
                color = (255, 0, 0)
                cv2.rectangle(display, (x, y), (x+w, y+h), color, 2)
                cv2.putText(display, f"{cand['id']}", (x, y-5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            cv2.putText(display, f"Bolinhas: {balls_collected}/{num_balls_needed}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(display, "Clique na BOLA + ENTER | ESC = todos negativos", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            cv2.imshow(window_name, display)
            
            clicked_ball = None
            
            def mouse_callback(event, x, y, flags, param):
                nonlocal clicked_ball
                if event == cv2.EVENT_LBUTTONDOWN:
                    if scene_config.is_point_inside((x, y)):
                        min_dist = 50
                        for cand in candidates:
                            cx, cy = cand['center']
                            dist = np.sqrt((x - cx)**2 + (y - cy)**2)
                            if dist < min_dist:
                                min_dist = dist
                                clicked_ball = cand
                    else:
                        print("   ⚠️ Clique fora da área de jogo")
            
            cv2.setMouseCallback(window_name, mouse_callback)
            
            action = None
            while action is None:
                display_temp = display.copy()
                if clicked_ball:
                    x, y, w, h = clicked_ball['bbox']
                    cv2.rectangle(display_temp, (x, y), (x+w, y+h), (0, 255, 0), 3)
                    cv2.circle(display_temp, clicked_ball['center'], 5, (0, 255, 0), -1)
                    cv2.putText(display_temp, "BOLA SELECIONADA", (x, y-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                cv2.imshow(window_name, display_temp)
                
                key = cv2.waitKey(10) & 0xFF
                if key == 13:
                    if clicked_ball:
                        action = "ball"
                    else:
                        print("   ⚠️ Nenhuma bola selecionada. Clique na bola primeiro!")
                elif key == 27:
                    action = "skip"
                elif key == ord('q'):
                    cap.release()
                    cv2.destroyAllWindows()
                    return False
            
            if action == "ball":
                self.training_data.append((clicked_ball['features'], 1))
                balls_collected += 1
                print(f"   ✅ BOLA {balls_collected}/{num_balls_needed} (area={clicked_ball['area']:.0f})")
                
                neg_count = 0
                for cand in candidates:
                    if cand != clicked_ball:
                        self.training_data.append((cand['features'], 0))
                        neg_count += 1
                print(f"      ➕ {neg_count} exemplos negativos adicionados")
                
            elif action == "skip":
                for cand in candidates:
                    self.training_data.append((cand['features'], 0))
                print(f"   ⏭️ Frame ignorado: {len(candidates)} exemplos negativos adicionados")
            
            cv2.destroyWindow(window_name)
        
        cap.release()
        cv2.destroyAllWindows()
        
        positives = sum(1 for _, label in self.training_data if label == 1)
        negatives = sum(1 for _, label in self.training_data if label == 0)
        
        print("\n" + "="*80)
        print("📊 COLETA FINALIZADA")
        print("="*80)
        print(f"✅ Total de amostras: {len(self.training_data)}")
        print(f"   Bolas (positivos): {positives}")
        print(f"   Não-bolas (negativos): {negatives}")
        print("="*80)
        
        return positives > 0


class MLBallDetector:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.calibrated = False
        self.training_data = []
        
    def train_model(self, training_data):
        if len(training_data) < 20:
            print(f"⚠️ Poucos dados: {len(training_data)}")
            return False
        
        X = np.array([item[0] for item in training_data])
        y = np.array([item[1] for item in training_data])
        
        unique = np.unique(y)
        print(f"📊 Classes encontradas: {unique}")
        
        if len(unique) < 2:
            print(f"❌ ERRO: Apenas uma classe encontrada!")
            return False
        
        self.scaler = RobustScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        X_train, X_val, y_train, y_val = train_test_split(X_scaled, y, test_size=0.2, random_state=42, stratify=y)
        
        # Calcula peso para balancear classes
        neg_count = np.sum(y == 0)
        pos_count = np.sum(y == 1)
        scale_pos_weight = neg_count / pos_count if pos_count > 0 else 1
        
        self.model = xgb.XGBClassifier(
            n_estimators=100, 
            max_depth=6, 
            random_state=42,
            scale_pos_weight=scale_pos_weight
        )
        self.model.fit(X_train, y_train)
        
        train_acc = self.model.score(X_train, y_train)
        val_acc = self.model.score(X_val, y_val)
        
        print(f"\n📈 RESULTADOS DO TREINO:")
        print(f"   Acurácia treino: {train_acc:.2%}")
        print(f"   Acurácia validação: {val_acc:.2%}")
        
        self.calibrated = True
        self.training_data = training_data
        return True
    
    def save_model(self, path):
        if self.model and self.scaler:
            joblib.dump({
                'model': self.model, 
                'scaler': self.scaler, 
                'data': self.training_data
            }, path)
            print(f"💾 Modelo salvo: {path}")
    
    def load_model(self, path):
        if os.path.exists(path):
            data = joblib.load(path)
            self.model = data['model']
            self.scaler = data['scaler']
            self.training_data = data.get('data', [])
            self.calibrated = True
            print(f"📂 Modelo carregado: {path}")
            return True
        return False
    
    def detect_ball(self, frame, bg_subtractor, scene_config):
        if not self.calibrated or self.model is None:
            return None, None, 0
        
        masked_frame = scene_config.apply_inclusion_mask(frame)
        fgmask = bg_subtractor.apply(masked_frame)
        fgmask = cv2.medianBlur(fgmask, 5)
        fgmask = cv2.dilate(fgmask, None, iterations=2)
        
        contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        ball_calibrator = BallCalibrator()
        best_ball = None
        best_prob = 0
        
        for contour in contours:
            features = ball_calibrator.extract_features(contour, frame.shape, masked_frame)
            if features:
                features_scaled = self.scaler.transform([features])
                prob = self.model.predict_proba(features_scaled)[0][1]
                if prob > 0.6 and prob > best_prob:
                    x, y, w, h = cv2.boundingRect(contour)
                    best_ball = (x, y, w, h, prob)
                    best_prob = prob
        
        if best_ball:
            return best_ball[:4], fgmask, best_prob
        return None, fgmask, 0


# ============ FUNÇÃO PARA CRIAR MAPA DE MOVIMENTO ============

def create_motion_map(prev_frame, curr_frame):
    """Cria um mapa de movimento colorido baseado na diferença entre frames"""
    if prev_frame is None:
        return np.zeros_like(curr_frame, dtype=np.uint8)
    
    # Converte para escala de cinza
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
    
    # Calcula diferença absoluta
    diff = cv2.absdiff(prev_gray, curr_gray)
    
    # Aplica threshold para destacar movimento
    _, motion = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
    
    # Aplica blur para suavizar
    motion = cv2.GaussianBlur(motion, (5, 5), 0)
    
    # Converte para mapa de calor colorido (azul = pouco movimento, vermelho = muito movimento)
    motion_color = cv2.applyColorMap(motion, cv2.COLORMAP_JET)
    
    return motion_color


# ============ PIPELINE PRINCIPAL ============

def main():
    video_path = "examples/example.mp4"
    config_path = "scene_config.pkl"
    model_path = "ball_model.pkl"
    
    if not os.path.exists(video_path):
        print(f"❌ Video nao encontrado: {video_path}")
        return
    
    # CONFIGURAÇÃO DA CENA
    scene_config = SceneConfigurator()
    
    if os.path.exists(config_path):
        print("📂 Configuração de cena encontrada.")
        choice = input("Usar configuração existente? (s/n): ").lower()
        if choice == 's':
            with open(config_path, 'rb') as f:
                data = pickle.load(f)
                scene_config.table_corners = data['table_corners']
                scene_config.net_points = data['net_points']
                scene_config.inclusion_polygon = data.get('inclusion_polygon', [])
                scene_config.calibrated = True
            print("✅ Configuração carregada!")
    
    if not scene_config.calibrated:
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        random_frame = np.random.randint(0, total_frames)
        cap.set(cv2.CAP_PROP_POS_FRAMES, random_frame)
        ret, sample_frame = cap.read()
        cap.release()
        
        if ret:
            scene_config.configure_from_frame(sample_frame)
            with open(config_path, 'wb') as f:
                pickle.dump({
                    'table_corners': scene_config.table_corners,
                    'net_points': scene_config.net_points,
                    'inclusion_polygon': scene_config.inclusion_polygon
                }, f)
            print(f"💾 Configuração salva em {config_path}")
    
    # CALIBRAGEM DA BOLINHA
    ball_calibrator = BallCalibrator()
    ml_detector = MLBallDetector()
    
    if os.path.exists(model_path):
        print("📂 Modelo de detecção encontrado.")
        choice = input("Usar modelo existente? (s/n): ").lower()
        if choice == 's':
            ml_detector.load_model(model_path)
    
    if not ml_detector.calibrated:
        print("\n🎾 Vamos calibrar a bolinha!")
        num_balls = input("Quantas bolinhas marcar? (recomendo 30-50): ") or "30"
        num_balls = int(num_balls)
        
        if ball_calibrator.collect_training_data(video_path, scene_config, num_balls_needed=num_balls):
            print("\n📊 Treinando modelo...")
            if ml_detector.train_model(ball_calibrator.training_data):
                ml_detector.save_model(model_path)
                print("✅ Modelo treinado e salvo!")
            else:
                print("❌ Falha no treinamento do modelo")
                return
        else:
            print("❌ Falha na coleta de dados")
            return
    
    # DETECÇÃO FINAL COM RESET E MAPA DE MOVIMENTO
    print("\n🎯 Iniciando detecção no vídeo completo...")
    
    cap = cv2.VideoCapture(video_path)
    bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=30, detectShadows=False)
    
    trajectory = deque(maxlen=50)
    frame_count = 0
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out = cv2.VideoWriter('output_final.mp4', cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
    
    # VARIÁVEIS PARA RESET
    frames_without_ball = 0
    max_frames_without_ball = 30  # Reset após 30 frames sem bola
    tracking_active = False
    
    # VARIÁVEIS PARA MAPA DE MOVIMENTO
    prev_frame = None
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Detecta bola
        ball_pos, fgmask, confidence = ml_detector.detect_ball(frame, bg_subtractor, scene_config)
        
        # LOGICA DE RESET
        if ball_pos:
            frames_without_ball = 0
            tracking_active = True
        else:
            frames_without_ball += 1
            if frames_without_ball >= max_frames_without_ball and tracking_active:
                print(f"   🔄 Reset no frame {frame_count}: {frames_without_ball} frames sem bola")
                tracking_active = False
                trajectory.clear()  # Limpa trajetória
                # Reseta o background subtractor para re-aprender
                bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=30, detectShadows=False)
        
        # CRIA MAPA DE MOVIMENTO
        motion_map = create_motion_map(prev_frame, frame)
        
        # Desenha elementos visuais
        display_frame = frame.copy()
        
        # Polígono de inclusão
        if len(scene_config.inclusion_polygon) >= 3:
            pts = np.array(scene_config.inclusion_polygon, np.int32)
            cv2.polylines(display_frame, [pts], True, (0, 255, 0), 2)
        
        # Mesa (referência)
        if len(scene_config.table_corners) == 4:
            pts = np.array(scene_config.table_corners, np.int32)
            cv2.polylines(display_frame, [pts], True, (0, 255, 0), 1)
        
        # Rede
        if len(scene_config.net_points) == 2:
            cv2.line(display_frame, scene_config.net_points[0], scene_config.net_points[1], (0, 0, 255), 2)
        
        # Bola detectada
        if ball_pos:
            x, y, w, h = ball_pos
            cx, cy = x + w//2, y + h//2
            trajectory.append((cx, cy))
            color = (0, 255, 0) if confidence > 0.8 else (0, 255, 255)
            cv2.rectangle(display_frame, (x, y), (x+w, y+h), color, 2)
            cv2.circle(display_frame, (cx, cy), 4, (0, 0, 255), -1)
            cv2.putText(display_frame, f"BOLA ({confidence:.0%})", (x, y-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Trajetória
        for i in range(1, len(trajectory)):
            cv2.line(display_frame, trajectory[i-1], trajectory[i], (0, 255, 255), 2)
        
        # ADICIONA MAPA DE MOVIMENTO NO CANTO
        if motion_map is not None:
            motion_small = cv2.resize(motion_map, (320, 180))
            display_frame[0:180, display_frame.shape[1]-320:display_frame.shape[1]] = motion_small
            cv2.putText(display_frame, "MAPA DE MOVIMENTO", (display_frame.shape[1]-315, 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # INFORMAÇÕES NA TELA
        status = "TRACKING" if tracking_active else "SEARCHING"
        status_color = (0, 255, 0) if tracking_active else (0, 0, 255)
        cv2.putText(display_frame, f"Status: {status}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
        cv2.putText(display_frame, f"Sem bola: {frames_without_ball}/{max_frames_without_ball}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(display_frame, f"Trajetoria: {len(trajectory)}", (10, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Mostra e salva
        cv2.imshow('Deteccao - Com Reset e Mapa de Movimento', display_frame)
        out.write(display_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        
        prev_frame = frame.copy()
        frame_count += 1
    
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print(f"\n✅ Vídeo salvo: output_final.mp4")

if __name__ == "__main__":
    main()