const int BUTTON_PIN = 15;
const int LED_PIN = 2;

const unsigned long SERIAL_BAUD_RATE = 115200;
const unsigned long DEBOUNCE_DELAY_MS = 20;

bool lastRawButtonState = LOW;
bool stableButtonState = LOW;
unsigned long lastRawChangeMs = 0;

void setup() {
  pinMode(BUTTON_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  Serial.begin(SERIAL_BAUD_RATE);
}

void loop() {
  const bool rawButtonState = digitalRead(BUTTON_PIN);
  const unsigned long nowMs = millis();

  if (rawButtonState != lastRawButtonState) {
    lastRawButtonState = rawButtonState;
    lastRawChangeMs = nowMs;
  }

  if (nowMs - lastRawChangeMs <= DEBOUNCE_DELAY_MS) { return; }
  if (rawButtonState == stableButtonState) { return; }

  stableButtonState = rawButtonState;

  if (stableButtonState == HIGH) {
    handleButtonPressed(nowMs);
  } else {
    handleButtonReleased(nowMs);
  }
}

void handleButtonPressed(unsigned long timestampMs) {
  digitalWrite(LED_PIN, HIGH);

  Serial.print("DOWN ");
  Serial.println(timestampMs);
}

void handleButtonReleased(unsigned long timestampMs) {
  digitalWrite(LED_PIN, LOW);

  Serial.print("UP ");
  Serial.print(timestampMs);
}

