"""Rebuild the three technical PDFs. Requires reportlab and pypdf."""
from pathlib import Path
from html import escape
import hashlib
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Preformatted
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader

# Embed the installed fonts so symbols and accents render consistently.
for name, font in [('Helvetica','arial.ttf'),('Helvetica-Bold','arialbd.ttf'),
                   ('Helvetica-Oblique','ariali.ttf'),('Helvetica-BoldOblique','arialbi.ttf'),
                   ('Courier','consola.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(Path('C:/Windows/Fonts')/font)))

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output' / 'pdf'
OUT.mkdir(parents=True, exist_ok=True)
NAVY = colors.HexColor('#142D46')
TEAL = colors.HexColor('#087F8C')
PALE = colors.HexColor('#EDF5F7')
INK = colors.HexColor('#253747')
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleDoc', fontName='Helvetica-Bold', fontSize=25, leading=29, textColor=NAVY, spaceAfter=12))
styles.add(ParagraphStyle(name='SectionDoc', fontName='Helvetica-Bold', fontSize=13, leading=17, textColor=TEAL, spaceBefore=12, spaceAfter=6, keepWithNext=True))
styles.add(ParagraphStyle(name='BodyDoc', fontName='Helvetica', fontSize=10, leading=14, textColor=INK, spaceAfter=7))
styles.add(ParagraphStyle(name='SmallDoc', parent=styles['BodyDoc'], fontSize=8.5, leading=11))
styles.add(ParagraphStyle(name='CellDoc', parent=styles['BodyDoc'], fontSize=9, leading=12, spaceAfter=0))
styles.add(ParagraphStyle(name='CodeDoc', fontName='Courier', fontSize=8, leading=11, textColor=NAVY, backColor=PALE, borderPadding=8, spaceBefore=5, spaceAfter=9))

def p(text): return Paragraph(text, styles['BodyDoc'])
def h(text): return Paragraph(text, styles['SectionDoc'])
def code(text): return Preformatted(text, styles['CodeDoc'])
def table(headers, rows, widths):
    cells = [[Paragraph('<b>'+escape(x)+'</b>',styles['CellDoc']) for x in headers]]
    cells += [[Paragraph(x,styles['CellDoc']) for x in row] for row in rows]
    t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PALE),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),1,TEAL),('LINEBELOW',(0,1),(-1,-1),0.3,colors.HexColor('#D9E3E9')),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    return t
def source(path, token=None):
    f=ROOT/path
    lines=f.read_text(encoding='utf-8').splitlines()
    n=next((i for i,s in enumerate(lines,1) if token and token in s),1)
    return f'<link href="{f.as_uri()}" color="#087F8C">{escape(path)}:{n}</link>'
def ref(file,page,label):
    return f'<link href="{file}#page={page}" color="#087F8C">{label}</link>'
def page(title, subtitle, *items):
    return [Paragraph(title,styles['TitleDoc']),p(subtitle),*items]
def build(filename, label, pages):
    def decorate(c,doc):
        w,ht=doc.pagesize
        c.setFillColor(TEAL); c.rect(0,ht-10,w,10,fill=1,stroke=0)
        c.setFont('Helvetica-Bold',8); c.setFillColor(NAVY)
        c.drawString(42,ht-33,'KATAMARIO / MANUAL TÉCNICO')
        c.setFont('Helvetica',8); c.drawRightString(w-42,ht-33,label)
        c.setStrokeColor(colors.HexColor('#D9E3E9')); c.line(42,38,w-42,38)
        c.setFont('Helvetica',8); c.drawString(42,25,'Prototipo ESP32 · revisión documental 1 · 16/09/2026')
        c.drawRightString(w-42,25,f'{doc.page} / {len(pages)}')
    story=[]
    for i,items in enumerate(pages):
        if i: story.append(PageBreak())
        story.extend(items)
    doc=SimpleDocTemplate(str(OUT/filename),pagesize=(595.28,841.89),leftMargin=42,rightMargin=42,topMargin=55,bottomMargin=53,title=label,author='Katamario',subject='Documentación del código implementado')
    doc.build(story,onFirstPage=decorate,onLaterPages=decorate)
    reader=PdfReader(OUT/filename)
    assert len(reader.pages)==len(pages),(filename,len(reader.pages),len(pages))
    print(filename, len(reader.pages),'pages',sum(len(x.extract_text()) for x in reader.pages),'characters')

main=[
page('main.cpp', '01 / Orquestación del firmware · responsabilidad y estado',
 p('Coordina MPU6050, calibración, seguimiento y publicación serial. Delega la matemática a <b>ball::Motion</b>. No implementa movimiento del juego, Bluetooth ni recepción desde Unity.'),
 p('Fuente: '+source('src/main.cpp')+'. Dependencias: Arduino, Wire, MPU6050 1.4.5, BallMotion.h y ControllerConfig.h.'),
 h('Estado compartido'),
 table(['Elemento','Responsabilidad'],[
 ('address','Dirección I²C seleccionada; valor inicial 0x68.'),
 ('motion / output','Estimación persistente de orientación y última orden calculada.'),
 ('bias / sum / calibrationCount','Sesgo estimado del gyro; suma y contador de muestras de calibración. Bias comienza en cero y se conserva entre reconexiones.'),
 ('alineadoEnUnity','Confirmación futura de alineación; empieza en false. Aún no existe receptor.'),
 ('lastSample / lastOutput','Instantes de procesamiento y publicación.'),
 ('lastProbe / demoStart','Control del reintento de conexión y fase de simulación.')],[162,349]),
 h('Máquina de estados'),
 table(['Estado','Orientación / orden'],[
 ('Waiting','Sensor no disponible o seguimiento invalidado. Identidad de relleno; orden cero.'),
 ('AwaitingAlignment','Lee y estima orientación provisional. Orden cero; espera confirmación o bypass.'),
 ('Calibrating','Acumula muestras quietas. Orientación reiniciada, sin seguimiento; orden cero.'),
 ('Ready','Estima orientación y calcula movimiento real.'),
 ('Demo','Genera mediciones sintéticas; orientación y orden simuladas.')],[162,349]),
 p('<b>Transición normal:</b> Waiting → AwaitingAlignment → Calibrating → Ready. Un fallo de lectura o saturación lleva a Waiting. En Ready/AwaitingAlignment también lo hace una pausa local excesiva.'),
 p('<b>Estado actual:</b> BYPASS_ALIGNMENT=true; la espera de confirmación se atraviesa automáticamente. No omite quietud ni nivelación.')
),
page('Adquisición y conexión','01 / API interna · funciones auxiliares',
 h('bool readSample(Vec &amp;accel, Vec &amp;gyro)'),
 p('Lee 14 bytes contiguos desde ACCEL_XOUT_H con timeout de 20 ms: acelerómetro XYZ, temperatura (ignorada) y giroscopio XYZ. Reconstruye enteros de 16 bits con signo. Devuelve false si la lectura es incompleta o algún eje gyro tiene valor absoluto ≥32700. El llamador debe descartar las salidas ante false.'),
 code('accel = rawAccel / 16384.0f;          // g, rango +/-2 g\ngyro  = rawGyro * pi / (180 * 16.4f); // rad/s, +/-2000 deg/s'),
 p('Las escalas dependen del rango del sensor: no son parámetros de sensibilidad del juego. No se comprueba saturación del acelerómetro explícitamente.'),
 h('bool connectSensor()'),
 p('Prueba 0x68 y 0x69: respuesta I²C, identificación mediante testConnection(), inicialización y configuración. Lee de vuelta rango, divisor, filtro y estado de suspensión. Si todo coincide, limpia la confirmación, reinicia orientación/orden y entra en AwaitingAlignment; devuelve true. Si ninguna dirección funciona, devuelve false.'),
 table(['Configuración aplicada','Valor'],[
 ('Gyro / acelerómetro','±2000 grados/s / ±2 g'),
 ('Filtro interno','DLPF_BW_42: gyro ~42 Hz; acelerómetro ~44 Hz'),
 ('Divisor de muestras','setRate(9): 1000 / (1 + 9) = 100 Hz')],[240,271]),
 h('void calibrate()'),
 p('Consume alineadoEnUnity, entra en Calibrating, limpia contador/suma/orden y reinicia orientación. Solo prepara el proceso: loop() recoge las muestras.'),
 h('void waitForSensor(const char *reason)'),
 p('Limpia confirmación y orden, reinicia orientación, entra en Waiting y registra lastProbe. Publica el motivo con prefijo #. No borra el bias anterior.'),
 h('const char *status()'),
 p('Serializa el estado como waiting, awaiting_alignment, calibrating, ready o demo. No modifica estado ni mediciones.'),
 p('Referencias de implementación: '+source('src/main.cpp','bool readSample')+'; '+source('src/main.cpp','bool connectSensor')+'.')
),
page('Arranque y ciclo','01 / Orden de ejecución y calibración',
 h('setup()'),
 p('Inicia Serial a 115200; Wire en SDA21/SCL22, 100 kHz y timeout de 20 ms. Publica ayuda y esquema CSV, intenta conectar y establece lastSample. Un fallo pasa a Waiting.'),
 h('loop(): secuencia de trabajo'),
 table(['Orden','Operación'],[
 ('1 · Comandos','Lee un carácter: d reinicia Demo; c reconecta/recentra; h imprime ayuda. Los demás caracteres se ignoran. c no confirma alineación.'),
 ('2 · Reconexión','En Waiting, connectSensor() cada 2000 ms. Reinicia el reloj de muestra después del intento.'),
 ('3 · Confirmación','En AwaitingAlignment: si alineadoEnUnity || BYPASS_ALIGNMENT, llama calibrate() y reinicia el reloj de muestra.'),
 ('4 · Muestra','Si elapsed ≥10000 us, procesa una muestra con dt real en segundos. No usa FIFO ni recupera muestras históricas.'),
 ('5 · Publicación','Cada ≥20 ms envía el resultado más reciente. Luego delay(1) cede ejecución.')],[120,391]),
 h('Rama Calibrating'),
 p('Acepta la muestra si |gyro| ≤0.08 rad/s, |ax| y |ay| ≤0.10 g, |az-1| ≤0.10 g y elapsed ≤MAX_SAMPLE_GAP_US. Un rechazo borra suma y contador; no exige nueva confirmación. Al alcanzar 300 aceptadas consecutivas: bias=sum/300, reset() y Ready.'),
 p('La pose requerida es X derecha, Y adelante y Z arriba. La gravedad comprueba nivel, no el frente. Marcas físicas y confirmación del jugador aportan esa referencia. Los ~3 s y tolerancias se revisarán con hardware.'),
 h('Ramas Ready / AwaitingAlignment'),
 p('Si la lectura falla, vuelve a Waiting. Si elapsed supera el límite local, también invalida seguimiento. En caso válido llama update(gyro-bias, accel, dt, mode==Ready). En espera actualiza orientación sin ordenar movimiento.'),
 h('Rama Demo'),
 p('Fases de 2 s: reposo, adelante lento/rápido, reposo, derecha, atrás, izquierda y giro vertical. Transforma gyro sintético y gravedad mediante orientation.inverse().rotate() y ejecuta update(). No valida ruido físico ni fallos del sensor.')
),
page('Telemetría y operación','01 / Contrato K2 · parámetros y validación',
 code('K2,millis,status,right,forward,qw,qx,qy,qz'),
 p('Nueve campos CSV, separados por comas y terminados en LF. right/forward usan 4 decimales; cuaternión 6. millis es el tiempo local de publicación, no de adquisición ni un reloj sincronizado con Unity; desborda aproximadamente cada 49,7 días.'),
 table(['Campo','Semántica'],[
 ('right / forward','Orden adimensional; derecha/adelante positivos. Magnitud conjunta ≤1. Aceptar como movimiento real solo en ready.'),
 ('qw / qx / qy / qz','Cuaternión sensor → referencia; orden w,x,y,z. X derecha, Y adelante, Z arriba. Requiere adaptación de ejes y orden en el receptor Unity.'),
 ('status','awaiting_alignment: orientación provisional; calibrating/waiting: identidad, no pose medida; demo: sintética; ready: relativa a la pose calibrada.')],[147,364]),
 p('Las líneas # son diagnósticos. K2 sustituye a K1. Un receptor debe validar el estado y caducidad de los datos; el timeout de recepción es independiente del límite de muestreo local. Bluetooth y receptor siguen pendientes.'),
 h('Parámetros locales todavía no centralizados'),
 p('SDA_PIN=21; SCL_PIN=22; SAMPLE_US=10000; OUTPUT_MS=20; BYPASS_ALIGNMENT=true. Literales: reintento 2000 ms, calibración 300 muestras y tolerancias, timeout I²C 20 ms, saturación 32700, divisor 9, fases demo 2000 ms y delay(1). Si cambia la tasa de muestra, coordinar divisor y duración de calibración.'),
 h('Herramientas de verificación existentes'),
 p('Entorno usb-smoke conserva el mensaje USB original. Las regresiones PC se ejecutan con test/run-host.ps1. No validan la máquina de estados completa ni el transporte. Compilación y regresiones matemáticas previas correctas; sensor físico aún no validado.'),
 p('Relacionado: '+ref('02_BallMotion_API.pdf',3,'configuración matemática')+' y '+ref('03_Integracion_Main_BallMotion.pdf',1,'mapa de integración')+'.')
)]

motion=[
page('BallMotion.h','02 / Referencia de API matemática',
 p('Módulo header-only en namespace ball. No depende de Arduino, I²C, serial ni Unity. Recibe mediciones físicas y conserva una orientación; devuelve una orden de movimiento.'),
 p('Fuente: '+source('include/BallMotion.h')+'. Configuración compartida: '+source('include/ControllerConfig.h')+'.'),
 h('Convenciones y contrato'),
 p('Gyro en rad/s, acelerómetro en g, dt en segundos. Las entradas se expresan en los ejes del sensor. La referencia calibrada usa X derecha, Y adelante, Z arriba (dextrógira). orientation rota sensor → referencia. Datos finitos y cuaternión unitario son precondiciones.'),
 table(['Tipo / miembro','Contrato'],[
 ('Vec(x,y,z)','Vector de tres float; constructor por defecto en cero. + y - por componente; * escala; norm() calcula magnitud euclídea.'),
 ('cross(Vec a, Vec b)','Producto vectorial a × b. Se usa internamente para la corrección de inclinación.'),
 ('Quat(w,x,y,z)','Identidad por defecto: (1,0,0,0). Constructor explícito por componentes.'),
 ('Quat::operator*','Producto de Hamilton; composición no conmutativa.'),
 ('Quat::inverse()','Devuelve conjugado; equivale a inversa solo para cuaterniones unitarios.'),
 ('Quat::normalize()','Divide por la norma. Requiere norma no nula; no implementa reparación de entradas arbitrarias.'),
 ('Quat::rotate(Vec)','Aplica q·(0,v)·q inverso. Mantiene magnitud si q es unitario.'),
 ('Output','right y forward, cero por defecto. Orden adimensional, no posición ni aceleración.')],[173,338]),
 h('Estado público de Motion'),
 p('<b>orientation:</b> cuaternión persistente. <b>fullSpeed:</b> float mutable, inicialmente pi rad/s (180 grados/s). Debe ser mayor que la zona muerta. reset() restablece solo orientation; no modifica fullSpeed ni calcula bias.'),
 p('No hay guardas generales contra NaN/Inf, cuaternión nulo o fullSpeed inválido. El firmware debe mantener estas precondiciones. No modificar orientation arbitrariamente desde un receptor.')
),
page('Motion::update','02 / Algoritmo y efectos de estado',
 code('Output update(Vec gyro, Vec accel, float dt,\n              bool movementEnabled = true);'),
 h('1. Validación temporal'),
 p('Rechaza dt ≤0 o superior a MAX_SAMPLE_GAP_SECONDS: devuelve Output cero sin modificar orientación. La función no cambia Mode ni reconecta hardware; esas responsabilidades pertenecen a main.'),
 h('2. Corrección de inclinación'),
 p('Copia gyro a corrected. Si la magnitud del gyro es &lt;0.15 rad/s y la del acelerómetro está estrictamente entre 0.9 y 1.1 g, calcula la vertical esperada en ejes locales. Suma cross(accel normalizado, expected) multiplicado por la ganancia 2 por segundo a corrected. Usa constantes de ControllerConfig.h.'),
 p('La condición aproxima reposo, no lo garantiza. La gravedad corrige inclinación, no observa rumbo absoluto. Cerca del reposo reduce contaminación por aceleración de movimiento; no elimina toda vibración.'),
 h('3. Integración de orientación'),
 code('speed = |corrected|\nhalf = speed * dt / 2\ndq = (cos(half), corrected * sin(half) / speed)\norientation = normalize(orientation * dq)'),
 p('Solo integra si speed &gt;1e-8 rad/s, para evitar división prácticamente por cero. Multiplica a la derecha porque el giro es local. Supone velocidad constante durante dt; no reconstruye muestras perdidas. Normalizar corrige error numérico, no deriva física.'),
 h('4. Bloqueo de movimiento y cambio de referencia'),
 p('Si movementEnabled=false, retorna cero después de actualizar orientación. Si true, calcula world=orientation.rotate(gyro). Usa gyro, no corrected: la corrección de inclinación no se agrega directamente a la orden.'),
 h('5. Dirección, zona muerta y escala'),
 code('x = world.y;  y = -world.x\nm = sqrt(x*x + y*y)\nif m <= deadzone: return (0,0)\ngain = min(1, (m-deadzone)/(fullSpeed-deadzone))\nreturn (x/m * gain, y/m * gain)'),
 p('Corresponde al movimiento de la superficie superior: omega × (0,0,R), con radio absorbido en sensibilidad. La diagonal comparte el máximo circular. world.z no produce desplazamiento; al detenerse no se agrega inercia artificial.')
),
page('Configuración y extensión','02 / Parámetros · restricciones · pruebas',
 table(['ControllerConfig.h','Valor inicial / función'],[
 ('MOVEMENT_DEADZONE_DEG_PER_SEC','2 grados/s; zona muerta radial de salida. Su equivalente RAD_PER_SEC se deriva automáticamente.'),
 ('TILT_MAX_GYRO_RAD_PER_SEC','0.15 rad/s; máximo para habilitar corrección de inclinación (comparación estricta).'),
 ('TILT_MIN_ACCEL_G / TILT_MAX_ACCEL_G','0.9 / 1.1 g; ventana estricta de magnitud acelerométrica.'),
 ('TILT_CORRECTION_GAIN_PER_SEC','2 por segundo; fuerza de corrección hacia la vertical medida.'),
 ('MAX_SAMPLE_GAP_US','50000 us; pausa local máxima admitida. MAX_SAMPLE_GAP_SECONDS se deriva de este valor.')],[238,273]),
 p('No confundir el límite local de muestreo con latencia Bluetooth. Revisar ruido de la caja, umbrales de reposo, fuerza de corrección y tiempos cuando haya hardware. fullSpeed aún es miembro de Motion, no constante centralizada.'),
 h('Placeholder: onVerticalRotation(float)'),
 p('Función vacía y sin llamadas. Su parámetro futuro es velocidad angular con signo sobre la vertical fija (world.z), en rad/s. No usar gyro.z local. No produce eventos, telemetría extra ni acción del juego.'),
 h('Limitaciones del modelo'),
 p('No estima posición, rumbo absoluto ni bias; main calcula el sesgo. Requiere pose física conocida al reiniciar para que identidad corresponda al jugador. Aceleración adicional, sesgo térmico y pérdidas de muestra pueden degradar orientación. La corrección puede modificar cómo se proyectan los giros, aunque no añade movimiento sintético.'),
 h('Regresiones de host'),
 p('test/motion_host.cpp comprueba reposo, ruido, signos, intensidad, diagonal, giro vertical, diez vueltas, cambios de referencia, corrección de inclinación, ausencia de corrección ficticia del rumbo, dt inválido, reset y preview con movimiento bloqueado. Ejecutar test/run-host.ps1; requiere g++ configurado. No sustituye pruebas de hardware.'),
 p('Uso desde firmware: '+ref('03_Integracion_Main_BallMotion.pdf',1,'mapa de llamadas y miembros')+'. Formato de publicación: '+ref('01_Main_Manual.pdf',4,'contrato serial K2')+'.')
)]

integration=[
page('Main ↔ BallMotion','03 / Mapa de integración y trazabilidad',
 p('Cada fila vincula un uso concreto del módulo matemático en main con su contrato. Los enlaces azules abren el código local o el PDF asociado. Mantener los tres PDF en la misma carpeta para los enlaces entre manuales; la apertura depende del visor.'),
 table(['Uso en main','Elemento de BallMotion / efecto'],[
 (source('src/main.cpp','ball::Motion motion'),ref('02_BallMotion_API.pdf',1,'Motion')+': instancia global; orientation persiste entre muestras. fullSpeed usa su valor por defecto.'),
 (source('src/main.cpp','ball::Vec bias'),ref('02_BallMotion_API.pdf',1,'Vec')+': bias, sum y muestras. Construcción por componentes, escala, suma/resta y norm().'),
 (source('src/main.cpp','ball::Output output'),ref('02_BallMotion_API.pdf',1,'Output')+': almacenamiento de la última orden; {} anula ambos ejes.'),
 (source('src/main.cpp','bool readSample'),ref('02_BallMotion_API.pdf',1,'Vec y pi')+': convierte raw a g/rad/s con constructor y multiplicación escalar.'),
 (source('src/main.cpp','void calibrate'),ref('02_BallMotion_API.pdf',1,'Motion::reset')+': identidad al iniciar calibración. También se usa al esperar sensor, conectar, entrar en demo y completar calibración.'),
 (source('src/main.cpp','auto inverse'),ref('02_BallMotion_API.pdf',1,'Quat::inverse / rotate')+': demo convierte giro fijo y gravedad a ejes del sensor simulado.'),
 (source('src/main.cpp','output=motion.update(inverse'),ref('02_BallMotion_API.pdf',2,'Motion::update')+': demo; cuarto argumento omitido, movimiento habilitado por defecto.'),
 (source('src/main.cpp','if (gyro.norm()'),ref('02_BallMotion_API.pdf',1,'Vec::norm / operadores')+': valida quietud, suma gyro y obtiene bias=sum/300.'),
 (source('src/main.cpp','else output=motion.update'),ref('02_BallMotion_API.pdf',2,'Motion::update')+': real; gyro-bias, accel, dt y habilitación solo en Ready.'),
 (source('src/main.cpp','const ball::Quat &q'),ref('02_BallMotion_API.pdf',1,'Motion::orientation / Quat')+': lectura de w,x,y,z para publicar K2.')],[210,301]),
 h('Uso indirecto y extensión sin uso'),
 p('cross(), multiplicación de Quat y normalize() son internos a la matemática, no llamadas directas de main. onVerticalRotation() no se invoca. Ambos archivos usan ControllerConfig.h; no es una dependencia del transporte.')
),
page('Flujos y límites de integración','03 / Contratos entre módulos',
 h('Datos reales'),
 code('MPU6050 -> readSample() -> gyro [rad/s], accel [g]\n        -> gyro - bias -> Motion::update(..., dt, enabled)\n        -> Output + orientation -> Serial K2 -> receptor futuro'),
 table(['Punto de ejecución','Entradas / resultados'],[
 ('AwaitingAlignment','update(..., false): orientación provisional activa; orden cero. Bias previo o cero inicial. Confirmación/bypass decide cuándo calibrar.'),
 ('Calibrating','No llama update(). Acumula muestras aceptadas; al completar, guarda bias, reinicia orientación y cambia a Ready.'),
 ('Ready','update(..., true): orientación y orden reales. Dirección en marco del jugador; intensidad normalizada.'),
 ('Demo','Entradas sintéticas; update() con movimiento habilitado. No lee sensor ni aplica bias real.'),
 ('Waiting / fallo','No actualiza orientación. main reinicia a identidad y anula salida; el estado indica que no es pose medida.')],[155,356]),
 h('Propiedad de las decisiones'),
 p('<b>main:</b> conexión, temporización, estado, bias, confirmación y publicación. <b>BallMotion:</b> inclinación, integración, cambio de ejes, zona muerta y normalización. <b>Unity futuro:</b> recepción, UI de alineación y aplicación del movimiento del juego.'),
 h('Frontera futura con Unity'),
 p('La orientación enviada es relativa y no prueba por sí sola el frente físico. El jugador alinea marcas de frente/arriba y confirma. La futura recepción deberá establecer alineadoEnUnity=true en AwaitingAlignment; main consume la confirmación al calibrar. Con bypass=true no espera. No hay implementación Bluetooth ni de Unity en esta entrega.'),
 p('El receptor debe adaptar ejes/orden del cuaternión, ignorar diagnósticos #, distinguir demo y estados inválidos, y anular movimiento ante datos caducados. No asumir continuidad visual al reset: el cuaternión pasa a identidad.'),
 h('Próximos pasos: validación de integración'),
 p('<b>1. Demo sin sensor:</b> en PlatformIO, entorno nodemcu-32s, ejecutar Build, Upload y Monitor (COM4, 115200); enviar d. Revisar juntos K2/demo: orden cero en reposo y giro vertical, signos correctos y mayor intensidad en avance rápido. La orientación debe cambiar al girar. c sale de demo. Esta sesión con el usuario sigue pendiente.'),
 p('<b>2. Hardware real:</b> validar montaje, calibración, ruido, zona muerta y tiempos de muestreo. Al implementar Bluetooth, medir también transmisión y recepción; no confundir su latencia con el intervalo local del sensor.'),
 p('Fuentes de esta documentación: código local de main.cpp, BallMotion.h, ControllerConfig.h, platformio.ini y test/motion_host.cpp. Describe el estado implementado, no una API futura prometida.')
)]

if __name__ == '__main__':
    build('01_Main_Manual.pdf','01 / main.cpp',main)
    build('02_BallMotion_API.pdf','02 / BallMotion.h',motion)
    build('03_Integracion_Main_BallMotion.pdf','03 / Integración',integration)
    for f in ['src/main.cpp','include/BallMotion.h','include/ControllerConfig.h']:
        print(f,hashlib.sha256((ROOT/f).read_bytes()).hexdigest())
