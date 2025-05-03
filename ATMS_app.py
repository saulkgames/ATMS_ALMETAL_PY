import pandas as pd
from datetime import datetime, timedelta
from tkinter import Tk, Button, filedialog, messagebox

# ---------- FUNCIONES DE PROCESAMIENTO ----------

def leer_archivo():
    archivo = filedialog.askopenfilename(
        title="Selecciona el archivo de asistencia",
        filetypes=[("CSV Files", "*.csv")]
    )
    return archivo

def guardar_archivo():
    archivo = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV Files", "*.csv")],
        title="Guardar archivo como..."
    )
    return archivo

# ----------Funcion para calcular minutos de retraso, tiempo extra o salida temprana ---------- #

def calcular_asistencia(df):
    # Definir horarios estándar
    hora_entrada = datetime.strptime("08:00", "%H:%M").time()
    hora_salida_comida = datetime.strptime("13:00", "%H:%M").time()
    hora_regreso_comida = datetime.strptime("14:30", "%H:%M").time()
    hora_salida = datetime.strptime("18:15", "%H:%M").time()  # salida ajustada

    tolerancia = timedelta(minutes=5)
    tolerancia_overtime = timedelta(minutes=20)

    df['RetardoMin'] = 0
    df['EarlyLeaveMin'] = 0
    df['OvertimeMin'] = 0

    def procesar(row):
        fecha = row['Time'].date()
        hora_actual = row['Time']

         # Usar hora de salida diferente si es sábado
        if row['Time'].weekday() == 5:
            hora_salida_dia = datetime.strptime("14:00", "%H:%M").time()
        else:
            hora_salida_dia = hora_salida

        h_entrada = datetime.combine(fecha, hora_entrada)
        h_salida_comida = datetime.combine(fecha, hora_salida_comida)
        h_regreso_comida = datetime.combine(fecha, hora_regreso_comida)
        h_salida = datetime.combine(fecha, hora_salida_dia)

        retardo = early = overtime = 0

        status = row['Attendance Status']

        if status == 'Check-in':
            if hora_actual > h_entrada + tolerancia:
                retardo = int((hora_actual - (h_entrada + tolerancia)).total_seconds() // 60)
            elif hora_actual < h_entrada - tolerancia:
                overtime = int(((h_entrada - tolerancia) - hora_actual).total_seconds() // 60)

        elif status == 'Break-Out':
            if hora_actual < h_salida_comida - tolerancia:
                early = int(((h_salida_comida - tolerancia) - hora_actual).total_seconds() // 60)
            elif hora_actual > h_salida_comida + tolerancia:
                overtime = int((hora_actual - (h_salida_comida + tolerancia)).total_seconds() // 60)

        elif status == 'Break-In':
            if hora_actual > h_regreso_comida + tolerancia:
                retardo = int((hora_actual - (h_regreso_comida + tolerancia)).total_seconds() // 60)
            elif hora_actual < h_regreso_comida - tolerancia:
                overtime = int(((h_regreso_comida - tolerancia) - hora_actual).total_seconds() // 60)

        elif status == 'Check-out':
            if hora_actual < h_salida - tolerancia:
                early = int(((h_salida - tolerancia) - hora_actual).total_seconds() // 60)
            elif hora_actual > h_salida + tolerancia_overtime:
                overtime = int((hora_actual - (h_salida + tolerancia_overtime)).total_seconds() // 60)

        return pd.Series([retardo, early, overtime])

    df[['RetardoMin', 'EarlyLeaveMin', 'OvertimeMin']] = df.apply(procesar, axis=1)

    resumen = df.groupby(['Person ID', 'Name', df['Time'].dt.date])[['RetardoMin', 'EarlyLeaveMin', 'OvertimeMin']].sum().reset_index()

    return resumen

# ---------- Funcion que revisa si algun check hizo falta dentro de los esperados de un dia ---------- #

def auditar_asistencia(df):
    faltantes = []
    # Hace un grupo por del df por cada person_id,name y fecha que sean iguales
    for (person_id, name, fecha), grupo in df.groupby(['Person ID', 'Name', df['Time'].dt.date]):
        # Determinar si es sábado
        es_sabado = pd.Timestamp(fecha).weekday() == 5
        
        # Definir los status esperados según el día
        if es_sabado:
            status_esperados = {'Check-in', 'Check-out'}
        else:
            status_esperados = {'Check-in', 'Break-Out', 'Break-In', 'Check-out'}
        
        # Esta linea declara una variable llamada status_del_dia la cual almacena en un conjunto los attendance status unicos
        status_del_dia = set(grupo['Attendance Status'])
        faltantes_status = status_esperados - status_del_dia
        # Si faltantes_status tiene algun valor rellena la lista de faltantes
        if faltantes_status:
            # Rellena la lista de faltantes con los valores que cumplen los criterios
            faltantes.append({
                'Person ID': person_id,
                'Name': name,
                'Fecha': fecha,
                'Faltantes': ', '.join(faltantes_status)
            })
    
    return pd.DataFrame(faltantes)

# ---------- Funcion para encontrar los checks duplicados y marcados por error ---------- #

def validar_duplicados(df):
    duplicados_lista = []  # Lista donde guardaremos los resultados finales
    
    # Agrupamos los registros por Person ID, Name y fecha (solo la parte de la fecha de la columna Time)
    for (person_id, name, fecha), grupo in df.groupby(['Person ID', 'Name', df['Time'].dt.date]):
        status_del_dia = grupo['Attendance Status'].tolist()  # Creamos un sub dataframe de solamente los 'Attendance Status' de ese día
        
        # Buscamos cuáles status están duplicados (es decir, que ocurren más de una vez)
        duplicados = {status for status in set(status_del_dia) if status_del_dia.count(status) > 1}
        
        if duplicados:  # Si encontramos algún status duplicado
            detalles = []  # Aquí guardaremos los detalles de cada status duplicado y sus horas
            
            # Para cada status duplicado
            for status in duplicados:
                # Obtenemos las horas (columna Time) en las que se registró ese status duplicado
                horas = grupo[grupo['Attendance Status'] == status]['Time'].dt.strftime('%H:%M:%S').tolist()
                
                # Formateamos el texto: nombre del status seguido de las horas separadas por |
                detalles.append(f"{status}: {' | '.join(horas)}")
            
            # Guardamos un diccionario con la persona, fecha y los detalles de los duplicados
            duplicados_lista.append({
                'Person ID': person_id,
                'Name': name,
                'Fecha': fecha,
                'Duplicados': '; '.join(detalles)  # Unimos todos los detalles en un solo string separado por ;
            })
    
    # Convertimos la lista de resultados en un DataFrame para fácil manejo o exportación
    return pd.DataFrame(duplicados_lista)

# ---------- EVENTOS DE BOTONES ----------

def accion_calculo():
    archivo = leer_archivo()
    if archivo:
        df = pd.read_csv(archivo)
        df['Time'] = pd.to_datetime(df['Time'])
        resultado = calcular_asistencia(df)
        ruta_guardado = guardar_archivo()
        if ruta_guardado:
            resultado.to_csv(ruta_guardado, index=False)
            messagebox.showinfo("Éxito", "Resumen de asistencia guardado correctamente.")

def accion_auditoria():
    archivo = leer_archivo()
    if archivo:
        df = pd.read_csv(archivo)
        df['Time'] = pd.to_datetime(df['Time'])
        resultado = auditar_asistencia(df)
        ruta_guardado = guardar_archivo()
        if ruta_guardado:
            resultado.to_csv(ruta_guardado, index=False)
            messagebox.showinfo("Éxito", "Auditoría guardada correctamente.")

def accion_duplicados():
    archivo = leer_archivo()
    if archivo:
        df = pd.read_csv(archivo)
        df['Time'] = pd.to_datetime(df['Time'])
        resultado = validar_duplicados(df)
        ruta_guardado = guardar_archivo()
        if ruta_guardado:
            resultado.to_csv(ruta_guardado, index=False)
            messagebox.showinfo("Éxito", "Validación de duplicados guardada correctamente.")

# ---------- UI ----------

root = Tk()
root.title("Gestión de Asistencia")
root.geometry("300x250")

btn_calculo = Button(root, text="Cálculo de Asistencia", width=30, command=accion_calculo)
btn_auditoria = Button(root, text="Auditoría de Asistencia", width=30, command=accion_auditoria)
btn_duplicados = Button(root, text="Validación de Checks Duplicados", width=30, command=accion_duplicados)

btn_calculo.pack(pady=15)
btn_auditoria.pack(pady=15)
btn_duplicados.pack(pady=15)

root.mainloop()
