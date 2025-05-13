import cv2
import numpy as np
import threading
import tkinter as tk
from tkinter import ttk
import json
import os
import serial
import time

ruta_config = "/home/raspberry/miniproyectoauto/config.json"
UART_PORT = "/dev/ttyACM0"
BAUD_RATE = 115200

# Inicializa UART
ser = serial.Serial(UART_PORT, BAUD_RATE, timeout=1)
time.sleep(2)

parametros = {
    "brillo": 0,
    "kernel_size": 3,
    "threshold1": 40,
    "threshold2": 160,
    "filtro": "Gaussian",
    "mostrar_canny": True,
    "mostrar_hsv": False,
    "color_seleccionado": "rojo",
    "ejecutar": True,
    "hsv": {
        "rojo": [(0, 100, 100), (10, 255, 255)],
        "verde": [(40, 70, 70), (80, 255, 255)],
        "amarillo": [(20, 100, 100), (30, 255, 255)],
        "azul": [(100, 150, 0), (140, 255, 255)]
    }
}

ultimo_estado_uart = None  # Guarda ultimo comando enviado

def aplicar_filtro(imagen):
    k = parametros["kernel_size"]
    if parametros["filtro"] == "Gaussian":
        return cv2.GaussianBlur(imagen, (k, k), 0)
    elif parametros["filtro"] == "Median":
        return cv2.medianBlur(imagen, k)
    elif parametros["filtro"] == "Bilateral":
        return cv2.bilateralFilter(imagen, 5, 50, 50)  # menor carga
    elif parametros["filtro"] == "Mean":
        return cv2.blur(imagen, (k, k))
    return imagen

def detectar_figuras_y_colores(frame, mascara):
    global ultimo_estado_uart
    contornos, _ = cv2.findContours(mascara, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    objetos_validos = []

    for contorno in contornos:
        area = cv2.contourArea(contorno)
        if area > 500:
            objetos_validos.append(contorno)
            epsilon = 0.02 * cv2.arcLength(contorno, True)
            approx = cv2.approxPolyDP(contorno, epsilon, True)
            x, y, w, h = cv2.boundingRect(approx)
            cv2.drawContours(frame, [approx], -1, (255, 255, 255), 2)

            forma = "Desconocida"
            vertices = len(approx)
            if vertices == 3:
                forma = "Triangulo"
            elif vertices == 4:
                aspecto = w / float(h)
                forma = "Cuadrado" if 0.95 < aspecto < 1.05 else "Rectangulo"
            elif vertices > 4:
                forma = "Circulo"

            color = parametros["color_seleccionado"].capitalize()
            texto = f"{forma} {color}"
            cv2.putText(frame, texto, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    # UART control con control de estado
    num_objetos = len(objetos_validos)
    nuevo_estado = None
    if num_objetos == 1:
        nuevo_estado = 1
    elif num_objetos >= 2:
        nuevo_estado = 2
    else:
        nuevo_estado = 3

    if nuevo_estado != ultimo_estado_uart:
        ser.write(str(nuevo_estado).encode())
        print(f"{num_objetos} objeto(s) detectado(s) -> enviar ({nuevo_estado})")
        ultimo_estado_uart = nuevo_estado

def procesar_video(captura):
    while parametros["ejecutar"]:
        ret, frame = captura.read()
        if not ret:
            break

        # Redimensionar para mejor rendimiento
        frame = cv2.resize(frame, (320, 240))

        ajustado = cv2.convertScaleAbs(frame, alpha=1, beta=parametros["brillo"])

        # Mostrar Canny si esta habilitado
        if parametros["mostrar_canny"]:
            gris = cv2.cvtColor(ajustado, cv2.COLOR_BGR2GRAY)
            filtrado = aplicar_filtro(gris)
            bordes = cv2.Canny(filtrado, parametros["threshold1"], parametros["threshold2"])
            cv2.imshow("Canny", bordes)

        # Mostrar HSV si esta habilitado
        if parametros["mostrar_hsv"]:
            hsv = cv2.cvtColor(ajustado, cv2.COLOR_BGR2HSV)
            color = parametros["color_seleccionado"]
            rango_bajo, rango_alto = parametros["hsv"][color]
            mascara = cv2.inRange(hsv, np.array(rango_bajo), np.array(rango_alto))
            resultado = cv2.bitwise_and(ajustado, ajustado, mask=mascara)

            detectar_figuras_y_colores(resultado, mascara)

            cv2.imshow("HSV", resultado)

        # Solo usar waitKey si se muestra algo
        if parametros["mostrar_canny"] or parametros["mostrar_hsv"]:
            if cv2.waitKey(1) & 0xFF == ord('q'):
                parametros["ejecutar"] = False
                break

    captura.release()
    cv2.destroyAllWindows()
    guardar_configuracion()
    ser.close()

def guardar_configuracion():
    os.makedirs(os.path.dirname(ruta_config), exist_ok=True)
    with open(ruta_config, 'w') as archivo:
        json.dump(parametros, archivo, indent=4)

def iniciar_gui():
    root = tk.Tk()
    root.title("Panel de Ajustes")

    def actualizar_valor(clave, var):
        parametros[clave] = int(var.get())
        if clave == "kernel_size" and parametros[clave] % 2 == 0:
            parametros[clave] += 1

    def actualizar_hsv(indice, var):
        hsv_actual = list(parametros["hsv"][parametros["color_seleccionado"]][0 if indice < 3 else 1])
        hsv_actual[indice % 3] = int(var.get())
        if indice < 3:
            parametros["hsv"][parametros["color_seleccionado"]] = (tuple(hsv_actual), parametros["hsv"][parametros["color_seleccionado"]][1])
        else:
            parametros["hsv"][parametros["color_seleccionado"]] = (parametros["hsv"][parametros["color_seleccionado"]][0], tuple(hsv_actual))

    sliders = {
        "Brillo": ("brillo", -100, 100),
        "Kernel Size": ("kernel_size", 3, 31),
        "Threshold1": ("threshold1", 0, 254),
        "Threshold2": ("threshold2", 1, 255)
    }

    for texto, (clave, minimo, maximo) in sliders.items():
        tk.Label(root, text=texto).pack()
        var = tk.Scale(root, from_=minimo, to=maximo, orient=tk.HORIZONTAL, resolution=2 if clave == "kernel_size" else 1)
        var.set(parametros[clave] if clave != "kernel_size" or parametros[clave] % 2 == 1 else parametros[clave] + 1)
        var.config(command=lambda v, c=clave, vv=var: actualizar_valor(c, vv))
        var.pack()

    tk.Label(root, text="Filtro").pack()
    filtro = ttk.Combobox(root, values=["Gaussian", "Median", "Bilateral", "Mean"])
    filtro.set(parametros["filtro"])
    filtro.bind("<<ComboboxSelected>>", lambda e: parametros.update({"filtro": filtro.get()}))
    filtro.pack()

    tk.Label(root, text="Color HSV").pack()
    color = ttk.Combobox(root, values=["rojo", "verde", "amarillo", "azul"])
    color.set(parametros["color_seleccionado"])
    def cambiar_color(e):
        parametros["color_seleccionado"] = color.get()
        actualizar_sliders_hsv()
    color.bind("<<ComboboxSelected>>", cambiar_color)
    color.pack()

    tk.Checkbutton(root, text="Mostrar Canny", variable=tk.BooleanVar(value=parametros["mostrar_canny"]),
                   command=lambda: parametros.update({"mostrar_canny": not parametros["mostrar_canny"]})).pack()
    tk.Checkbutton(root, text="Mostrar HSV", variable=tk.BooleanVar(value=parametros["mostrar_hsv"]),
                   command=lambda: parametros.update({"mostrar_hsv": not parametros["mostrar_hsv"]})).pack()

    etiquetas = ["Hmin", "Smin", "Vmin", "Hmax", "Smax", "Vmax"]
    hsv_sliders = []

    def actualizar_sliders_hsv():
        color_act = parametros["color_seleccionado"]
        valores = list(parametros["hsv"][color_act][0]) + list(parametros["hsv"][color_act][1])
        for i, slider in enumerate(hsv_sliders):
            slider.set(valores[i])

    for i, nombre in enumerate(etiquetas):
        tk.Label(root, text=nombre).pack()
        slider = tk.Scale(root, from_=0, to=255, orient=tk.HORIZONTAL, command=lambda v, idx=i: actualizar_hsv(idx, hsv_sliders[idx]))
        slider.pack()
        hsv_sliders.append(slider)

    actualizar_sliders_hsv()
    root.mainloop()
    parametros["ejecutar"] = False

def main():
    url = "http://192.168.1.2:4747/video"
    captura = cv2.VideoCapture(url)
    if not captura.isOpened():
        print("Error al conectar con la camara")
        return

    hilo_video = threading.Thread(target=procesar_video, args=(captura,), daemon=True)
    hilo_video.start()
    iniciar_gui()
    hilo_video.join()

if __name__ == "__main__":
    main()
