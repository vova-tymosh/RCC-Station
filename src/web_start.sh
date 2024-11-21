
pid=`ps ax | grep "python3 StationWeb.py" | grep -v "grep" | head -1 | awk '{print $1}'`
kill $pid

cd /home/vova/Station
python3 StationWeb.py &

