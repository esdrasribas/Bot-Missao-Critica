# Use uma imagem base do Python
FROM missao-critica-bot:latest

# Defina o fuso horário
ENV TZ="America/Sao_Paulo"
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Configurar o proxy para o apt-get
ARG HTTP_PROXY
ARG HTTPS_PROXY

# Definir variáveis de ambiente para proxy
ENV http_proxy=${HTTP_PROXY}
ENV https_proxy=${HTTPS_PROXY}
ENV no_proxy=localhost,127.0.0.1

# Atualizar repositórios e instalar o cron
RUN apt-get update && apt-get install -y cron

# Copie o requirements.txt e instale as dependências
COPY requirements.txt ./  
RUN pip install --no-cache-dir -r requirements.txt

# Copie o restante do código do bot para dentro do container
COPY . /app

# Defina o diretório de trabalho dentro do container
WORKDIR /app


# Dê permissão de execução para os scripts
RUN chmod +x /app/missaoCriticaBot/missaoCriticaBot/cron/call_missaoCriticaBot.sh \
    && chmod +x /app/missaoCriticaBot/missaoCriticaBot/cron/exec_call.sh

# Copiar o arquivo cronjob para o diretório correto do cron no container
COPY cronjob /etc/cron.d/monitorar_cron

# Dar permissão de execução para o cron job
RUN chmod 0644 /etc/cron.d/monitorar_cron

# Adicionar o cron service
RUN crontab /etc/cron.d/monitorar_cron

# # Inicia apenas o cron como serviço principal do container
CMD ["cron", "-f"]

# Rodar o serviço cron junto com o bot
# CMD cron && python3 missaoCriticaBot/missaoCriticaBot.py
