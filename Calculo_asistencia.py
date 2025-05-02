import pandas as pd
from datetime import datetime, timedelta

# Leer CSV y convertir columna Time a datetime
df = pd.read_csv('TestTable_Attendance.csv')
df['Time'] = pd.to_datetime(df['Time'])

# Crear columnas vacías para resultados
df['RetardoMin'] = 0
df['EarlyLeaveMin'] = 0
df['OvertimeMin'] = 0

def calcular_minutos(row):
    fecha = row['Time'].date()
    hora_actual = row['Time']
    tolerancia = timedelta(minutes=5)

    # Definir horas esperadas
    if fecha.weekday() == 5:  # sábado
        hora_salida = datetime.strptime("14:00", "%H:%M").time()
    else:
        hora_salida = datetime.strptime("18:15", "%H:%M").time()

    hora_entrada = datetime.strptime("08:00", "%H:%M").time()
    hora_salida_comida = datetime.strptime("13:00", "%H:%M").time()
    hora_regreso_comida = datetime.strptime("14:30", "%H:%M").time()

    retardo = 0
    early = 0
    overtime = 0

    if row['Attendance Status'] == 'Check-in':
        hora_ref = datetime.combine(fecha, hora_entrada)
        if hora_actual > hora_ref + tolerancia:
            retardo = int((hora_actual - (hora_ref + tolerancia)).total_seconds() // 60)
        elif hora_actual < hora_ref - tolerancia:
            overtime = int(((hora_ref - tolerancia) - hora_actual).total_seconds() // 60)

    elif row['Attendance Status'] == 'Break-Out':
        hora_ref = datetime.combine(fecha, hora_salida_comida)
        if hora_actual < hora_ref - tolerancia:
            early = int(((hora_ref - tolerancia) - hora_actual).total_seconds() // 60)
        elif hora_actual > hora_ref + tolerancia:
            overtime = int((hora_actual - (hora_ref + tolerancia)).total_seconds() // 60)

    elif row['Attendance Status'] == 'Break-In':
        hora_ref = datetime.combine(fecha, hora_regreso_comida)
        if hora_actual > hora_ref + tolerancia:
            retardo = int((hora_actual - (hora_ref + tolerancia)).total_seconds() // 60)
        elif hora_actual < hora_ref - tolerancia:
            overtime = int(((hora_ref - tolerancia) - hora_actual).total_seconds() // 60)

    elif row['Attendance Status'] == 'Check-out':
        hora_ref = datetime.combine(fecha, hora_salida)
        if hora_actual < hora_ref - tolerancia:
            early = int(((hora_ref - tolerancia) - hora_actual).total_seconds() // 60)
        elif hora_actual > hora_ref + tolerancia:
            overtime = int((hora_actual - (hora_ref + tolerancia)).total_seconds() // 60)

    return retardo, early, overtime

# Aplicar cálculo
df[['RetardoMin', 'EarlyLeaveMin', 'OvertimeMin']] = df.apply(lambda row: pd.Series(calcular_minutos(row)), axis=1)

# Agrupar por empleado y fecha
resumen = df.groupby(['Person ID', 'Name', df['Time'].dt.date])[['RetardoMin', 'EarlyLeaveMin', 'OvertimeMin']].sum().reset_index()

# Exportar resumen a CSV
resumen.to_csv('resumen_asistencia.csv', index=False)

print("Resumen exportado a resumen_asistencia.csv")
