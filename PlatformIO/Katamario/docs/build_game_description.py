"""Editorial game concept; intentionally separate from technical manuals."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor, Color
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/pdf/05_Descripcion_del_Juego.pdf'
for name,font in [('Game','arial.ttf'),('GameBold','arialbd.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(Path('C:/Windows/Fonts')/font)))
pdfmetrics.registerFontFamily('Game',normal='Game',bold='GameBold',italic='Game',boldItalic='GameBold')
CREAM=HexColor('#F7F2E9'); INK=HexColor('#24364A'); SKY=HexColor('#79B5D3')
CORAL=HexColor('#BA563E'); GREEN=HexColor('#71804D'); WHITE=HexColor('#FFFFFF')
W,H=595.28,841.89
c=canvas.Canvas(str(OUT),pagesize=(W,H))
c.setTitle('Kyuboru | Descripción del juego')
c.setAuthor('Kyuboru')
c.setSubject('Concepto de juego, experiencia e identidad visual')

def text(s,x,top,width,size=11,leading=16,color=INK,bold=False):
    st=ParagraphStyle('g',fontName='GameBold' if bold else 'Game',fontSize=size,leading=leading,textColor=color)
    p=Paragraph(s,st); _,height=p.wrap(width,H)
    assert top+height<790,(s,top,height)
    p.drawOn(c,x,H-top-height)
    return top+height
def rect(x,top,width,height,color,radius=0):
    c.setFillColor(color);c.setStrokeColor(color)
    c.roundRect(x,H-top-height,width,height,radius,fill=1,stroke=0)
def base(n,label):
    rect(0,0,W,H,CREAM)
    text('KYUBORU',38,26,170,10,12,bold=True)
    text(label,285,26,272,9,12,color=CORAL)
    c.setStrokeColor(SKY);c.setLineWidth(.6);c.line(38,55,W-38,55)
    text('CONCEPTO DE JUEGO · SEPTIEMBRE 2026',38,800,400,8,10)
    # Footer intentionally outside the main text layout bounds.
def footer(n):
    c.setFillColor(INK);c.setFont('Game',8)
    c.drawString(38,24,'CONCEPTO DE JUEGO · SEPTIEMBRE 2026')
    c.drawRightString(W-38,24,f'{n} / 4')
def page(n,label):
    rect(0,0,W,H,CREAM)
    text('KYUBORU',38,26,170,10,12,bold=True)
    text(label,285,26,272,9,12,color=CORAL)
    c.setStrokeColor(SKY);c.setLineWidth(.6);c.line(38,55,W-38,55)
    footer(n)

page(1,'01 / LA IDEA')
text('KYUBORU',38,85,519,43,49,bold=True)
text('Rodar con las manos.<br/>Recolectar en pantalla.',38,145,500,27,33,bold=True)
text('Un juego inspirado en Katamari en el que un personaje empuja una pelota para recoger objetos del entorno. Su rasgo distintivo es el control: el jugador hace girar una esfera real y reproduce con las manos la acción que ve en pantalla.',38,225,505,12,17)
rect(38,309,519,88,SKY,14)
text('LA FANTASÍA CENTRAL',56,322,480,10,13,bold=True)
text('Sentir que sos vos quien hace rodar la pelota del juego, mediante un gesto físico continuo y reconocible.',56,344,480,15,20,bold=True)
text('Cinco pilares de la experiencia',38,417,500,19,24,bold=True)
pillars=[('01','Una acción que se entiende','Empujar y hacer rodar: la acción física del jugador acompaña la acción del personaje.'),
         ('02','Movimiento y recolección','Dirigir la pelota por el entorno para entrar en contacto con objetos y recogerlos.'),
         ('03','Humor con identidad propia','Una lectura paródica, simpática y argentina; reconocible como inspiración, sin repetir literalmente al personaje de referencia.'),
         ('04','Comer, crecer y abrir caminos','Comer te hace más grande. Ser más grande te da acceso a lugares nuevos.'),
         ('05','Nuevos lugares, nuevas posibilidades','Los nuevos lugares dan acceso a niveles temáticos con más mecánicas. Por ahora, sólo se contempla la mecánica de giro sobre el eje vertical.')]
y=457
for num,title,body in pillars:
    text(num,38,y,40,17,20,color=CORAL,bold=True)
    text(title,88,y,460,12,16,bold=True)
    end=text(body,88,y+23,460,10.5,15)
    y=end+14
c.showPage()

page(2,'02 / CÓMO SE JUEGA')
text('El gesto se convierte<br/>en recorrido',38,82,515,29,34,bold=True)
text('El personaje empuja la pelota; el jugador decide hacia dónde avanzar y con qué intensidad haciendo rodar el controlador. La recolección sucede a través de la pelota en el escenario.',38,169,510,12,18)
steps=[('ELEGIR','Reconocer objetos y orientar el recorrido hacia ellos.'),('RODAR','Girar la esfera para conducir la pelota del juego.'),('RECOGER','Alcanzar objetos con la pelota y continuar el recorrido.')]
for i,(title,body) in enumerate(steps):
    x=38+i*178
    rect(x,249,163,109,WHITE,10)
    text(title,x+13,264,137,11,15,color=CORAL,bold=True)
    text(body,x+13,290,137,10,14)
text('Un control que se toca',38,384,515,19,24,bold=True)
text('La esfera gira dentro de una caja fija, como un trackball de gran tamaño. El jugador trabaja sobre su superficie sin desplazar la caja. Todo el conjunto está pensado para usarse de forma inalámbrica.',38,420,515,11,16)
text('<b>Seguir girando es seguir dando movimiento.</b> Mantener la pelota en una orientación no equivale a sostener un stick. Un giro más rápido aumenta la intensidad hasta un máximo; las diagonales conservan ese mismo máximo.',38,482,515,11,16)
text('Al frenar la esfera, cesa la orden de movimiento. Si sigue rodando después de soltarla, continúa la orden. El comportamiento físico final del personaje y la pelota virtual pertenece al juego.',38,558,515,11,16)
rect(38,638,519,101,HexColor('#E7EBCF'),12)
text('UN GESTO ESPECIAL RESERVADO',55,652,480,10,14,color=GREEN,bold=True)
text('Girar sobre el eje vertical a cierta velocidad podrá activar una acción especial distinta del desplazamiento. El gesto está previsto; su efecto dentro del juego todavía no está definido.',55,678,480,11,16)
c.showPage()

page(3,'03 / IDENTIDAD Y ALCANCE')
text('El Pibe Rodante',38,81,519,29,35,bold=True)
text('Boceto 01 / Variante horizontal',38,126,519,11,15,color=CORAL)
art=ROOT/'docs/assets/pibe-rodante-exploracion.png'
c.drawImage(str(art),38,H-165-346,width=519,height=346,preserveAspectRatio=True,mask='auto')
text('Referencia recuperada de “Generar personaje T pose”. Exploración previa; no representa un diseño final aprobado.',38,518,519,8.5,12,color=CORAL)
text('La búsqueda apunta a un personaje caricaturesco con tinte argentino: cuerpo redondeado, panza visible y una cabeza inspirada en un chorizo o choripán. El piluso, la ropa albiceleste y las proporciones simples aparecen en las exploraciones visuales.',38,553,519,11,16)
text('Se exploraron cabezas horizontales y verticales, manos más definidas, bigote y barba. El objetivo expresado es conservar el guiño paródico y construir una silueta propia. Ninguna de esas variantes se presenta aquí como cierre definitivo.',38,623,519,10.5,15)
text('<b>Progresión definida:</b> comer permite crecer y acceder a nuevos lugares y niveles temáticos. Quedan abiertos la historia, las temáticas concretas, los umbrales de crecimiento, la puntuación, las condiciones de victoria o derrota y el efecto de la acción vertical.',38,690,519,10,14)
text('Base: “Proyecto Katamari Arduino”, “Generar personaje T pose” y las decisiones de esta conversación. Este documento describe el concepto; no es un manual técnico ni un listado de tareas.',38,751,519,8.5,11)
c.linkURL('https://chatgpt.com/c/6a95ffe8-1538-83e9-8e36-f515af84ca69',(38,H-779,270,H-751),relative=0)
c.linkURL('https://chatgpt.com/c/6a9c11a3-eae0-83e9-b45d-6e2506ee3cbd',(270,H-779,557,H-751),relative=0)
c.showPage()
page(4,'04 / BOCETOS DEL PERSONAJE')
text('El Pibe Rodante',38,81,519,29,35,bold=True)
text('Boceto 02 / Variante vertical',38,126,519,11,15,color=CORAL)
art_vertical=ROOT/'docs/assets/pibe-rodante-vertical.png'
c.drawImage(str(art_vertical),38,H-165-389.25,width=519,height=389.25,preserveAspectRatio=True,mask='auto')
text('Referencia recuperada de “Generar personaje T pose”. Boceto de exploración; no representa un diseño final aprobado.',38,566,519,8.5,12,color=CORAL)
text('La variante vertical explora una cabeza alargada hacia arriba, manteniendo el piluso, la ropa albiceleste y la panza visible. Se presenta junto a la variante horizontal como alternativa de silueta para el mismo personaje.',38,610,519,11,16)
rect(38,691,519,67,HexColor('#E7EBCF'),12)
text('DOS BOCETOS, UN PERSONAJE EN EXPLORACIÓN',55,704,480,10,14,color=GREEN,bold=True)
text('Ambas variantes son referencias de diseño, no personajes distintos ni una selección definitiva.',55,726,480,10.5,15)
c.save()
r=PdfReader(OUT)
assert len(r.pages)==4
print(OUT, len(r.pages),'pages')
