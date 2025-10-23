# Simple test script to add RCC MQTT Plotter button to DecoderPro
# Run this from JMRI Script Entry to test the button integration

import jmri
import javax.swing
import java.awt.event.ActionListener
import subprocess
import os

class RccButtonListener(java.awt.event.ActionListener):
    def actionPerformed(self, event):
        try:
            jmri_home = os.path.expanduser("~/JMRI")
            launcher_script = os.path.join(jmri_home, "launch-rcc-plotter.sh")
            subprocess.Popen([launcher_script], shell=True)
            print("RCC MQTT Data Plotter launched!")
        except Exception as e:
            print("Error: " + str(e))

# Create and show the button
button = javax.swing.JButton("RCC MQTT Plotter")
button.addActionListener(RccButtonListener())

# Create a simple window to hold the button
frame = javax.swing.JFrame("RCC Controls")
frame.setDefaultCloseOperation(javax.swing.JFrame.HIDE_ON_CLOSE)
frame.setSize(200, 100)
frame.add(button)
frame.setVisible(True)
frame.setAlwaysOnTop(True)

print("RCC MQTT Plotter button created! Click the button to launch the plotter.")