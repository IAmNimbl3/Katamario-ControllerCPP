# AK09911C opcional: lectura y corrección de rumbo

Estado (2026-11-10): driver verificado en la placa y correccion provisional
habilitada en `MagnetometerConfig.h`. Ambos sensores permanecen fijos entre si.
No sustituye al MPU6050 ni cambia el CSV K3 de Unity.

La calibracion provisional proviene de `output/tests/2026-11-10-magnetometer/`:
ajuste afin conjunto contra la orientacion del MPU, con descomposicion polar
para separar montaje y compensacion magnetica. La escala global se normaliza
por determinante; no es una medicion independiente de la intensidad terrestre.
Error de rumbo sobre el conjunto ajustado: mediana 7,6 grados, percentil 95
18,9 grados. Es ayuda provisional, no alineacion de precision validada.
Para deshabilitar solo la correccion: `calibration.valid=false`.

## Estructura

- `Ak09911.h`: driver portable; identifica AK09911 (WIA1=0x48, WIA2=0x05),
  prueba 0x0C/0x0D, aplica sensibilidad de fábrica y lee XYZ en microteslas.
- `Ak09911Wire.h`: adaptador del bus Wire existente. No cambia reloj ni pines.
- `BallOrientation.h`: calibración magnética del montaje y corrección gradual
  exclusivamente del rumbo del cuaternión de `BallMotion`.
- `MagnetometerConfig.h`: habilitación y calibración física del conjunto.
- `main.cpp`: inicializa, entrega lecturas nuevas en Ready y reinicia la referencia
  al recalibrar, entrar en demo o perder el MPU. No se modifica `BallMotion.h`.

## Activación progresiva

1. Verificar alimentación y niveles de la placa MCU9911 real. Este código no
   certifica su electrónica. Mantener el bus compartido a 100 kHz y lógica 3,3 V.
2. `magneticConfig::ENABLED=false` permite deshabilitar el modulo: sin tráfico I2C
   adicional ni cambio en las lecturas/movimiento del MPU6050.
3. Habilitar para probar identidad y lecturas; dejar `calibration.valid=false`.
   Con `g` se alterna diagnóstico USB a 5 Hz, solo durante Ready. No corrige aún.
4. Medir bias hard-iron, matriz soft-iron y orientación relativa de ambos sensores
   en el montaje final. Introducirlos en `MagnetometerConfig.h`; recién entonces
   marcar `valid=true`. No se implementa todavía un asistente de adquisición ni
   ajuste de estos coeficientes: no inventar valores ni validar la identidad.
5. Validar sentidos, estabilidad y retorno a la referencia. Los parámetros físicos
   del filtro están en `BallOrientation::Settings`, configurados desde
   `magneticConfig::settings()`; no son sensibilidad de juego.

## Algoritmo y límites

El driver usa modo continuo de 100 Hz. Lee ST1 y el bloque HXL..ST2 completo;
ST2 es obligatorio para liberar la muestra. Descarta overflow y lecturas parciales.
Aplica la fórmula específica AK09911: raw * (1 + ASA/128) * 0,6 uT.
No confundir con AK8963, que usa otra fórmula. DOR indica muestras anteriores
perdidas; la lectura actual puede utilizarse.

La calibración física aplica `mounting.rotate(matrix * (field - bias))`, en ese
orden. Se transforma el campo al marco global con el cuaternión del MPU. Tras
30 muestras válidas consecutivas y quietas se conserva una referencia magnética
de la pose que eligió el jugador. No se fuerza norte magnético ni se identifica
la pantalla automáticamente. La corrección se aplica antes de la integración MPU
del ciclo; usa su estimación de orientación previa (desfase de un ciclo, limitado
por la condición de reposo). La salida y el cuaternión enviados son del mismo ciclo.

Solo corrige con giro <=0,15 rad/s, muestras separadas por <=50 ms, campo de
10..100 uT y componente horizontal >=5 uT. Rechaza cambios de magnitud >20%
respecto de la referencia o errores de rumbo >45 grados. Ganancia 0,5/s,
corrección máxima 0,05 rad/s. Valores iniciales para medir en banco.

### Corrección durante pausas naturales

Antes de corregir requiere **2,5 segundos continuos** de baja velocidad y campo
magnético estable. La duración se configura con `quietSecondsBeforeCorrection`.
La estabilidad compara dirección del campo global (tolerancia de 3 grados) y
magnitud (5%) con el inicio de la ventana. Al compensar la orientación del MPU,
un giro físico lento no equivale a un cambio del campo ambiental.

Un giro superior al umbral reinicia la espera, incluso si ocurre entre dos
lecturas del magnetómetro. También la reinician muestras inválidas, overflow,
interrupciones >50 ms, variaciones excesivas o desactivar el filtro/calibración.
Un ciclo normal sin dato nuevo no acumula tiempo por sí solo. El tiempo se mide
entre muestras nuevas, no por cantidad de ciclos de Unity ni paquetes Bluetooth.

Una vez cumplida la espera, corrige gradualmente mientras las condiciones se
mantengan. La ventana de estabilidad se transforma junto con la corrección para
no confundir el propio ajuste con una perturbación. La referencia inicial nunca
se sustituye por la orientación de la pausa: si el ángulo real es 40 grados y el
estimado 45, debe corregir hacia 40, no hacia cero. Una perturbación estable puede
seguir siendo indistinguible de error de rumbo; no es una garantía de alineación.

### Responsabilidad de Unity

El ESP32 combina los sensores y corrige su estimación física antes de calcular
movimiento y emitir K3. Unity recibe `right`, `forward` y el cuaternión ya
corregidos: no debe aplicar una segunda corrección magnética. No hace falta
cambiar el receptor K3 ni enviar el campo magnético para este comportamiento.
La referencia visual del nivel, UI y decisiones de juego pertenecen a Unity.
No se agregó persistencia de referencia entre reinicios ni se cambió el flujo
actual de `c`: ese comando sigue solicitando una calibración explícita nueva.

La corrección es una rotación por izquierda alrededor del Z global: no cambia la
inclinación ni suma una velocidad ficticia al giroscopio/retorcimiento. Durante
movimiento normal se sigue usando el MPU; el magnetómetro ayuda cerca del reposo.
No garantiza detectar perturbaciones que roten el campo sin cambiar su magnitud.
No recupera automáticamente una referencia muy desviada: requiere realineación y `c`.

## Fallos y diagnóstico

Ausencia/error I2C desactiva el driver hasta inicio o comando `c`, sin bucle de
reintentos que bloquee el MPU. No-data/overflow nunca reutilizan el último campo.
La pérdida del magnetómetro conserva el cuaternión actual y continúa con el MPU;
no provoca Ready ni reemplaza las condiciones de calibración del MPU.
Si un fallo físico retiene el bus compartido, también puede fallar el MPU: se
mantiene la protección existente de pausa/recalibración, no se puede aislar por software.

`# MAG,ms,result,state,mx_uT,my_uT,mz_uT` (solo USB; no cambia K3):

- result: 0 Sample, 1 NotReady, 2 Overflow, 3 IoError, 4 Offline.
- state: 0 Disabled, 1 Uncalibrated, 2 Waiting, 3 Referenced, 4 Corrected, 5 Rejected.
- Los campos cero con result distinto de 0 NO son una medición.
- `c` reinicia ambos sensores y obliga a recalibrar el MPU y tomar nueva referencia.

## Validación sin hardware

Compilar y ejecutar `test/motion_host.cpp` y `test/magnetometer_host.cpp` con un
compilador C++11 o superior y `-Iinclude`. El segundo simula el bus y comprueba
identidad, modos, conversión, ST2, fallos y corrección matemática de orientación.
Compilar `pio run -e nodemcu-32s`. Esto no valida el módulo físico, interferencias,
calibración magnética ni temporización real sobre el bus compartido.

Referencia: AKM AK09911 MS1526-E-01 (2014/7), secciones 6-8:
https://www.ecsimple.com/files/b7/ak09911c.pdf
