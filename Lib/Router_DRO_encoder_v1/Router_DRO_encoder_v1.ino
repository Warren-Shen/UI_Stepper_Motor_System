//length: 50 mm = 50000 um
//resolution: 5 um
//steps: 50000 um / 5 um = 10000
//REMEMBER! You have to calibrate your scale to get precise values in physical units
//You only get increments here and you have to calibrate the increments
 
#define encoder_pin1  2 //Pin 2 is one of the pins which works with attachInterrupt() on Arduino UNO
#define encoder_pin2  4
#define step_pin 24
#define dir_pin 30
#define enable_pin 13
#define emergency_pin 10

uint8_t incoming = 0;
uint8_t x_pulse_high_time = 100; // in ms
uint8_t x_pulse_low_time = 300;
uint8_t dir = 1; //the status of direction, used to record the pulse sent to motor
volatile int encoder0Pos = 0; //reading of the encoder
volatile int is_move = 1;
int command[9]; //record the incoming char 
uint8_t command_index = 0;
volatile long start_pos = 0;
volatile long pulse = 0; //accumulative pulse sine booting
volatile long target_dis = 0; //created by parsing the incoming command
String output;

 
void setup() {

  //pins of DRO 
  pinMode(encoder_pin1, INPUT); //Pin 2 = Input
  digitalWrite(encoder_pin1, HIGH);       // turn on pull-up resistor
  pinMode(encoder_pin2, INPUT); //Pin 4 = Input
  digitalWrite(encoder_pin2, HIGH);       // turn on pull-up resistor

  //pins of emergency stop button
  pinMode (emergency_pin, INPUT_PULLUP);

  //pins of motor:
  //step pin: send pulse to motor
  //dir pin: high/low refer to move forward/backward
  //enable pin: high will disable the motor. That is, it will be turned to high while emergency stop being triggered
  pinMode(step_pin, OUTPUT); 
  digitalWrite(step_pin, LOW);
  pinMode(dir_pin, OUTPUT);
  digitalWrite(dir_pin, LOW);
  pinMode(enable_pin, OUTPUT);
  digitalWrite(enable_pin, HIGH);
 
  //attachInterrupt: arduino built-in function
  //0: modify status of encoder pin, could record dro reading even if motor is running
  //1: emergency stop buoon
  attachInterrupt(0, doEncoder, CHANGE);  // encoder pin on interrupt 0 - pin 2
  attachInterrupt(1, stop , FALLING);  // 
  Serial.begin (9600);

  output = "";
}
 
void loop()
{
  if (Serial.available() > 0) {
    // read the incoming byte:
    incoming = Serial.read();
    //Serial.print(incoming);
    
    if (incoming == 35){ // '#' indicate end of command{

      switch (command[0]){
        case 76:
          move(command);
          break;
      }
      command_index = 0;
    }
    else{
      command[command_index] = incoming;
      command_index++;
    }
  }
}
 

void doEncoder() 
{
  //by comparing two pins of dro, record the dro reading
  if (digitalRead(encoder_pin1) == digitalRead(encoder_pin2)) 
  {
    encoder0Pos--; // increase the position
  } else {
    encoder0Pos++; //otherwise decrease the position
  }

  //check if motor move to target dis with dro reading
  if (abs(encoder0Pos - start_pos) >= target_dis){
    is_move = 0;
  }
  print_cor(is_move);
}

void stop(){
  digitalWrite(enable_pin, HIGH);
  is_move = 0;
}

void move(int commands[]){
  //Serial.print("move ");

  int pulse_high_time, pulse_low_time, step_pin, dir_pin, direction;
  long delay_time = 0;

  step_pin = step_pin;
  dir_pin = dir_pin;
  pulse_high_time = x_pulse_high_time;
  pulse_low_time = x_pulse_low_time;

  delay_time = (commands[2]-48)*10 + (commands[3]-48);
  target_dis = (commands[4]-48)*1000 + (commands[5]-48)*100 + (commands[6]-48)*10 + (commands[7]-48);

  digitalWrite(enable_pin, LOW); // Enable pin turn to low

  if (commands[1] == '+') {
    digitalWrite(dir_pin, LOW);
    direction = 1;
  }
  else if (commands[1] == '-') {
    digitalWrite(dir_pin, HIGH); 
    direction = -1;
  }
  
  delay(500);
  start_pos = encoder0Pos;
  is_move = 1;

  //Keep moving until dro return the expected coordinate
  while (is_move == 1){  

    digitalWrite(step_pin, HIGH);
    delayMicroseconds(pulse_high_time);
    digitalWrite(step_pin, LOW);
    delayMicroseconds(pulse_low_time + delay_time);
    pulse += direction;
    
  }
  digitalWrite(enable_pin, HIGH);
}

// print the encoder reading with the status
// 1 for running, 0 for finishing
void print_cor(int status){
  switch (status){
    case 1:
      output = "RR";
      break;
    case 0:
      output = "RF";
      break;
  }
  output.concat(String(pulse));
  output.concat(";");
  output.concat(String(encoder0Pos));
  output.concat("!");
  Serial.write(output.c_str());
  output = "";
}
