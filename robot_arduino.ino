#include <AFMotor.h>            // [PARTIE MOTEUR]
#include <SoftwareSerial.h>     // [PARTIE CAM]
#include "DFRobot_HuskyLens.h"  // [PARTIE CAM]
#include <Wire.h>               // [PARTIE CAM]
#include <Servo.h>              // [ULTRASON + SERVO]

AF_DCMotor motor1(1); 
AF_DCMotor motor2(2); 
AF_DCMotor motor3(3); 
AF_DCMotor motor4(4); 
int vitesse = 200; 

DFRobot_HuskyLens huskylens;
int targetID = 0;    
int displayMode = 1; 
String currentAlgoName = "Face Recognition";
bool showLabels = true;

bool modeAutomatique = false;

// Variables pour centraliser la lecture de la caméra dans la loop
bool targetDetected = false;
HUSKYLENSResult sharedResult;

const int TRIG_PIN = 7;
const int ECHO_PIN = 8;
const int SERVO_PIN = 9;
const int SERVO_CENTER = 90;

Servo scanServo;

void displayAdvancedInfo();
void systemMenu();
void autonomousDrive();
long readDistanceCM();
long readDistanceAt(int angle);
void avancerDiagGauche();
void avancerDiagDroite();
void reculerDiagGauche();
void reculerDiagDroite();

void setup() {
    Serial.begin(9600); // 9600 bauds pour la Pi
    Wire.begin(); 
    Wire.setClock(400000); 

    pinMode(TRIG_PIN, OUTPUT);
    pinMode(ECHO_PIN, INPUT);
    scanServo.attach(SERVO_PIN);
    scanServo.write(SERVO_CENTER);

    // [HUSKYLENS DÉSACTIVÉE POUR LES TESTS MANUELS]
    /*
    while (!huskylens.begin(Wire)) {
        Serial.println(F("Erreur HuskyLens..."));
        delay(1000);
    }
    */
    
    Serial.println(F("========================================"));
    Serial.println(F("    SYSTEME MOTEUR OK (SANS HUSKY)      "));
    Serial.println(F("========================================"));
    stopRobot(); 
}

void loop() {
    targetDetected = false;

    // [HUSKYLENS DÉSACTIVÉE POUR LES TESTS MANUELS]
    /*
    if (huskylens.request() && huskylens.available() > 0) {
        targetDetected = true;
        sharedResult = huskylens.read(); 
        displayAdvancedInfo();
    }
    */

    // Étape 2 : Écoute des paquets série provenant de la Pi
    if (Serial.available()) {
        systemMenu();
    }

    // Étape 3 : Logique de conduite autonome si activée
    if (modeAutomatique) {
        autonomousDrive();
    }

    delay(50); 
}

void setVitesse(int v) {
  motor1.setSpeed(v); motor2.setSpeed(v);
  motor3.setSpeed(v); motor4.setSpeed(v);
}

void stopRobot() {
  motor1.run(RELEASE); motor2.run(RELEASE);
  motor3.run(RELEASE); motor4.run(RELEASE);
}

void avancer() {
  setVitesse(vitesse);
  motor1.run(FORWARD); motor2.run(FORWARD);
  motor3.run(FORWARD); motor4.run(FORWARD);
}

void reculer() {
  setVitesse(vitesse);
  motor1.run(BACKWARD); motor2.run(BACKWARD);
  motor3.run(BACKWARD); motor4.run(BACKWARD);
}

void glisserDroite() {
  setVitesse(vitesse);
  motor1.run(FORWARD);  motor2.run(BACKWARD);
  motor3.run(BACKWARD); motor4.run(FORWARD);
}

void glisserGauche() {
  setVitesse(vitesse);
  motor1.run(BACKWARD); motor2.run(FORWARD);
  motor3.run(FORWARD);  motor4.run(BACKWARD);
}

void rotationHoraire() {
  setVitesse(vitesse);
  motor1.run(FORWARD);  motor2.run(BACKWARD);
  motor3.run(FORWARD);  motor4.run(BACKWARD);
}

void rotationAntiHoraire() {
  setVitesse(vitesse);
  motor1.run(BACKWARD); motor2.run(FORWARD);
  motor3.run(BACKWARD); motor4.run(FORWARD);
}

void displayAdvancedInfo() {
    if (!targetDetected) return;
    if (displayMode == 2 && sharedResult.command != COMMAND_RETURN_BLOCK) return;
    if (displayMode == 3 && sharedResult.command != COMMAND_RETURN_ARROW) return;
    if (targetID != 0 && sharedResult.ID != targetID) return;

    if (showLabels) {
        String osdMsg = "ID:" + String(sharedResult.ID) + " " + currentAlgoName.substring(0,4);
        forceWriteOSD(osdMsg, sharedResult.xCenter - 20, sharedResult.yCenter - 20);
    }
}

void forceWriteOSD(String text, int x, int y) {
    uint8_t len = text.length();
    uint8_t dataLen = len + 4;
    uint8_t checksum = 0;
    uint8_t header[] = {0x55, 0xAA, 0x11, dataLen, 0x34};
    uint8_t x_low = x & 0xFF; uint8_t x_high = (x >> 8) & 0xFF;
    uint8_t y_pos = (uint8_t)y;
    Wire.beginTransmission(0x32);
    for (uint8_t b : header) { Wire.write(b); checksum += b; }
    Wire.write(x_low); checksum += x_low;
    Wire.write(x_high); checksum += x_high;
    Wire.write(y_pos); checksum += y_pos;
    Wire.write(len); checksum += len;
    for (uint8_t i = 0; i < len; i++) { Wire.write(text[i]); checksum += text[i]; }
    Wire.write(checksum);
    Wire.endTransmission();
}

long readDistanceCM() {
    digitalWrite(TRIG_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIG_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG_PIN, LOW);

    long duration = pulseIn(ECHO_PIN, HIGH, 25000); // ~4m max
    if (duration == 0) return 999;
    long distance = duration / 58;
    return distance;
}

long readDistanceAt(int angle) {
    scanServo.write(angle);
    delay(120);
    return readDistanceCM();
}

void avancerDiagGauche() {
  setVitesse(vitesse);
  motor1.run(FORWARD); motor4.run(FORWARD);
  motor2.run(RELEASE); motor3.run(RELEASE);
}

void avancerDiagDroite() {
  setVitesse(vitesse);
  motor2.run(FORWARD); motor3.run(FORWARD);
  motor1.run(RELEASE); motor4.run(RELEASE);
}

void reculerDiagGauche() {
  setVitesse(vitesse);
  motor1.run(BACKWARD); motor4.run(BACKWARD);
  motor2.run(RELEASE);  motor3.run(RELEASE);
}

void reculerDiagDroite() {
  setVitesse(vitesse);
  motor2.run(BACKWARD); motor3.run(BACKWARD);
  motor1.run(RELEASE);  motor4.run(RELEASE);
}

void autonomousDrive() {
    long frontDist = readDistanceAt(SERVO_CENTER);

    if (frontDist < 30) {
        int autoSpeed = map(constrain((int)frontDist, 5, 30), 5, 30, 80, vitesse);
        setVitesse(autoSpeed);

        if (frontDist < 15) {
            stopRobot();

            long leftDist = readDistanceAt(30);
            long rightDist = readDistanceAt(150);
            scanServo.write(SERVO_CENTER);

            if (leftDist > rightDist && leftDist > 30) {
                glisserGauche();
            } else if (rightDist > leftDist && rightDist > 30) {
                glisserDroite();
            } else {
                reculer();
            }
            return;
        }

        avancer();
        return;
    }

    setVitesse(vitesse);
    avancer();
}

void systemMenu() {
    char cmd = Serial.read();

    if (cmd == 'A') { modeAutomatique = true; stopRobot(); return; }
    if (cmd == 'M') { modeAutomatique = false; stopRobot(); return; }

    if (cmd == 'V') {
        while (Serial.available() == 0) { delay(2); }
        int v = Serial.parseInt();
        vitesse = constrain(v, 0, 255);
        return;
    }

    bool isMoveCmd = (cmd == 'z' || cmd == 's' || cmd == 'q' || cmd == 'd' || cmd == 'a' || cmd == 'e' || cmd == 'x' ||
                      cmd == 'u' || cmd == 'i' || cmd == 'j' || cmd == 'k');
    if (modeAutomatique && isMoveCmd) return;

    switch (cmd) {
        case '1': huskylens.writeAlgorithm(ALGORITHM_FACE_RECOGNITION); currentAlgoName = "Face Recognition"; break;
        case '2': huskylens.writeAlgorithm(ALGORITHM_OBJECT_TRACKING); currentAlgoName = "Object Tracking"; break;
        case '3': huskylens.writeAlgorithm(ALGORITHM_OBJECT_RECOGNITION); currentAlgoName = "Object Recognition"; break;
        case '4': huskylens.writeAlgorithm(ALGORITHM_LINE_TRACKING); currentAlgoName = "Line Tracking"; break;
        case '5': huskylens.writeAlgorithm(ALGORITHM_COLOR_RECOGNITION); currentAlgoName = "Color Recognition"; break;
        case '6': huskylens.writeAlgorithm(ALGORITHM_TAG_RECOGNITION); currentAlgoName = "Tag Recognition"; break;
        case 'i': Serial.println(F("ID cible ?")); while(!Serial.available()); targetID = Serial.parseInt(); break;
        
        case 'z': avancer(); break;
        case 's': reculer(); break;
        case 'q': glisserGauche(); break;
        case 'd': glisserDroite(); break;
        case 'a': rotationAntiHoraire(); break;
        case 'e': rotationHoraire(); break;
        case 'u': avancerDiagGauche(); break;
        case 'i': avancerDiagDroite(); break;
        case 'j': reculerDiagGauche(); break;
        case 'k': reculerDiagDroite(); break;
        case 'x': stopRobot(); break;
        
        case 'r': targetID = 0; displayMode = 1; stopRobot(); break;
    }
}
