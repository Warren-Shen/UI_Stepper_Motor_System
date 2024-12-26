# Project Title

A system includes user-interface to interact with motor and encoder.

## Description

This project aims at enhancing accuracy of a step motor by integrating digital readout (DRO) as the encoder. 
The step motor is usually easy to be controlled by sending PWM commands, while the disadvantage comes from the lack of encoder. Thus, the pulses sent to the motor is commonly used to viewed as the travelling distance or further converted to the coordinate. This system combines the motor and the DRO. That is, it relies on the DRO readings as the encoder instead of the accumulative pulses. 
Further, this system includes a UI interface providing basic functionalities, such as triggering the motor, emergency stop and data visualization of the relationship between pulses and encoder readings.

## Structure

![image](https://github.com/VermouthVulpix/UI_Stepper_Motor_System/blob/main/Doc/structure.png)

## Getting Started

### Dependencies

* PyQT6
* PySerial
* Arduino

### Executing program

* How to run the program
* Step-by-step bullets
```
code blocks for commands
```

## Help

Any advise for common problems or issues.
```
command to run if program contains helper info
```

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


Inspiration, code snippets, etc.
* [awesome-readme](https://github.com/matiassingers/awesome-readme)
* [PurpleBooth](https://gist.github.com/PurpleBooth/109311bb0361f32d87a2)
* [dbader](https://github.com/dbader/readme-template)
* [zenorocha](https://gist.github.com/zenorocha/4526327)
* [fvcproductions](https://gist.github.com/fvcproductions/1bfc2d4aecb01a834b46)
