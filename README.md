# Project Title

A system includes user-interface to interact with motor and encoder.

## Description

This project aims at enhancing accuracy of a step motor by integrating digital readout (DRO) as the encoder. 
The step motor is usually easy to be controlled by sending PWM commands, while the disadvantage comes from the lack of encoder. Thus, the pulses sent to the motor is commonly used to viewed as the travelling distance or further converted to the coordinate. This system combines the motor and the DRO. That is, it relies on the DRO readings as the encoder instead of the accumulative pulses. 
Further, this system includes a UI interface providing basic functionalities, such as triggering the motor, emergency stop and data visualization of the relationship between pulses and encoder readings.

## Structure

![image](https://github.com/VermouthVulpix/UI_Stepper_Motor_System/blob/main/Doc/structure.png)

## Quick Demo

This demo demonstrates the real-time display of relationship between stepper motor pulses and DRO readings

![image](https://github.com/VermouthVulpix/UI_Stepper_Motor_System/blob/main/Demo/Demo.gif)

## Getting Started

### Dependencies

* PyQT6
* PySerial
* Arduino

## Authors

Contributors names and contact info

VermouthVilpix  
stonecreek00@gmail.com

## Version History

* 1.1
    * Various bug fixes and optimizations
    * Improved visualization layout
* 1.0
    * Initial Release
