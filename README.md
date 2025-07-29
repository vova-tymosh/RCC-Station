# RCC-Station
This is the Station for RCC. Read more about RCC on the main page - [RCC](https://github.com/vova-tymosh/RCC).


There are two parts of the story - [JMRI](https://www.jmri.org/) and RCC-RF24. Both of them can run on the same Raspberry Pi and this page explains how to set up this Raspberry Pi without the need of a screen or keyboard. If you are going to use WiFi/MQTT Locos only, you may skip the RCC-RF24 station part.




## Raspberry Setup


1. Get a Raspberry Pi. Better Raspberry Pi 4 or newer, older versions are too slow for JMRI.
2. Get an SD card of 8GB or bigger. Download the [Raspberry Imager](https://www.raspberrypi.com/software/).
3. As it was mentioned above, there is a way to set up everything without ever connecting the Raspberry to a screen or a keyboard. For that you just need to give the Imager your WiFi data, specify the hostename, enable SSH and create a user with a password.
4. Once the flashing is done the Raspberry would boot and connect to your WiFi network. You can check your WiFi router for the IP address of your Raspberry (if you provided the hostname, just look for that name in your home router DHCP clients list).
5. Now you can connect to the Raspberry remotely using SSH. Mac and Linux have SSH clients installed. On Windows try Putty (Google it for details).


## Install JMRI
1. Enable VNC, get to the Raspberry via SSH, do `raspi-config`, navigate to Interfaces and enable VNC.
2. Get a VNC client for your main computer, like [Real VNC](https://www.realvnc.com).
3. Start VNC, connect to the Raspberry using the same IP/username you'd use for SSH. You'd have a full graphic interface like with a real display/mouse/keyboard.
4. Install Java by `sudo apt install default-jdk`.
5. Install JMRI as per [Install page](https://www.jmri.org/install/Linux.shtml). Essentially it is just an archive you need to download and extract.
6. You are done. Go ahead and try DecoderPro or PanelPro.


## Install RCC-RF24
The RCC part is needed to connect NRF24 nodes/Locos to MQTT ones or to JMRI. For this part you'd need to phisically connect NRF module to Raspberry Pi. You can create your own adoptor/shield or try something like this one from [Aliexpress](https://www.aliexpress.us/item/2251832672119623.html?gatewayAdapt=glo2usa4itemAdapt). More details on how to connect/build your own is on [nRF24 page](https://nrf24.github.io/pyRF24/). It make sense to get the RF24 with an amplifier to extend the range to some 300-500ft, like [this](https://www.amazon.com/MakerFocus-NRF24L01-Wireless-Transceiver-Regulator/dp/B08LSPZHT8/ref=sr_1_4?dib=eyJ2IjoiMSJ9.INY1ZJf_cbNGizzyPvyfDZkD4E_Z5J3zWtY-B5WhHG_mJZ40pjJf1K0o2l0zt4GH4vLvbIGxeclY_kWh-6eV55jDJrEq6ce8HrOtrgxfXa9krxPIBV3RCY7jujlE7VrxHhkqOoPGGQ6nn2BvfyKRzvQA4DXkXmh1N270kMxSgY4Ioqxg9uenrm01u2YG7Og8G-PpiBGOjit10KE6Oyq4Vlx_8j8b-evkDVMVDSQbLnQ._SjB-cEmWMdm2wny8Jbg6zT1ORGa2NNR1mf5KJS56SQ&dib_tag=se&hvadid=694590041969&hvdev=c&hvexpln=67&hvlocphy=1013950&hvnetw=g&hvocijid=15798605651029559051--&hvqmt=b&hvrand=15798605651029559051&hvtargid=kwd-27068984794&hydadcr=18031_13447380&keywords=nrf24l01+transceiver&mcid=34f09a0ffd9732ab99c139c8daf3fb16&qid=1753545230&sr=8-4). It would also mean you have to provide good enough power. Use that tiny board that comes with RF24 to convert Raspberry Pi 5V to a stable 3.3V.


To complete the software setup, do the following:
1. It is recommended to create a separate user to run RCC. You may skip this and run it under your default user, just make sure you add this user to spi group.
2. To create a user: `sudo adduser rcc`
3. Add the user to the spi group: `sudo usermod -a -G spi rcc`.
4. Switch to this new user `sudo -s -u rcc`.
5. Create a Python virtual environment. You may try to skip this step and install all the dependency into your system python, but modern Linux is pretty protective and would resist your attempts. Create the environment `python3 -m venv venv`.
6. Activate the environment, setup dependencies (RF24 and MQTT), get out of it:
```
   source venv/bin/activate
   pip3 install pyrf24
   pip3 install paho-mqtt
   deactivate
```
7. Create a folder for your Station code: `mkdir Station`.
8. Get the RCC code from https://github.com/vova-tymosh/RCC-Station. Put the scripts from `src` to the folder you have created.
9. Make the RCC start at boot: `crontab -e`. Add to the end of the file: `@reboot /home/rcc/Station/init_station.sh`
10. You are done, boot your Raspberry. To test if everything works check the logs in `/home/rcc/Station/comms.log`. If everything is set correctly you should see heartbeat messages coming from your locos.
