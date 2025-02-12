#!/bin/sh
cd /app/missaoCriticaBot/
cpu_threshold='80'
mem_threshold='1024'

SHOW_LOGS=false
export TERM=xterm

while true; do
    cpu_idle=$(top -bn 1 | grep '^%Cpu' | awk '{print $8}' | cut -f 1 -d ',')
    if ! [ "$cpu_idle" -eq "$cpu_idle" ] 2>/dev/null; then
        cpu_idle=100
    fi
    cpu_use=$((100 - cpu_idle))
    mem_free=$(free -m | grep "Mem" | awk '{print $4+$6}')

    # Exibir informações de CPU e memória somente se SHOW_LOGS for true
    if [ "$SHOW_LOGS" = true ]; then
        echo "Exec: CPU:$cpu_use MEM:$mem_free - $(date +%H:%M:%S)"
    fi

    if [ "$mem_free" -gt "$mem_threshold" ] && [ "$cpu_use" -lt "$cpu_threshold" ]; then

        if pgrep -f missaoCriticaBot.py > /dev/null; then
            if [ "$SHOW_LOGS" = true ]; then
                echo "O processo missaoCriticaBot.py já está em execução."
            fi
        else
            if [ "$SHOW_LOGS" = true ]; then
                echo "O processo missaoCriticaBot não está em execução. Reiniciando..."
                echo "Tentando iniciar o missaoCriticaBot.py..."
            fi

            /usr/local/bin/python3 missaoCriticaBot.py > /dev/stdout 2>&1 &
            
            if [ "$SHOW_LOGS" = true ]; then
                echo "Iniciado missaoCriticaBot.py com PID $!"
            fi
        fi
        sleep 5
    fi
done
