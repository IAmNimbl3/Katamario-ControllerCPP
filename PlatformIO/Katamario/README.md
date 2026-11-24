# Kyuboru

Controlador esférico para un juego inspirado en Katamari. El jugador hace rodar una pelota dentro de una base fija: la dirección y rapidez del giro se traducen en una orden de movimiento. Al frenar la pelota, la orden vuelve a cero.

El MPU6050, el ESP32 y la alimentación estarán dentro de la esfera, girando juntos. La conexión final será por Bluetooth. Unity recibirá la información y aplicará el movimiento y la física del juego; este proyecto se ocupa del controlador.

## Estado del prototipo

La prueba USB inicial funcionó en la placa. El firmware del controlador incluye lectura del sensor, calibración, estimación de orientación y una demo sin sensor. Compiló y pasó pruebas matemáticas en PC.

El 14/10/2026 se cargó y validó la demo sin sensor en el ESP32 por COM4: dos ciclos completos, 1650 paquetes con intervalos de 20 ms, direcciones y velocidades esperadas, cuaterniones normalizados y retorno a espera con salida cero. Resultado: aprobado. Esto no valida el sensor físico, Bluetooth ni Unity. [Resultados de la prueba](output/tests/2026-10-14-demo/result.json) y [registro serie](output/tests/2026-10-14-demo/serial.log).

El firmware ya incorpora Bluetooth clásico SPP bajo el nombre `Kyuboru` y un receptor de prueba independiente de Unity. Con Bluetooth inicializado, la demo volvió a pasar por USB: dos ciclos, 1650 paquetes y cadencia de 20 ms. [Resultados](output/tests/2026-10-14-bluetooth-usb/result.json). El receptor pasó cinco pruebas automatizadas de lectura y timeout.

Bluetooth, MPU6050, magnetómetro e integración Unity ya se probaron con el controlador. La marca física define el adelante inicial y el magnetómetro ayuda a conservarlo. El firmware actual emite K4. Los registros anteriores se conservan como evidencia histórica.

## Documentación

Integración opcional del AK09911C: [magnetómetro y corrección de rumbo](docs/Magnetometro.md).
Habilitada para el montaje calibrado: corrección suave tras 2,5 segundos de baja velocidad y campo estable.

Descripción del concepto: [Kyuboru: el juego](output/pdf/05_Descripcion_del_Juego.pdf).

Ampliación del firmware: [comunicación y receptor de prueba](docs/Comunicacion.md). Los PDFs técnicos todavía no incluyen esta ampliación.

Documentación PDF, con referencias cruzadas:

- [Main: funcionamiento del firmware](output/pdf/01_Main_Manual.pdf)
- [BallMotion: referencia de API y matemática](output/pdf/02_BallMotion_API.pdf)
- [Integración: usos de BallMotion desde Main](output/pdf/03_Integracion_Main_BallMotion.pdf)
- [Flujo de uso y bocetos del control](output/pdf/04_Flujo_Uso_y_Bocetos.pdf)

## Verificación actual

Las nuevas tolerancias y la continuidad de calibración requieren prueba física cuando se disponga del controlador. Compilar no actualiza la placa: hay que cargar el firmware. Los PDF históricos se conservan sin modificar; consultar los Markdown de comunicación y magnetómetro para la especificación vigente.
