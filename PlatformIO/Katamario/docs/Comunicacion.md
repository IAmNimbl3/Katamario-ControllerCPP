# Comunicación del controlador Kyuboru

El firmware ofrece la misma telemetría por USB y Bluetooth clásico SPP. El receptor de consola permite probarla en Windows sin el repositorio de Unity. Bluetooth se anuncia como `Kyuboru`; no es BLE ni un gamepad HID.

## Datos y comandos

Cada línea de datos termina en LF y conserva el formato de la demo:

`K2,millis,status,right,forward,qw,qx,qy,qz`

`millis` es el tiempo desde el arranque del ESP32, no una fecha. Se reinicia al reiniciar la placa y desborda a los 49,7 días. `right` y `forward` son órdenes normalizadas, no posiciones. El cuaternión se transmite en orden w, x, y, z, con la referencia X derecha, Y adelante, Z arriba. La adaptación al sistema de coordenadas de Unity sigue pendiente.

Los estados son `waiting`, `awaiting_alignment`, `calibrating`, `ready` y `demo`. Sólo `ready` y `demo` habilitan movimiento en el receptor. Las líneas que empiezan por `#` son mensajes de diagnóstico o respuesta, no datos de movimiento.

Los comandos de banco son caracteres individuales, en minúscula. Se ignoran CR y LF:

- `d`: iniciar o reiniciar la demo sintética.
- `c`: salir de la demo y buscar el sensor para realinear y recalibrar. Sin sensor vuelve a espera.
- `a`: confirmar alineación únicamente en `awaiting_alignment`; en otro estado devuelve un error.
- `h`: consultar ayuda.

`BYPASS_ALIGNMENT` continúa en `true`, por lo que la confirmación manual no es obligatoria todavía. La calibración real y su confirmación requieren una prueba posterior con sensor. Los dos transportes comparten comandos y estado: usar un solo cliente de control para evitar órdenes contradictorias.

## Receptor de Windows

Requiere Python y `pyserial`, ya disponibles en el entorno local de PlatformIO. Desde la carpeta del proyecto, en PowerShell:

```powershell
& C:/Users/Dylan/.platformio/penv/Scripts/python.exe tools/receiver.py --port COM4 --command d --seconds 35 --log output/tests/receiver-usb.log
```

La consola muestra el último estado recibido cada medio segundo; el archivo conserva el flujo de entrada. Al terminar una ejecución con `--command d`, el receptor intenta enviar `c` y cierra el puerto. Los comandos pueden probarse por separado cambiando `--command`.

El receptor tolera líneas fragmentadas, rechaza valores no finitos y formatos inválidos, y limita el tamaño de cada línea. Si deja de recibir paquetes válidos durante `--timeout` segundos (0,5 por defecto), muestra `stale`, movimiento cero y orientación no válida. Ese tiempo es configurable y debe ajustarse con las pruebas inalámbricas. No representa pérdida de orientación del sensor. Los datos válidos nuevos restablecen el estado del receptor; la política de alineación del firmware es independiente.

## Prueba posterior con Android

Con el ESP32 alimentado, buscar `Kyuboru` y conectarse desde una aplicación terminal que soporte Bluetooth clásico SPP/RFCOMM, no sólo BLE. Enviar `h` para verificar respuesta y `d` para observar la demo; enviar `c` al terminar. Emparejar por sí solo no inicia la demo. La versión de firmware instalada usa el emparejamiento predeterminado de BluetoothSerial, sin PIN personalizado ni autenticación de comandos adicional: es una configuración de banco para un entorno de confianza, no un diseño de seguridad final.

En Windows, cuando el adaptador funcione, seleccionar el puerto COM saliente del servicio SPP asignado al emparejar; no asumir que será COM4. El receptor usa ese puerto sin cambiar el formato de datos.

## Límites de esta versión

El envío Bluetooth se ejecuta en una tarea separada. Una cola de una muestra conserva la telemetría más reciente; otra cola acotada contiene respuestas. La aplicación evita acumular telemetría sin límite, pero la biblioteca y el sistema operativo también tienen buffers: la latencia real y la reconexión se deben medir por radio.

No hay identificadores de órdenes, confirmaciones fiables con reintentos, receptor Unity ni conversión de ejes del engine. No se modificó la matemática de BallMotion. La acción vertical sigue siendo un placeholder. Los manuales PDF preceden a esta ampliación y no se actualizaron.

Referencias del transporte: [BluetoothSerial de Espressif](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/bluetooth.html) y [Bluetooth clásico en Android](https://developer.android.com/develop/connectivity/bluetooth).
