
pid=`ps ax | grep "python3 Comms.py" | grep -v "grep" | head -1 | awk '{print $1}'`
kill $pid 2> /dev/null


cd /home/rcc/Station
/home/rcc/venv/bin/python3 Comms.py &


#runuser -l vova /home/vova/Station/web_start.sh
