import cv2
import numpy as np
from collections import deque

def track_ball_interativo(video_path):
    """Versão com ajuste fino de todos os parâmetros"""
    cap = cv2.VideoCapture(video_path)
    
    # Parâmetros configuráveis
    min_area = 20
    max_area = 400
    min_circularity = 0.4  # Começa baixo para detectar mais
    history_frames = 300
    
    bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=history_frames, varThreshold=36, detectShadows=False)
    last_positions = deque(maxlen=5)
    
    # Variáveis para debug
    show_masks = True
    frame_count = 0
    
    print("🎮 CONTROLES:")
    print("  ↑/↓     - Ajusta área mínima")
    print("  →/←     - Ajusta área máxima")
    print("  + / -   - Ajusta circularidade")
    print("  m       - Mostra/esconde máscaras")
    print("  r       - Resetar parâmetros")
    print("  ESC/q   - Sair")
    
    def update_display(frame, fgmask, balls):
        display = frame.copy()
        
        # Mostra máscara se ativada
        if show_masks:
            # Redimensiona máscara para ficar menor (canto superior direito)
            mask_small = cv2.resize(fgmask, (320, 180))
            mask_color = cv2.cvtColor(mask_small, cv2.COLOR_GRAY2BGR)
            display[0:180, frame.shape[1]-320:frame.shape[1]] = mask_color
            
            cv2.putText(display, "Mascara de Movimento", (frame.shape[1]-315, 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # Desenha detecções
        for ball in balls:
            x, y, w, h, circularity = ball
            # Cor verde para melhor circularidade, amarelo para média
            color = (0, 255, 0) if circularity > 0.6 else (0, 255, 255)
            cv2.rectangle(display, (x, y), (x+w, y+h), color, 2)
            cv2.circle(display, (x+w//2, y+h//2), 2, (0, 0, 255), -1)
            cv2.putText(display, f"{circularity:.2f}", (x, y-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Mostra parâmetros
        cv2.putText(display, f"Area: {min_area}-{max_area}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(display, f"Circularidade: {min_circularity:.2f}", (10, 55), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(display, f"Detected: {len(balls)}", (10, 80), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0) if balls else (0, 0, 255), 1)
        
        return display
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Processamento
        fgmask = bg_subtractor.apply(frame)
        fgmask = cv2.medianBlur(fgmask, 5)
        fgmask = cv2.dilate(fgmask, None, iterations=2)
        
        contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        balls = []
        for contour in contours:
            area = cv2.contourArea(contour)
            
            if area < min_area or area > max_area:
                continue
            
            perimeter = cv2.arcLength(contour, True)
            if perimeter == 0:
                continue
            
            circularity = 4 * np.pi * area / (perimeter * perimeter)
            
            if circularity > min_circularity:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Verifica proporção
                if 0.4 < w/h < 2.5:  # Bem tolerante
                    balls.append((x, y, w, h, circularity))
        
        # Mantém últimas posições para suavização
        if balls:
            # Pega a bola com melhor circularidade
            balls.sort(key=lambda b: b[4], reverse=True)
            last_positions.append(balls[0][:4])
        
        # Mostra resultado
        display = update_display(frame, fgmask, balls)
        
        # Desenha rastro
        if len(last_positions) > 1:
            for i in range(1, len(last_positions)):
                x1, y1, w1, h1 = last_positions[i-1]
                x2, y2, w2, h2 = last_positions[i]
                cx1, cy1 = x1 + w1//2, y1 + h1//2
                cx2, cy2 = x2 + w2//2, y2 + h2//2
                cv2.line(display, (cx1, cy1), (cx2, cy2), (0, 255, 255), 2)
        
        cv2.imshow('Deteccao Interativa', display)
        
        # Controles
        key = cv2.waitKey(30) & 0xFF
        if key == 27 or key == ord('q'):
            break
        elif key == ord('u'):  # Aumenta min_area (Up)
            min_area += 5
        elif key == ord('j'):  # Diminui min_area (Down)
            min_area = max(5, min_area - 5)
        elif key == ord('i'):  # Aumenta max_area (Right)
            max_area += 50
        elif key == ord('k'):  # Diminui max_area (Left)
            max_area = max(50, max_area - 50)
        elif key == ord('+'):  # Aumenta circularidade
            min_circularity = min(1.0, min_circularity + 0.05)
        elif key == ord('-'):  # Diminui circularidade
            min_circularity = max(0.1, min_circularity - 0.05)
        elif key == ord('m'):  # Mostra máscaras
            show_masks = not show_masks
        elif key == ord('r'):  # Reset
            min_area = 20
            max_area = 400
            min_circularity = 0.4
            print("Parâmetros resetados!")
        
        print(f"\rMinArea:{min_area} MaxArea:{max_area} Circ:{min_circularity:.2f} Bolas:{len(balls)}", end="")
    
    cap.release()
    cv2.destroyAllWindows()

# Teste
track_ball_interativo("examples/example.mp4")