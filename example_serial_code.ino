// holds the incoming raw data. Signal value can range from 0-1024
int Signal0;
int Signal1;                
int Signal2;                
int Signal3;                
int Signal4;               
int Signal5; 
int Signal6;                
int Signal7;    
int Signal8;

// The SetUp Function:
void setup() {
  pinMode(A0,INPUT); 
  pinMode(A1,INPUT); 
  pinMode(A2,INPUT); 
  pinMode(A3,INPUT); 
  pinMode(A4,INPUT); 
  pinMode(A5,INPUT); 
  pinMode(A6,INPUT); 
  pinMode(A7,INPUT); 
  Serial.begin(115200);         // Baudrate.
}

// The Main Loop Function
void loop() {

// Analog input pins
 Signal0 = analogRead(A0);
 Signal1 = analogRead(A1);
 Signal2 = analogRead(A2);
 Signal3 = analogRead(A3);
 Signal4 = analogRead(A4);
 Signal5 = analogRead(A5);
 Signal6 = analogRead(A6);
 Signal7 = analogRead(A7);
 Signal8 = analogRead(A8);

Serial.print(Signal0);                 
Serial.print(',');                    
Serial.print(Signal1);                  
Serial.print(',');                   
Serial.print(Signal2);                   
Serial.print(',');                    
Serial.print(Signal3);
Serial.print(',');     
Serial.print(Signal4);                 
Serial.print(',');                    
Serial.print(Signal5);                  
Serial.print(',');                   
Serial.print(Signal6);                   
Serial.print(',');                    
Serial.print(Signal7);
Serial.print(',');                    
Serial.println(Signal8);


}
