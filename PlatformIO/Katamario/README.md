# Kyuboru

Controlador esférico para un juego inspirado en Katamari. El jugador hace rodar una pelota dentro de una base fija: la dirección y rapidez del giro se traducen en una orden de movimiento. Al frenar la pelota, la orden vuelve a cero.

El MPU6050, el ESP32 y la alimentación estarán dentro de la esfera, girando juntos. La conexión final será por Bluetooth. Unity recibirá la información y aplicará el movimiento y la física del juego; este proyecto se ocupa del controlador.

## Estado del prototipo

La prueba USB inicial funcionó en la placa. El firmware del controlador incluye lectura del sensor, calibración, estimación de orientación y una demo sin sensor. Compiló y pasó pruebas matemáticas en PC.

El 14/10/2026 se cargó y validó la demo sin sensor en el ESP32 por COM4: dos ciclos completos, 1650 paquetes con intervalos de 20 ms, direcciones y velocidades esperadas, cuaterniones normalizados y retorno a espera con salida cero. Resultado: aprobado. Esto no valida el sensor físico, Bluetooth ni Unity. [Resultados de la prueba](output/tests/2026-10-14-demo/result.json) y [registro serie](output/tests/2026-10-14-demo/serial.log).

El firmware ya incorpora Bluetooth clásico SPP bajo el nombre `Kyuboru` y un receptor de prueba independiente de Unity. Con Bluetooth inicializado, la demo volvió a pasar por USB: dos ciclos, 1650 paquetes y cadencia de 20 ms. [Resultados](output/tests/2026-10-14-bluetooth-usb/result.json). El receptor pasó cinco pruebas automatizadas de lectura y timeout.

La conexión inalámbrica real sigue pendiente: el adaptador Bluetooth de Windows presenta un error de dispositivo. Se probará con Android. También faltan la integración con Unity, la validación del MPU6050 y el montaje real. Marcas de frente y arriba permitirán alinear físicamente la pelota antes de confirmar su referencia.

## Documentación

Integración opcional del AK09911C: [magnetómetro y corrección de rumbo](docs/Magnetometro.md).
Preparada en código, desactivada por defecto y pendiente de calibración y prueba física.

Descripción del concepto: [Kyuboru: el juego](output/pdf/05_Descripcion_del_Juego.pdf).

Ampliación del firmware: [comunicación y receptor de prueba](docs/Comunicacion.md). Los PDFs técnicos todavía no incluyen esta ampliación.

Documentación PDF, con referencias cruzadas:

- [Main: funcionamiento del firmware](output/pdf/01_Main_Manual.pdf)
- [BallMotion: referencia de API y matemática](output/pdf/02_BallMotion_API.pdf)
- [Integración: usos de BallMotion desde Main](output/pdf/03_Integracion_Main_BallMotion.pdf)
- [Flujo de uso y bocetos del control](output/pdf/04_Flujo_Uso_y_Bocetos.pdf)

## Próximo paso acordado

**Probar el enlace Bluetooth con Android cuando el usuario vuelva.** La demo sin sensor ya fue probada por USB. Después se conectará y validará el MPU6050; Unity requiere el repositorio del juego. El documento de Integración, página 2, conserva el procedimiento anterior a estas pruebas.
