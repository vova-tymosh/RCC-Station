#
# Copyright (c) 2024-2025 Volodymyr "Vova" Tymoshchuk
# Distributed under MIT licence, https://github.com/vova-tymosh/RCC/blob/main/LICENSE
# For more details go to https://github.com/vova-tymosh/RCC
#
# The above copyright notice shall be included in all
# copies or substantial portions of the Software.
#

pid=`ps ax | grep "python3 Comms.py" | grep -v "grep" | head -1 | awk '{print $1}'`
kill $pid 2> /dev/null


cd /home/rcc/Station
/home/rcc/venv/bin/python3 Comms.py &

