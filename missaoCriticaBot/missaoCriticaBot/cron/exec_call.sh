#!/bin/sh
clear
cd /app/missaoCriticaBot/cron/
lista_rpa="call_missaoCriticaBot.sh"

SHOW_LOGS=false
export TERM=xterm

for script in $lista_rpa
do
    # Procura o script por nome específico
    if pgrep -f "$script" > /dev/null
    then
		if [ "$SHOW_LOGS" = true ]; then
        	echo "O processo $script já está em execução."
		fi
    else
		if [ "$SHOW_LOGS" = true ]; then
        	echo "O processo $script não está em execução. Iniciando..."
		fi

        nohup sh $script >> /dev/stdout 2>&1 &
        
		if [ "$SHOW_LOGS" = true ]; then
			echo "Iniciado $script com PID $!"
		fi
    fi
done
