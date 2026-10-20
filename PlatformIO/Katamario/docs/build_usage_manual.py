"""Generate the illustrated operating-flow manual; reuse the technical style."""
from build_manuals import *
from reportlab.platypus import Flowable, Image
from reportlab.lib.styles import ParagraphStyle
import math

class OperatingFlow(Flowable):
    def __init__(self):
        super().__init__()
        self.width=511
        self.height=440
    def draw(self):
        c=self.canv
        def label(text,x,y,w,size=9):
            style=ParagraphStyle('diagram',fontName='Helvetica',fontSize=size,leading=size+3,textColor=INK,alignment=1)
            item=Paragraph(text,style)
            _,ht=item.wrap(w,100)
            item.drawOn(c,x,y-ht/2)
        def box(x,y,w,ht,text,fill=PALE):
            c.setFillColor(fill); c.setStrokeColor(TEAL); c.setLineWidth(1)
            c.roundRect(x,y,w,ht,7,fill=1,stroke=1)
            label(text,x+7,y+ht/2,w-14)
        def arrow(points):
            c.setStrokeColor(TEAL); c.setFillColor(TEAL); c.setLineWidth(1.1)
            path=c.beginPath(); path.moveTo(*points[0])
            for point in points[1:]: path.lineTo(*point)
            c.drawPath(path)
            a,b=points[-2:]; angle=math.atan2(b[1]-a[1],b[0]-a[0]); length=6
            path=c.beginPath();path.moveTo(*b)
            path.lineTo(b[0]-length*math.cos(angle-.5),b[1]-length*math.sin(angle-.5))
            path.lineTo(b[0]-length*math.cos(angle+.5),b[1]-length*math.sin(angle+.5));path.close()
            c.drawPath(path,fill=1,stroke=0)
        x,w=135,245
        box(x,395,w,35,'<b>ENCENDER EL CONTROL</b>')
        box(x,315,w,48,'<b>¿Sensor disponible y configurado?</b><br/>Comprobar MPU6050')
        box(x,225,w,60,'<b>ALINEAR Y CONFIRMAR</b><br/>Frente hacia pantalla + arriba nivelado<br/>AwaitingAlignment')
        box(x,135,w,60,'<b>MANTENER QUIETA LA PELOTA</b><br/>300 muestras válidas (~3 s)<br/>Calibrating')
        box(x,40,w,65,'<b>CONTROL LISTO · Ready</b><br/>Girar para mover; frenar para parar<br/>Enviar orientación + orden continuamente')
        arrow([(257,395),(257,363)])
        arrow([(257,315),(257,285)]);label('SÍ',269,299,30,8)
        arrow([(257,225),(257,195)]);label('Confirmación o bypass',270,210,125,8)
        arrow([(257,135),(257,105)]);label('Calibración válida',269,120,125,8)
        box(0,305,106,69,'<b>ESPERAR</b><br/>Movimiento cero<br/>Reintentar en 2 s')
        arrow([(135,339),(106,339)]);label('NO',107,352,26,8)
        arrow([(53,374),(53,383),(160,383),(160,363)])
        box(405,62,106,110,'<b>FALLO LOCAL</b><br/>Lectura, saturación<br/>o pausa excesiva<br/><br/>Salida cero;<br/>volver a conectar')
        arrow([(380,72),(405,72)])
        arrow([(458,172),(458,339),(380,339)])
        label('También desde<br/>espera de<br/>alineación',383,239,68,8)
        box(0,131,106,70,'Si se mueve<br/>o no está nivelada:<br/><b>reiniciar conteo</b>')
        arrow([(135,165),(106,165)])
        arrow([(53,131),(53,118),(160,118),(160,135)])

pages=[
page('Flujo de uso del control','04 / Operación · arranque, alineación y recuperación',
 p('La caja permanece fija. El jugador gira la esfera con las manos; el ESP32 interpreta ese giro y Unity aplica el movimiento del juego. El diagrama resume el flujo real del firmware y la confirmación prevista desde Unity.'),
 OperatingFlow(),
 h('Qué está activo y qué falta'),
 p('<b>Implementado:</b> estados, calibración, orientación, orden y salida USB. <b>Pendiente:</b> transporte Bluetooth, recepción de confirmación e interfaz de Unity. Hoy BYPASS_ALIGNMENT=true permite iniciar la calibración sin confirmación; no omite la comprobación de quietud y nivel.'),
 p('La confirmación indica que el jugador alineó físicamente las marcas. El sensor no comprueba por sí mismo el frente. Una deriva gradual puede no disparar ningún fallo: el recentrado manual sigue siendo necesario cuando se advierta desalineación.')
),
page('La pelota en su caja','04 / Boceto industrial conceptual · exterior y corte',
 Image(str(ROOT/'docs/assets/control-concepto.png'),width=511,height=511*1024/1536),
 table(['Vista exterior · izquierda','Vista interna · derecha'],[
 ('Esfera accesible desde arriba, base fija y marcas visuales para recuperar la pose inicial. La flecha identifica el frente y el punto permite reconocer arriba.',
  'ESP32, MPU6050 y batería sujetos a un soporte solidario con la esfera. Todo gira junto; no hay cable entre pelota y caja. Apoyos ilustrativos permiten el giro libre.')],[255.5,255.5]),
 h('Alcance del boceto'),
 p('Imagen generada con IA como propuesta visual. No es un plano mecánico, eléctrico ni una selección de componentes. No fija dimensiones, materiales, tolerancias ni cantidad/tipo definitivo de apoyos. Las placas dibujadas no representan modelos verificados.'),
 p('En el montaje real, ubicar el sensor lo más cerca posible del centro, mantenerlo rígido respecto de la carcasa y revisar balance, acceso para mantenimiento, retención y fricción. La posición aparente del sensor en este corte sirve para mostrarlo; no especifica su ubicación exacta.'),
 p('Las marcas deben corresponder al montaje real del sensor: X derecha, Y adelante, Z arriba al calibrar. Usar la pantalla como referencia de frente y la base como referencia fija. El diseño de la marca final se validará con el prototipo.')
),
page('Interacción del jugador','04 / Guía del jugador y comportamiento esperado',
 table(['Acción del jugador','Respuesta prevista'],[
 ('Alinear las marcas','Colocar el frente hacia la pantalla y el indicador de arriba en su pose de referencia; la caja no se mueve.'),
 ('Confirmar alineación','Unity enviará la confirmación; el firmware iniciará calibración. Hoy se usa el bypass o la variable preparada, sin receptor implementado.'),
 ('Mantener quieta la pelota','Completar ~3 s de muestras aceptadas. Si se mueve o sale de nivel, reinicia la acumulación.'),
 ('Rodar adelante / atrás / costados','Producir una orden con la dirección y rapidez del giro. La orientación también se transmite.'),
 ('Frenar / soltar','Al detenerse, orden cero. Soltar no equivale a detener: si la esfera sigue girando, continúa la orden.'),
 ('Retorcer sobre la vertical','Función prevista: al girar sobre el eje vertical y alcanzar un umbral de velocidad, enviar una señal para un control especial independiente del movimiento de la pelota en el juego. Hoy solo cambia la orientación: el placeholder está vacío y no se llama. El umbral, la emisión de la señal y la acción especial aún no están implementados ni definidos.'),
 ('Notar desalineación o sufrir fallo','Solicitar recentrado, alinear y confirmar de nuevo. La operación c de consola reinicia el proceso; no confirma la pose.')],[174,337]),
 h('Comunicación en ambos sentidos'),
 code('CONTROL -> UNITY: orientación + dirección/intensidad + estado\nUNITY -> CONTROL: solicitud de recentrado / confirmación (futuro)'),
 p('En AwaitingAlignment se puede visualizar orientación provisional mientras el desplazamiento está bloqueado. No equivale a detección automática de la marca. La calibración reinicia el cuaternión: la vista puede saltar a la referencia. Bluetooth y esa UI todavía no están implementados.'),
 p('Bocetos: herramienta integrada image_gen. Prompt y PNG conservados en docs/assets/. Este documento no modifica el firmware ni sustituye las referencias de API.')
)]

if __name__=='__main__':
    build('04_Flujo_Uso_y_Bocetos.pdf','04 / Flujo y concepto físico',pages)
