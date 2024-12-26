# User Interface Design, API Design and I/O Integration
A system includes user-interface to interact with motor and encoder.

## Description

This project aims at enhancing accuracy of a step motor by integrating digital readout (DRO) as the encoder. 
The step motor is usually easy to be controlled by sending PWM commands, while the disadvantage comes from the lack of encoder. Thus, the pulses sent to the motor is commonly used to viewed as the travelling distance or further converted to the coordinate. This system combines the motor and the DRO. That is, it relies on the DRO readings as the encoder instead of the accumulative pulses. 
Further, this system includes a UI interface providing basic functionalities, such as triggering the motor, emergency stop and data visualization of the relationship between pulses and encoder readings.

## Structure

* Mechanical module: including a stepper motor, a driver, a digital readout (DRO), a NC switch
* Control module: including Arduino Mega
* UI module: utilizing PyQT6 for the main UI, PySerial for communication, Matplotlib and PyQtGraph for graph

![image](https://github.com/VermouthVulpix/UI_Stepper_Motor_System/blob/main/Doc/structure.png)

## Quick Demo

This demo demonstrates the real-time display of relationship between stepper motor pulses and DRO readings

* Basic: Connecting controller board, in this case, Arduino Mega, with defined "COM Port" name
* Info: Pop up window that displays information for manual, spec, etc.
* Coordinate: Display real-time accumulative pulses sent to motor and DRO reading in text format
* Parmeters: A manually operating panel, will create move commands based on the defined direction, speed and stroke
* Chart: Plot real-time accumulative pulses sent to motor and DRO reading in the same diagram for easy comparison
* Message box: Display message, e.g. task complete, connection successfully, etc.

![image](https://github.com/VermouthVulpix/UI_Stepper_Motor_System/blob/main/Demo/Demo.gif)

## Getting Started

### Dependencies

* PyQT6
* PySerial
* Arduino

## Authors

Contributors names and contact info

VermouthVulpix  
stonecreek00@gmail.com

## Version History

* 1.1
    * Various bug fixes and optimizations
    * Improved visualization layout
* 1.0
    * Initial Release
