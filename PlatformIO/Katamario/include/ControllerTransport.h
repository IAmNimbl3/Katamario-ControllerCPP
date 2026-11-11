#pragma once
#include <Arduino.h>
#include <BluetoothSerial.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <freertos/task.h>

// Bench transport: Classic SPP, not BLE or a HID gamepad.
// Blocking Bluetooth writes run outside the sensor loop. Telemetry is a
// single latest-value mailbox, not an unbounded backlog of old movement.
class ControllerTransport {
  struct Line { char text[192]; };
  BluetoothSerial bt;
  QueueHandle_t latest=nullptr, replies=nullptr;
  bool enabled=false;
  static void writer(void *arg) {
    auto &self=*static_cast<ControllerTransport *>(arg);
    Line line;
    for (;;) {
      if (!self.bt.hasClient()) {
        xQueueReset(self.latest); xQueueReset(self.replies);
      } else {
        if (xQueueReceive(self.replies,&line,0)==pdTRUE)
          self.bt.print(line.text);
        if (xQueueReceive(self.latest,&line,0)==pdTRUE)
          self.bt.print(line.text);
      }
      vTaskDelay(pdMS_TO_TICKS(10));
    }
  }
 public:
  bool begin() {
    latest=xQueueCreate(1,sizeof(Line));
    replies=xQueueCreate(8,sizeof(Line));
    if (!latest || !replies) return false;
    if (!bt.begin("Kyuboru")) return false;
    enabled=xTaskCreate(writer,"kyuboru-bt",4096,this,1,nullptr)==pdPASS;
    if (!enabled) bt.end();
    return enabled;
  }
  int readBluetooth() { return enabled && bt.available() ? bt.read() : -1; }
  // A connected SPP client owns commands. On battery, the USB UART can
  // receive spurious bytes; never let those override Bluetooth control.
  bool acceptsUsbCommands() { return !enabled || !bt.hasClient(); }
  void send(const char *text, bool telemetry=false) {
    Serial.print(text);
    if (!enabled || !bt.hasClient()) return;
    Line line={};
    snprintf(line.text,sizeof(line.text),"%s",text);
    if (telemetry) xQueueOverwrite(latest,&line);
    else xQueueSend(replies,&line,0); // Bounded; never block sampling for replies.
  }
};
