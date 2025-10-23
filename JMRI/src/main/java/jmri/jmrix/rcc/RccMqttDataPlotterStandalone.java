package jmri.jmrix.rcc;

import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.io.*;
import java.util.*;
import java.util.List;
import javax.swing.*;
import javax.swing.border.TitledBorder;

import org.eclipse.paho.client.mqttv3.*;
import org.json.JSONObject;
import org.jfree.chart.ChartFactory;
import org.jfree.chart.ChartPanel;
import org.jfree.chart.JFreeChart;
import org.jfree.data.time.Second;
import org.jfree.data.time.TimeSeries;
import org.jfree.data.time.TimeSeriesCollection;

/**
 * Standalone version of RCC MQTT Data Plotter for testing
 * Can run independently without JMRI
 */
public class RccMqttDataPlotterStandalone extends JFrame implements MqttCallback {
    
    /**
     * Information about a discovered locomotive
     */
    private static class LocomotiveInfo {
        String id;
        String address;
        String name;
        String version;
        boolean isActive;
        long lastSeen;
        double distanceTraveled;
        
        LocomotiveInfo(String id) {
            this.id = id;
            this.isActive = false;
            this.lastSeen = System.currentTimeMillis();
            this.distanceTraveled = 0.0;
        }
        
        @Override
        public String toString() {
            if (address != null && name != null) {
                String versionStr = version != null ? ", Version: " + version : "";
                return String.format("Loco: %s (Addr: %s%s)", name, address, versionStr);
            }
            return "Loco " + id;
        }
        
        public String getDisplayNameWithDistance() {
            return String.format("%s. Distance: %.1f", toString(), distanceTraveled);
        }
    }
    
    // Configuration
    private Properties config;
    private String brokerUrl;
    private String topicPattern;
    private String clientId;
    private int connectionTimeout;
    private int keepAliveInterval;
    private int maxDataPoints;
    private boolean autoConnect;
    
    private MqttClient mqttClient;
    
    // Chart components
    private JFreeChart speedChart;
    private JFreeChart throttleChart;
    private JFreeChart batteryChart;
    private JFreeChart currentChart;
    private JFreeChart tempChart;
    private JFreeChart psiChart;
    private TimeSeriesCollection speedDataset;
    private TimeSeriesCollection throttleDataset;
    private TimeSeriesCollection batteryDataset;
    private TimeSeriesCollection currentDataset;
    private TimeSeriesCollection tempDataset;
    private TimeSeriesCollection psiDataset;
    
    // Data storage
    private Map<String, TimeSeries> speedSeriesMap;
    private Map<String, TimeSeries> throttleSeriesMap;
    private Map<String, TimeSeries> batterySeriesMap;
    private Map<String, TimeSeries> currentSeriesMap;
    private Map<String, TimeSeries> tempSeriesMap;
    private Map<String, TimeSeries> psiSeriesMap;
    
    // Field mappings for RCC heartbeat data
    private Map<String, String[]> locomotiveKeys;
    
    // Locomotive selection components
    private JPanel locomotiveSelectionPanel;
    private Map<String, JCheckBox> locomotiveCheckboxes;
    private Map<String, LocomotiveInfo> discoveredLocomotives;
    
    // Color management for chart series
    private Map<String, Color> locomotiveColors;
    private Color[] chartColors = {
        Color.BLUE, Color.RED, Color.GREEN, Color.ORANGE, Color.MAGENTA,
        Color.CYAN, Color.PINK, Color.YELLOW, Color.DARK_GRAY, Color.LIGHT_GRAY
    };
    private int colorIndex = 0;
    
    public RccMqttDataPlotterStandalone() {
        super("RCC MQTT Data Plotter");
        
        // Load configuration
        loadConfiguration();
        
        initializeComponents();
        setupCharts();
        layoutComponents();
        
        speedSeriesMap = new HashMap<>();
        throttleSeriesMap = new HashMap<>();
        batterySeriesMap = new HashMap<>();
        currentSeriesMap = new HashMap<>();
        tempSeriesMap = new HashMap<>();
        psiSeriesMap = new HashMap<>();
        locomotiveKeys = new HashMap<>();
        locomotiveCheckboxes = new HashMap<>();
        discoveredLocomotives = new HashMap<>();
        locomotiveColors = new HashMap<>();
        
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        
        // Auto-connect if enabled
        if (autoConnect) {
            SwingUtilities.invokeLater(this::connectToMqtt);
        }
    }
    
    private void loadConfiguration() {
        config = new Properties();
        
        // Try to load from config file
        try (InputStream input = new FileInputStream("config.properties")) {
            config.load(input);
            System.out.println("Configuration loaded from config.properties");
        } catch (IOException e) {
            System.out.println("Could not load config.properties, using defaults: " + e.getMessage());
            // Set default values
            config.setProperty("mqtt.broker", "tcp://127.0.0.1:1883");
            config.setProperty("mqtt.topic", "cab/+/heartbeat/values");
            config.setProperty("mqtt.client.id", "RCC_MQTT_Plotter");
            config.setProperty("mqtt.timeout", "10");
            config.setProperty("mqtt.keepalive", "20");
            config.setProperty("chart.max.points", "1000");
            config.setProperty("window.width", "1000");
            config.setProperty("window.height", "700");
            config.setProperty("auto.connect", "true");
        }
        
        // Parse configuration values
        brokerUrl = config.getProperty("mqtt.broker");
        topicPattern = config.getProperty("mqtt.topic");
        clientId = config.getProperty("mqtt.client.id") + "_" + System.currentTimeMillis();
        connectionTimeout = Integer.parseInt(config.getProperty("mqtt.timeout", "10"));
        keepAliveInterval = Integer.parseInt(config.getProperty("mqtt.keepalive", "20"));
        maxDataPoints = Integer.parseInt(config.getProperty("chart.max.points", "1000"));
        autoConnect = Boolean.parseBoolean(config.getProperty("auto.connect", "true"));
        
        System.out.println("MQTT Broker: " + brokerUrl);
        System.out.println("MQTT Topic: " + topicPattern);
        System.out.println("Auto-connect: " + autoConnect);
    }
    
    private void initializeComponents() {
        // Initialize locomotive selection panel
        locomotiveSelectionPanel = new JPanel();
        locomotiveSelectionPanel.setLayout(new BoxLayout(locomotiveSelectionPanel, BoxLayout.Y_AXIS));
        locomotiveSelectionPanel.setBorder(new TitledBorder("Locomotive Selection"));
        locomotiveSelectionPanel.add(new JLabel("No locomotives discovered yet"));
    }
    
    private void setupCharts() {
        // Speed chart
        speedDataset = new TimeSeriesCollection();
        speedChart = ChartFactory.createTimeSeriesChart(
            null, null, "Speed", speedDataset, false, true, false);
        
        // Throttle chart
        throttleDataset = new TimeSeriesCollection();
        throttleChart = ChartFactory.createTimeSeriesChart(
            null, null, "Throttle", throttleDataset, false, true, false);
        
        // Battery chart
        batteryDataset = new TimeSeriesCollection();
        batteryChart = ChartFactory.createTimeSeriesChart(
            null, null, "Battery", batteryDataset, false, true, false);
        
        // Current chart  
        currentDataset = new TimeSeriesCollection();
        currentChart = ChartFactory.createTimeSeriesChart(
            null, null, "Current", currentDataset, false, true, false);
            
        // Temperature chart
        tempDataset = new TimeSeriesCollection();
        tempChart = ChartFactory.createTimeSeriesChart(
            null, null, "Temperatire", tempDataset, false, true, false);
            
        // Pressure chart
        psiDataset = new TimeSeriesCollection();
        psiChart = ChartFactory.createTimeSeriesChart(
            null, null, "Pressure", psiDataset, false, true, false);
    }
    
    private void layoutComponents() {
        setLayout(new BorderLayout());
        
        // Locomotive selection panel with scroll - now uses full top area
        JScrollPane locomotiveScrollPane = new JScrollPane(locomotiveSelectionPanel);
        locomotiveScrollPane.setPreferredSize(new Dimension(1000, 120));
        locomotiveScrollPane.setMaximumSize(new Dimension(Integer.MAX_VALUE, 120));
        locomotiveScrollPane.setVerticalScrollBarPolicy(JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED);
        
        add(locomotiveScrollPane, BorderLayout.NORTH);
        
        // Charts panel with fixed chart heights - 6 charts in order: Speed, Throttle, Battery, Current, Temp, Psi
        JPanel chartsPanel = new JPanel(new GridLayout(6, 1));
        
        int chartHeight = Integer.parseInt(config.getProperty("chart.height", "120"));
        
        ChartPanel speedChartPanel = new ChartPanel(speedChart);
        speedChartPanel.setPreferredSize(new Dimension(800, chartHeight));
        
        ChartPanel throttleChartPanel = new ChartPanel(throttleChart);
        throttleChartPanel.setPreferredSize(new Dimension(800, chartHeight));
        
        ChartPanel batteryChartPanel = new ChartPanel(batteryChart);
        batteryChartPanel.setPreferredSize(new Dimension(800, chartHeight));
        
        ChartPanel currentChartPanel = new ChartPanel(currentChart);
        currentChartPanel.setPreferredSize(new Dimension(800, chartHeight));
        
        ChartPanel tempChartPanel = new ChartPanel(tempChart);
        tempChartPanel.setPreferredSize(new Dimension(800, chartHeight));
        
        ChartPanel psiChartPanel = new ChartPanel(psiChart);
        psiChartPanel.setPreferredSize(new Dimension(800, chartHeight));
        
        chartsPanel.add(speedChartPanel);
        chartsPanel.add(throttleChartPanel);
        chartsPanel.add(batteryChartPanel);
        chartsPanel.add(currentChartPanel);
        chartsPanel.add(tempChartPanel);
        chartsPanel.add(psiChartPanel);
        
        add(chartsPanel, BorderLayout.CENTER);
        
        // Set window size from config
        int width = Integer.parseInt(config.getProperty("window.width", "1000"));
        int height = Integer.parseInt(config.getProperty("window.height", "700"));
        setSize(width, height);
        setPreferredSize(new Dimension(width, height));
    }
    
    private void connectToMqtt() {
        try {
            System.out.println("Connecting to MQTT broker: " + brokerUrl);
            
            mqttClient = new MqttClient(brokerUrl, clientId);
            mqttClient.setCallback(this);
            
            MqttConnectOptions options = new MqttConnectOptions();
            options.setCleanSession(true);
            options.setConnectionTimeout(connectionTimeout);
            options.setKeepAliveInterval(keepAliveInterval);
            
            mqttClient.connect(options);
            mqttClient.subscribe(topicPattern);
            mqttClient.subscribe("cab/+/heartbeat/keys");
            mqttClient.subscribe("cab/+/intro");
            
            System.out.println("Connected to MQTT broker: " + brokerUrl);
            System.out.println("Subscribed to topics: " + topicPattern + ", cab/+/heartbeat/keys, cab/+/intro");
            
        } catch (MqttException ex) {
            System.err.println("Failed to connect to MQTT broker: " + ex.getMessage());
        }
    }
    
    private void reconnectToMqtt() {
        try {
            if (mqttClient != null && mqttClient.isConnected()) {
                mqttClient.disconnect();
                mqttClient.close();
            }
        } catch (MqttException e) {
            System.err.println("Error disconnecting before reconnect: " + e.getMessage());
        }
        
        // Generate new client ID for reconnection
        clientId = config.getProperty("mqtt.client.id") + "_" + System.currentTimeMillis();
        connectToMqtt();
    }
    
    @Override
    public void connectionLost(Throwable cause) {
        System.err.println("MQTT connection lost: " + cause.getMessage());
        // Auto-reconnect after a delay
        SwingUtilities.invokeLater(() -> {
            javax.swing.Timer reconnectTimer = new javax.swing.Timer(5000, e -> reconnectToMqtt());
            reconnectTimer.setRepeats(false);
            reconnectTimer.start();
        });
    }
    
    @Override
    public void messageArrived(String topic, MqttMessage message) throws Exception {
        String payload = new String(message.getPayload());
        System.out.println("Received message on topic: " + topic);
        System.out.println("Payload: " + payload);
        
        if (topic.contains("/heartbeat/values")) {
            processHeartbeatValues(topic, payload);
        } else if (topic.contains("/heartbeat/keys")) {
            processHeartbeatKeys(topic, payload);
        } else if (topic.contains("/intro")) {
            processIntroMessage(topic, payload);
        }
    }
    
    @Override
    public void deliveryComplete(IMqttDeliveryToken token) {
        // Not used for subscriber
    }
    
    private void processHeartbeatValues(String topic, String payload) {
        try {
            // Extract locomotive ID from topic (cab/{locoId}/heartbeat/values)
            String[] topicParts = topic.split("/");
            if (topicParts.length < 2) return;
            String locoId = topicParts[1];
            
            // Ensure locomotive is discovered
            ensureLocomotiveDiscovered(locoId);
            
            // Parse CSV payload: "39,48,1073741824,62,0,0,0,0,0,0,0"
            String[] values = payload.split(",");
            String[] keys = locomotiveKeys.get(locoId);
            
            if (keys == null) {
                System.out.println("No keys found for locomotive " + locoId + ", using default mapping");
                // Default RCC key mapping: Time,Distance,Bitstate,Speed,Lost,Throttle,ThrOut,Battery,Temp,Psi,Current
                keys = new String[]{"Time", "Distance", "Bitstate", "Speed", "Lost", "Throttle", "ThrOut", "Battery", "Temp", "Psi", "Current"};
            }
            
            if (values.length != keys.length) {
                System.err.println("Value count (" + values.length + ") doesn't match key count (" + keys.length + ") for loco " + locoId);
                return;
            }
            
            // Extract relevant values
            double battery = 0, current = 0, speed = 0, temp = 0, distance = 0, throttle = 0, psi = 0;
            long timestamp = System.currentTimeMillis();
            
            for (int i = 0; i < keys.length && i < values.length; i++) {
                try {
                    double value = Double.parseDouble(values[i].trim());
                    String key = keys[i].trim();
                    
                    switch (key.toLowerCase()) {
                        case "battery":
                            battery = value;
                            break;
                        case "current":
                            current = value;
                            break;
                        case "speed":
                            speed = value;
                            break;
                        case "temp":
                            temp = value;
                            break;
                        case "distance":
                            distance = value;
                            break;
                        case "throttle":
                            throttle = value;
                            break;
                        case "psi":
                            psi = value;
                            break;
                        case "time":
                            // Use RCC time if available, otherwise system time
                            if (value > 0) timestamp = (long)value;
                            break;
                    }
                } catch (NumberFormatException e) {
                    // Skip non-numeric values
                }
            }
            
            System.out.println(String.format("Loco %s: Speed=%.1f, Throttle=%.1f, Battery=%.1f, Current=%.1f, Temp=%.1f, Psi=%.1f, Distance=%.1f", 
                locoId, speed, throttle, battery, current, temp, psi, distance));
            
            // Update locomotive activity and distance
            LocomotiveInfo locoInfo = discoveredLocomotives.get(locoId);
            if (locoInfo != null) {
                locoInfo.isActive = true;
                locoInfo.lastSeen = System.currentTimeMillis();
                locoInfo.distanceTraveled = distance;
            }
            
            // Update charts on EDT only if locomotive is selected
            final double fSpeed = speed, fThrottle = throttle, fBattery = battery, fCurrent = current, fTemp = temp, fPsi = psi;
            final long fTimestamp = timestamp;
            SwingUtilities.invokeLater(() -> {
                if (isLocomotiveSelected(locoId)) {
                    updateChartData(locoId, fSpeed, fThrottle, fBattery, fCurrent, fTemp, fPsi, fTimestamp);
                    // Update the selection panel to refresh distance display for selected locomotive
                    updateLocomotiveSelectionPanel();
                }
            });
            
        } catch (Exception e) {
            System.err.println("Error processing heartbeat values: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    private void processHeartbeatKeys(String topic, String payload) {
        try {
            // Extract locomotive ID from topic (cab/{locoId}/heartbeat/keys)
            String[] topicParts = topic.split("/");
            if (topicParts.length < 2) return;
            String locoId = topicParts[1];
            
            // Parse CSV keys: "Time,Distance,Bitstate,Speed,Lost,Throttle,ThrOut,Battery,Temp,Psi,Current"
            String[] keys = payload.split(",");
            locomotiveKeys.put(locoId, keys);
            
            System.out.println("Stored keys for locomotive " + locoId + ": " + payload);
            
        } catch (Exception e) {
            System.err.println("Error processing heartbeat keys: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    private void processIntroMessage(String topic, String payload) {
        try {
            // Extract locomotive ID from topic (cab/{locoId}/intro)
            String[] topicParts = topic.split("/");
            if (topicParts.length < 2) return;
            String locoId = topicParts[1];
            
            // Parse intro: "L,3,RCC,0.8,BIIIHBBBBBBB"
            String[] parts = payload.split(",");
            if (parts.length >= 4 && "L".equals(parts[0].trim())) {
                String type = parts[0].trim();
                String address = parts[1].trim();
                String name = parts[2].trim();
                String version = parts[3].trim();
                
                // Update locomotive info
                LocomotiveInfo locoInfo = discoveredLocomotives.get(locoId);
                if (locoInfo == null) {
                    locoInfo = new LocomotiveInfo(locoId);
                    discoveredLocomotives.put(locoId, locoInfo);
                }
                locoInfo.address = address;
                locoInfo.name = name;
                locoInfo.version = version;
                
                System.out.println(String.format("Locomotive %s introduced: Type=%s, Address=%s, System=%s, Version=%s", 
                    locoId, type, address, name, version));
                
                // Update UI on EDT
                SwingUtilities.invokeLater(() -> updateLocomotiveSelectionPanel());
            }
            
        } catch (Exception e) {
            System.err.println("Error processing intro message: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    private void ensureLocomotiveDiscovered(String locoId) {
        if (!discoveredLocomotives.containsKey(locoId)) {
            LocomotiveInfo locoInfo = new LocomotiveInfo(locoId);
            discoveredLocomotives.put(locoId, locoInfo);
            
            // Assign a color to this locomotive
            if (!locomotiveColors.containsKey(locoId)) {
                locomotiveColors.put(locoId, chartColors[colorIndex % chartColors.length]);
                colorIndex++;
            }
            
            SwingUtilities.invokeLater(() -> updateLocomotiveSelectionPanel());
        }
    }
    
    private void updateLocomotiveSelectionPanel() {
        locomotiveSelectionPanel.removeAll();
        
        if (discoveredLocomotives.isEmpty()) {
            locomotiveSelectionPanel.add(new JLabel("No locomotives discovered yet"));
        } else {
            // Add checkboxes for each locomotive with color indicators and distance
            for (LocomotiveInfo locoInfo : discoveredLocomotives.values()) {
                JPanel locoPanel = new JPanel(new FlowLayout(FlowLayout.LEFT, 5, 0));
                
                JCheckBox checkbox = locomotiveCheckboxes.get(locoInfo.id);
                if (checkbox == null) {
                    checkbox = new JCheckBox(locoInfo.getDisplayNameWithDistance(), true); // Default to selected
                    checkbox.addActionListener(e -> refreshCharts());
                    locomotiveCheckboxes.put(locoInfo.id, checkbox);
                } else {
                    // Update checkbox text with current distance
                    checkbox.setText(locoInfo.getDisplayNameWithDistance());
                }
                
                // Add activity indicator to checkbox text color
                if (locoInfo.isActive) {
                    checkbox.setForeground(Color.BLACK);
                } else {
                    checkbox.setForeground(Color.GRAY);
                }
                
                // Create color indicator
                Color locoColor = locomotiveColors.get(locoInfo.id);
                if (locoColor != null) {
                    JLabel colorIndicator = new JLabel("●");
                    colorIndicator.setForeground(locoColor);
                    colorIndicator.setFont(colorIndicator.getFont().deriveFont(16f));
                    locoPanel.add(colorIndicator);
                }
                
                locoPanel.add(checkbox);
                locomotiveSelectionPanel.add(locoPanel);
            }
        }
        
        locomotiveSelectionPanel.revalidate();
        locomotiveSelectionPanel.repaint();
    }
    
    private boolean isLocomotiveSelected(String locoId) {
        JCheckBox checkbox = locomotiveCheckboxes.get(locoId);
        return checkbox != null && checkbox.isSelected();
    }
    
    private void refreshCharts() {
        // Clear all datasets
        speedDataset.removeAllSeries();
        throttleDataset.removeAllSeries();
        batteryDataset.removeAllSeries();
        currentDataset.removeAllSeries();
        tempDataset.removeAllSeries();
        psiDataset.removeAllSeries();
        
        // Re-add selected locomotives
        for (String locoId : discoveredLocomotives.keySet()) {
            if (isLocomotiveSelected(locoId)) {
                TimeSeries speedSeries = speedSeriesMap.get(locoId);
                TimeSeries throttleSeries = throttleSeriesMap.get(locoId);
                TimeSeries batterySeries = batterySeriesMap.get(locoId);
                TimeSeries currentSeries = currentSeriesMap.get(locoId);
                TimeSeries tempSeries = tempSeriesMap.get(locoId);
                TimeSeries psiSeries = psiSeriesMap.get(locoId);
                
                if (speedSeries != null) {
                    speedDataset.addSeries(speedSeries);
                }
                if (throttleSeries != null) {
                    throttleDataset.addSeries(throttleSeries);
                }
                if (batterySeries != null) {
                    batteryDataset.addSeries(batterySeries);
                }
                if (currentSeries != null) {
                    currentDataset.addSeries(currentSeries);
                }
                if (tempSeries != null) {
                    tempDataset.addSeries(tempSeries);
                }
                if (psiSeries != null) {
                    psiDataset.addSeries(psiSeries);
                }
            }
        }
        
        // Apply colors after all series are added
        applyAllSeriesColors();
    }
    
    private void applyAllSeriesColors() {
        applyColorsToChart(speedChart, speedDataset);
        applyColorsToChart(throttleChart, throttleDataset);
        applyColorsToChart(batteryChart, batteryDataset);
        applyColorsToChart(currentChart, currentDataset);
        applyColorsToChart(tempChart, tempDataset);
        applyColorsToChart(psiChart, psiDataset);
    }
    
    private void applyColorsToChart(JFreeChart chart, TimeSeriesCollection dataset) {
        org.jfree.chart.plot.XYPlot plot = (org.jfree.chart.plot.XYPlot) chart.getPlot();
        org.jfree.chart.renderer.xy.XYItemRenderer renderer = plot.getRenderer();
        for (int i = 0; i < dataset.getSeriesCount(); i++) {
            String seriesKey = (String) dataset.getSeriesKey(i);
            String locoId = findLocoIdBySeriesName(seriesKey);
            if (locoId != null) {
                Color color = locomotiveColors.get(locoId);
                if (color != null) {
                    renderer.setSeriesPaint(i, color);
                }
            }
        }
    }
    
    private String findLocoIdBySeriesName(String seriesName) {
        for (Map.Entry<String, LocomotiveInfo> entry : discoveredLocomotives.entrySet()) {
            if (seriesName.equals(entry.getValue().toString())) {
                return entry.getKey();
            }
        }
        return null;
    }
    
    private void applySeriesColor(JFreeChart chart, TimeSeries series, String locoId) {
        Color locoColor = locomotiveColors.get(locoId);
        if (locoColor != null && chart.getPlot() instanceof org.jfree.chart.plot.XYPlot) {
            org.jfree.chart.plot.XYPlot plot = (org.jfree.chart.plot.XYPlot) chart.getPlot();
            org.jfree.chart.renderer.xy.XYItemRenderer renderer = plot.getRenderer();
            
            // Find the series index in the dataset
            TimeSeriesCollection dataset = (TimeSeriesCollection) plot.getDataset();
            int seriesIndex = dataset.indexOf(series.getKey());
            if (seriesIndex >= 0) {
                renderer.setSeriesPaint(seriesIndex, locoColor);
            }
        }
    }
    
    private void updateChartData(String locoId, double speed, double throttle, double battery, double current, double temp, double psi, long timestamp) {
        Second timePoint = new Second(new Date(timestamp));
        
        // Get locomotive display name
        LocomotiveInfo locoInfo = discoveredLocomotives.get(locoId);
        String displayName = locoInfo != null ? locoInfo.toString() : "Loco " + locoId;
        
        // Always store data for all locomotives
        // Update speed chart
        TimeSeries speedSeries = speedSeriesMap.get(locoId);
        if (speedSeries == null) {
            speedSeries = new TimeSeries(displayName);
            speedSeriesMap.put(locoId, speedSeries);
            if (isLocomotiveSelected(locoId)) {
                speedDataset.addSeries(speedSeries);
            }
        }
        speedSeries.addOrUpdate(timePoint, speed);
        
        // Update throttle chart
        TimeSeries throttleSeries = throttleSeriesMap.get(locoId);
        if (throttleSeries == null) {
            throttleSeries = new TimeSeries(displayName);
            throttleSeriesMap.put(locoId, throttleSeries);
            if (isLocomotiveSelected(locoId)) {
                throttleDataset.addSeries(throttleSeries);
            }
        }
        throttleSeries.addOrUpdate(timePoint, throttle);
        
        // Update battery chart
        TimeSeries batterySeries = batterySeriesMap.get(locoId);
        if (batterySeries == null) {
            batterySeries = new TimeSeries(displayName);
            batterySeriesMap.put(locoId, batterySeries);
            if (isLocomotiveSelected(locoId)) {
                batteryDataset.addSeries(batterySeries);
            }
        }
        batterySeries.addOrUpdate(timePoint, battery);
        
        // Update current chart
        TimeSeries currentSeries = currentSeriesMap.get(locoId);
        if (currentSeries == null) {
            currentSeries = new TimeSeries(displayName);
            currentSeriesMap.put(locoId, currentSeries);
            if (isLocomotiveSelected(locoId)) {
                currentDataset.addSeries(currentSeries);
            }
        }
        currentSeries.addOrUpdate(timePoint, current);
        
        // Update temperature chart
        TimeSeries tempSeries = tempSeriesMap.get(locoId);
        if (tempSeries == null) {
            tempSeries = new TimeSeries(displayName);
            tempSeriesMap.put(locoId, tempSeries);
            if (isLocomotiveSelected(locoId)) {
                tempDataset.addSeries(tempSeries);
            }
        }
        tempSeries.addOrUpdate(timePoint, temp);
        
        // Update pressure chart
        TimeSeries psiSeries = psiSeriesMap.get(locoId);
        if (psiSeries == null) {
            psiSeries = new TimeSeries(displayName);
            psiSeriesMap.put(locoId, psiSeries);
            if (isLocomotiveSelected(locoId)) {
                psiDataset.addSeries(psiSeries);
            }
        }
        psiSeries.addOrUpdate(timePoint, psi);
        
        // Limit data points to prevent memory issues
        limitSeriesSize(speedSeries, maxDataPoints);
        limitSeriesSize(throttleSeries, maxDataPoints);
        limitSeriesSize(batterySeries, maxDataPoints);
        limitSeriesSize(currentSeries, maxDataPoints);
        limitSeriesSize(tempSeries, maxDataPoints);
        limitSeriesSize(psiSeries, maxDataPoints);
    }
    
    private void limitSeriesSize(TimeSeries series, int maxSize) {
        while (series.getItemCount() > maxSize) {
            series.delete(0, 0);
        }
    }
    
    @Override
    public void dispose() {
        try {
            if (mqttClient != null && mqttClient.isConnected()) {
                mqttClient.disconnect();
                mqttClient.close();
            }
        } catch (MqttException e) {
            System.err.println("Error closing MQTT connection: " + e.getMessage());
        }
        super.dispose();
    }
    
    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> {
            RccMqttDataPlotterStandalone plotter = new RccMqttDataPlotterStandalone();
            plotter.setVisible(true);
            
            System.out.println("RCC MQTT Data Plotter started");
            System.out.println("Connect to your MQTT broker and start receiving heartbeat data");
        });
    }
}