const int BUTTON_PIN = 15;
const int LED_PIN = 2;
const unsigned long DEBOUNCE_DELAY_MILLISECONDS = 20;

bool lastRawButtonState = LOW;
bool stableButtonState = LOW;
unsigned long lastRawStateChangeTimeMilliseconds = 0;
unsigned long buttonPressStartTimeMilliseconds = 0;

void setup() {
  pinMode(BUTTON_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  Serial.begin(115200);
}

void loop() {
  const bool currentRawButtonState = digitalRead(BUTTON_PIN);
  const unsigned long nowMilliseconds = millis();

  if (currentRawButtonState != lastRawButtonState) {
    lastRawButtonState = currentRawButtonState;
    lastRawStateChangeTimeMilliseconds = nowMilliseconds;
  }

  if (nowMilliseconds - lastRawStateChangeTimeMilliseconds <= DEBOUNCE_DELAY_MILLISECONDS) { return; }
  if (currentRawButtonState == stableButtonState) { return; }

  stableButtonState = currentRawButtonState;

  if (stableButtonState == HIGH) {
    handleButtonPressed(nowMilliseconds);
  } else {
    handleButtonReleased(nowMilliseconds);
  }
}

void handleButtonPressed(unsigned long timestampMilliseconds) {
  digitalWrite(LED_PIN, HIGH);
  buttonPressStartTimestampMilliseconds = timestampMilliseconds;

  Serial.print("DOWN ");
  Serial.println(timestampMilliseconds);
}

void handleButtonReleased(unsigned long timestampMilliseconds) {
  digitalWrite(LED_PIN, LOW);

  const unsigned long pressDurationMilliseconds = timestampMilliseconds - buttonPressStartTimestampMilliseconds;

  Serial.print("UP ");
  Serial.print(timestampMilliseconds);
  Serial.print(" ");
  Serial.println(pressDurationMilliseconds);
}

