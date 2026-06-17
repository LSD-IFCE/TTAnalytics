import cv2
import numpy as np
from collections import deque
import os
import pickle
import json
from datetime import datetime
import random
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

os.environ["QT_QPA_PLATFORM"] = "xcb"

# ============================================================
# CLASSE: CONFIGURAÇÃO DA CENA (MESA + REDE + ROI)
# ============================================================

class SceneConfigurator:
    """Configura completa da cena: mesa, rede e ROI"""
    
    def __init__(self):
        self.table_corners = []      # 4 pontos da mesa
        self.net_points = []         # 2 pontos da rede
        self.roi_polygon = []        # Polígono de interesse (opcional)
        self.calibrated = False
        
    def configure_scene(self, frame):
        """Configura todos os elementos da cena"""
        print("\n" + "="*70)
        print("🎯 CONFIGURAÇÃO COMPLETA DA CENA")
        print("="*70)
        
        # PARTE 1: Vértices da mesa
        print("\n🔷 PARTE 1: Clique nos 4 VÉRTICES da mesa")
        self.table_corners = self._collect_points(frame, num_points=4, color=(0, 255, 0),
                                                   window_name="Config - Vertices da Mesa")
        
        if len(self.table_corners) != 4:
            print("⚠️ Configuração da mesa incompleta. Usando frame inteiro.")
            h, w = frame.shape[:2]
            self.table_corners = [(0, 0), (w, 0), (w, h), (0, h)]
        
        # PARTE 2: Pontos da rede
        print("\n🔴 PARTE 2: Clique nos 2 pontos da rede (esquerda e direita)")
        self.net_points = self._collect_points(frame, num_points=2, color=(0, 0, 255),
                                                window_name="Config - Pontos da Rede")
        
        if len(self.net_points) != 2:
            print("⚠️ Pontos da rede não configurados. Calculando automaticamente...")
            if len(self.table_corners) == 4:
                self.net_points = [
                    ((self.table_corners[0][0] + self.table_corners[3][0]) // 2,
                     (self.table_corners[0][1] + self.table_corners[3][1]) // 2),
                    ((self.table_corners[1][0] + self.table_corners[2][0]) // 2,
                     (self.table_corners[1][1] + self.table_corners[2][1]) // 2)
                ]
        
        # PARTE 3: ROI (opcional)
        print("\n🟨 PARTE 3: Desenhe a ROI (área de busca) - Opcional")
        print("   Se não desenhar, usará a mesa inteira")
        self.roi_polygon = self._draw_polygon(frame, "Config - ROI (Area de Busca)")
        
        self.calibrated = True
        self._visualize_configuration(frame)
        
        return True
    
    def _collect_points(self, frame, num_points, color, window_name):
        """Coleta pontos clicados pelo usuário"""
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
    
    def _draw_polygon(self, frame, window_name):
        """Desenha polígono interativamente (para ROI)"""
        polygon = []
        cv2.namedWindow(window_name)
        display = frame.copy()
        cv2.putText(display, "Clique para adicionar pontos | ENTER=fechar | ESC=pular", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.imshow(window_name, display)
        cv2.waitKey(1)
        
        def mouse_callback(event, x, y, flags, param):
            nonlocal polygon, display
            if event == cv2.EVENT_LBUTTONDOWN:
                polygon.append((x, y))
                display = frame.copy()
                if len(polygon) > 0:
                    pts = np.array(polygon, np.int32)
                    cv2.polylines(display, [pts], False, (0, 255, 255), 2)
                    overlay = display.copy()
                    cv2.fillPoly(overlay, [pts], (0, 255, 255))
                    cv2.addWeighted(overlay, 0.2, display, 0.8, 0, display)
                    for i, pt in enumerate(polygon):
                        cv2.circle(display, pt, 5, (0, 255, 255), -1)
                        cv2.putText(display, f"{i+1}", (pt[0]+8, pt[1]-8), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                cv2.putText(display, f"Pontos: {len(polygon)} | ENTER=fechar", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.imshow(window_name, display)
        
        cv2.setMouseCallback(window_name, mouse_callback)
        
        while True:
            key = cv2.waitKey(10) & 0xFF
            if key == 13 and len(polygon) >= 3:
                break
            elif key == 27:
                polygon = []
                break
            elif key == ord('r'):
                polygon = []
                display = frame.copy()
                cv2.putText(display, "Poligono resetado", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.imshow(window_name, display)
            elif key == ord('u') and polygon:
                polygon.pop()
                display = frame.copy()
                if len(polygon) > 0:
                    pts = np.array(polygon, np.int32)
                    cv2.polylines(display, [pts], False, (0, 255, 255), 2)
                    overlay = display.copy()
                    cv2.fillPoly(overlay, [pts], (0, 255, 255))
                    cv2.addWeighted(overlay, 0.2, display, 0.8, 0, display)
                    for i, pt in enumerate(polygon):
                        cv2.circle(display, pt, 5, (0, 255, 255), -1)
                cv2.putText(display, f"Pontos: {len(polygon)} | ENTER=fechar", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.imshow(window_name, display)
            elif key == ord('q'):
                cv2.destroyAllWindows()
                exit()
        
        cv2.destroyWindow(window_name)
        return polygon
    
    def _visualize_configuration(self, frame):
        """Mostra visualização final da configuração"""
        vis = frame.copy()
        
        # Desenha mesa (verde)
        if len(self.table_corners) == 4:
            pts = np.array(self.table_corners, np.int32)
            cv2.polylines(vis, [pts], True, (0, 255, 0), 3)
            for i, pt in enumerate(self.table_corners):
                cv2.circle(vis, pt, 8, (0, 255, 0), -1)
                cv2.putText(vis, f"M{i+1}", (pt[0]+10, pt[1]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Desenha rede (vermelho)
        if len(self.net_points) == 2:
            cv2.line(vis, self.net_points[0], self.net_points[1], (0, 0, 255), 4)
            for i, pt in enumerate(self.net_points):
                cv2.circle(vis, pt, 8, (0, 0, 255), -1)
                cv2.putText(vis, f"Rede", (pt[0]+10, pt[1]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        # Desenha ROI (amarelo)
        if len(self.roi_polygon) >= 3:
            pts = np.array(self.roi_polygon, np.int32)
            overlay = vis.copy()
            cv2.fillPoly(overlay, [pts], (0, 255, 255))
            cv2.addWeighted(overlay, 0.2, vis, 0.8, 0, vis)
            cv2.polylines(vis, [pts], True, (0, 255, 255), 2)
        
        cv2.putText(vis, "CONFIGURACAO CONCLUIDA - Pressione ENTER", (10, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.imshow("Cena Configurada", vis)
        cv2.waitKey(0)
        cv2.destroyWindow("Cena Configurada")
    
    def apply_roi_mask(self, frame):
        """Aplica máscara da ROI (tudo fora fica preto)"""
        if len(self.roi_polygon) >= 3:
            mask = np.zeros(frame.shape[:2], dtype=np.uint8)
            pts = np.array(self.roi_polygon, np.int32)
            cv2.fillPoly(mask, [pts], 255)
            return cv2.bitwise_and(frame, frame, mask=mask)
        return frame
    
    def draw_scene(self, frame):
        """Desenha todos os elementos da cena no frame"""
        result = frame.copy()
        
        # Mesa (verde)
        if len(self.table_corners) == 4:
            pts = np.array(self.table_corners, np.int32)
            cv2.polylines(result, [pts], True, (0, 255, 0), 2)
        
        # Rede (vermelho)
        if len(self.net_points) == 2:
            cv2.line(result, self.net_points[0], self.net_points[1], (0, 0, 255), 3)
        
        # ROI (amarelo)
        if len(self.roi_polygon) >= 3:
            pts = np.array(self.roi_polygon, np.int32)
            cv2.polylines(result, [pts], True, (0, 255, 255), 2)
        
        return result


# ============================================================
# CLASSE: COLETOR DE DADOS TEMPORAIS
# ============================================================

class TemporalDataCollector:
    def __init__(self, window_size=5):
        self.window_size = window_size
        self.training_data = []
        self.frame_buffer = deque(maxlen=window_size)
        self.mask_buffer = deque(maxlen=window_size)
        
    def extract_features(self, masks, ball_position=None):
        """Extrai features da janela temporal"""
        features = []
        
        for mask in masks:
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            best_contour = None
            best_score = 0
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < 20 or area > 500:
                    continue
                
                perimeter = cv2.arcLength(contour, True)
                if perimeter == 0:
                    continue
                
                circularity = 4 * np.pi * area / (perimeter * perimeter)
                
                if ball_position:
                    x, y, w, h = cv2.boundingRect(contour)
                    cx, cy = x + w//2, y + h//2
                    dist = np.sqrt((cx - ball_position[0])**2 + (cy - ball_position[1])**2)
                    if dist < 40 and circularity > 0.4:
                        score = circularity * (1.0 / (1.0 + dist/20))
                        if score > best_score:
                            best_score = score
                            best_contour = contour
                else:
                    if circularity > 0.4 and area > best_score:
                        best_score = area
                        best_contour = contour
            
            if best_contour is not None:
                area = cv2.contourArea(best_contour)
                perimeter = cv2.arcLength(best_contour, True)
                circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
                x, y, w, h = cv2.boundingRect(best_contour)
                aspect_ratio = w / h if h > 0 else 1
                
                features.extend([area, circularity, aspect_ratio, w, h])
            else:
                features.extend([0, 0, 0, 0, 0])
        
        # Continuidade
        continuity = 0
        for mask in masks:
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if any(cv2.contourArea(c) > 20 for c in contours):
                continuity += 1
        features.append(continuity)
        
        # Variação
        if len(masks) >= 2:
            prev_pixels = np.sum(masks[-2] > 0)
            curr_pixels = np.sum(masks[-1] > 0)
            variation = abs(curr_pixels - prev_pixels) / (prev_pixels + 1)
            features.append(variation)
        else:
            features.append(0)
        
        return features
    
    def collect_from_video(self, video_path, scene_config, num_samples=50):
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=100, varThreshold=30)
        
        # Preenche buffers
        self.frame_buffer.clear()
        self.mask_buffer.clear()
        frame_num = 0
        
        while len(self.mask_buffer) < self.window_size and frame_num < total_frames:
            ret, frame = cap.read()
            if not ret:
                break
            masked = scene_config.apply_roi_mask(frame)
            fgmask = bg_subtractor.apply(masked)
            fgmask = cv2.medianBlur(fgmask, 5)
            fgmask = cv2.dilate(fgmask, None, iterations=2)
            self.frame_buffer.append(frame)
            self.mask_buffer.append(fgmask)
            frame_num += 1
        
        print("\n" + "="*70)
        print(f"🎾 COLETA TEMPORAL - {num_samples} amostras")
        print("="*70)
        print("CLIQUE na bolinha + ENTER = POSITIVO")
        print("ESC = NEGATIVO (sem bola)")
        print("="*70)
        
        collected = 0
        negatives = 0
        
        while collected < num_samples and frame_num < total_frames:
            central_frame = self.frame_buffer[self.window_size // 2]
            
            display = scene_config.draw_scene(central_frame)
            
            # Desenha contornos
            central_mask = self.mask_buffer[self.window_size // 2]
            contours, _ = cv2.findContours(central_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in contours:
                if cv2.contourArea(c) > 20:
                    x, y, w, h = cv2.boundingRect(c)
                    cv2.rectangle(display, (x, y), (x+w, y+h), (255, 0, 0), 2)
            
            cv2.putText(display, f"Positivos: {collected}/{num_samples} | Negativos: {negatives}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(display, "Clique na BOLA + ENTER | ESC = negativo", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            cv2.imshow("Coleta Temporal", display)
            
            clicked = None
            def mouse_cb(event, x, y, flags, param):
                nonlocal clicked
                if event == cv2.EVENT_LBUTTONDOWN:
                    clicked = (x, y)
            
            cv2.setMouseCallback("Coleta Temporal", mouse_cb)
            
            decision = None
            while decision is None:
                temp = display.copy()
                if clicked:
                    cv2.circle(temp, clicked, 8, (0, 255, 0), 2)
                    cv2.putText(temp, "BOLA", (clicked[0]-30, clicked[1]-10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                cv2.imshow("Coleta Temporal", temp)
                
                key = cv2.waitKey(10) & 0xFF
                if key == 13 and clicked:
                    decision = "positive"
                elif key == 27:
                    decision = "negative"
                elif key == ord('q'):
                    cap.release()
                    cv2.destroyAllWindows()
                    return False
            
            features = self.extract_features(list(self.mask_buffer), clicked if decision == "positive" else None)
            
            if decision == "positive":
                self.training_data.append((features, 1))
                collected += 1
                print(f"   ✅ {collected}/{num_samples} - POSITIVO")
            else:
                self.training_data.append((features, 0))
                negatives += 1
                print(f"   ⚠️ NEGATIVO ({negatives} total)")
            
            # Avança
            ret, frame = cap.read()
            if not ret:
                break
            masked = scene_config.apply_roi_mask(frame)
            fgmask = bg_subtractor.apply(masked)
            fgmask = cv2.medianBlur(fgmask, 5)
            fgmask = cv2.dilate(fgmask, None, iterations=2)
            self.frame_buffer.append(frame)
            self.mask_buffer.append(fgmask)
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
# MAIN
# ============================================================

def main():
    video_path = "examples/example.mp4"
    config_path = "scene_config.pkl"
    data_path = "temporal_data.pkl"
    model_path = "temporal_model.pkl"
    
    if not os.path.exists(video_path):
        print(f"❌ Video nao encontrado: {video_path}")
        return
    
    # 1. Configura cena (mesa + rede + ROI)
    scene_config = SceneConfigurator()
    
    if os.path.exists(config_path):
        choice = input("Usar configuração existente? (s/n): ").lower()
        if choice == 's':
            with open(config_path, 'rb') as f:
                data = pickle.load(f)
                scene_config.table_corners = data.get('table_corners', [])
                scene_config.net_points = data.get('net_points', [])
                scene_config.roi_polygon = data.get('roi_polygon', [])
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
                    'net_points': scene_config.net_points,
                    'roi_polygon': scene_config.roi_polygon
                }, f)
            print("💾 Configuração salva")
    
    # 2. Coleta dados temporais
    collector = TemporalDataCollector(window_size=5)
    
    if os.path.exists(data_path):
        choice = input(f"Usar dados existentes ({data_path})? (s/n): ").lower()
        if choice == 's':
            collector.load_data(data_path)
    
    if len(collector.training_data) == 0:
        num = int(input("\nQuantas amostras? [50]: ") or "50")
        collector.collect_from_video(video_path, scene_config, num_samples=num)
        collector.save_data(data_path)
    
    # 3. Treina modelo
    if len(collector.training_data) > 0:
        X = np.array([d[0] for d in collector.training_data])
        y = np.array([d[1] for d in collector.training_data])
        
        print(f"\n🚀 Treinando modelo com {len(X)} amostras, {X.shape[1]} features...")
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
        
        model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
        model.fit(X_train, y_train)
        
        train_acc = model.score(X_train, y_train)
        test_acc = model.score(X_test, y_test)
        
        print(f"\n📈 Resultados:")
        print(f"   Acurácia treino: {train_acc:.2%}")
        print(f"   Acurácia teste: {test_acc:.2%}")
        
        with open(model_path, 'wb') as f:
            pickle.dump({'model': model, 'scaler': scaler}, f)
        print(f"💾 Modelo salvo: {model_path}")
    
    print("\n✅ Pipeline concluído!")


if __name__ == "__main__":
    main()