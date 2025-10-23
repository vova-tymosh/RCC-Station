# RCC MQTT Data Plotter Button Integration for JMRI DecoderPro
# Adds a button to the main DecoderPro window to launch the RCC MQTT Data Plotter
# Author: RCC MQTT Extension

import jmri
import javax.swing
import apps
import subprocess
import os
import java.awt.event.ActionListener

class RccPlotterButtonListener(java.awt.event.ActionListener):
    def actionPerformed(self, event):
        try:
            # Get JMRI home directory
            jmri_home = os.path.expanduser("~/JMRI")
            launcher_script = os.path.join(jmri_home, "launch-rcc-plotter.sh")
            
            # Launch the RCC MQTT Data Plotter
            if os.path.exists(launcher_script):
                subprocess.Popen([launcher_script], shell=True)
                print("RCC MQTT Data Plotter launched successfully!")
            else:
                # Fallback to direct JAR execution
                jar_path = os.path.join(jmri_home, "lib", "rcc-mqtt-plotter.jar")
                if os.path.exists(jar_path):
                    os.chdir(jmri_home)  # Change to JMRI directory for config.properties
                    subprocess.Popen(["java", "-jar", jar_path], 
                                   env=dict(os.environ, DISPLAY=":0"))
                    print("RCC MQTT Data Plotter launched via JAR!")
                else:
                    print("Error: RCC MQTT Data Plotter not found. Please run deploy-to-decoderpro.sh")
                    
        except Exception as e:
            print("Error launching RCC MQTT Data Plotter: " + str(e))

def addRccPlotterButton():
    try:
        # Create the button
        button = javax.swing.JButton("RCC MQTT Plotter")
        button.setToolTipText("Launch RCC MQTT Data Plotter for real-time locomotive telemetry")
        
        # Add the action listener
        button.addActionListener(RccPlotterButtonListener())
        
        # Try to add to the main window button space
        if hasattr(apps.Apps, 'buttonSpace'):
            # Method 1: Use Apps.buttonSpace() if available
            button_space = apps.Apps.buttonSpace()
            if button_space:
                button_space.add(button)
                button_space.revalidate()
                button_space.repaint()
                print("RCC MQTT Plotter button added to main window")
                return True
        
        # Method 2: Try to find the main frame and add to toolbar
        frames = javax.swing.JFrame.getFrames()
        for frame in frames:
            if hasattr(frame, 'getTitle') and frame.getTitle():
                title = frame.getTitle().lower()
                if 'decoderpro' in title or 'jmri' in title:
                    # Try to find a toolbar or button panel
                    content_pane = frame.getContentPane()
                    if hasattr(content_pane, 'add'):
                        # Add to the top of the content pane
                        toolbar = javax.swing.JPanel()
                        toolbar.add(button)
                        content_pane.add(toolbar, java.awt.BorderLayout.NORTH)
                        frame.revalidate()
                        frame.repaint()
                        print("RCC MQTT Plotter button added to DecoderPro toolbar")
                        return True
        
        # Method 3: Create a floating button window if main integration fails
        button_frame = javax.swing.JFrame("RCC Controls")
        button_frame.setDefaultCloseOperation(javax.swing.JFrame.HIDE_ON_CLOSE)
        button_frame.setAlwaysOnTop(True)
        button_frame.setSize(200, 80)
        button_frame.add(button)
        button_frame.setVisible(True)
        print("RCC MQTT Plotter button created in floating window")
        return True
        
    except Exception as e:
        print("Error adding RCC MQTT Plotter button: " + str(e))
        return False

# Add the button when this script is loaded
if addRccPlotterButton():
    print("RCC MQTT Data Plotter integration complete!")
else:
    print("RCC MQTT Data Plotter button integration failed")