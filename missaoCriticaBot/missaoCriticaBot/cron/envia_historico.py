import schedule
import time
import telebot
from datetime import datetime, timedelta
import pymysql
import os
import logging
from conn.mysqlConnector import buscar_chat_ids_todos
from dotenv import load_dotenv
load_dotenv()

# Configuração do logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def conectar_ao_banco():
    try:
        connection = pymysql.connect(
            host=os.environ.get('DB_HOST'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
            database=os.environ.get('DB_NAME')
        )
        return connection
    except pymysql.MySQLError as e:
        print(f"Erro ao conectar no banco: {e}")


# Configurações do Telegram Bot
TELEGRAM_API_TOKEN = os.getenv('TOKEN_TELEGRAM')
bot = telebot.TeleBot(TELEGRAM_API_TOKEN)


def obter_quantidades_reparos():
    conn = conectar_ao_banco()
    if conn is None:
        return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN nv_escalacao = 3 THEN 1 END) AS acima_6h,
                    COUNT(CASE WHEN nv_escalacao = 2 THEN 1 END) AS acima_4h,
                    COUNT(CASE WHEN nv_escalacao = 1 THEN 1 END) AS abaixo_4h
                FROM notifica_missao_critica
                WHERE status != 'Fechado';
            """)
            acima_6h, acima_4h, abaixo_4h = cursor.fetchone()
            
            cursor.execute("""
                SELECT COUNT(*) 
                FROM notifica_missao_critica_hist 
                WHERE status = 'Fechado' 
                AND data_fechado_missao_critica >= NOW() - INTERVAL 24 HOUR 
                AND escalonado = 'FIM_COB';
            """)
            resolvidos = cursor.fetchone()[0]

            return acima_6h, acima_4h, abaixo_4h, resolvidos
    finally:
        conn.close()

def obter_lista_reparos_fechados():
    conn = conectar_ao_banco()
    if conn is None:
        return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    '✔️' AS status_icone,
                    uf,
                    posto,
                    circuito,
                    data_abertura,
                    data_fechado_missao_critica
                FROM notifica_missao_critica_hist
                WHERE status = 'Fechado'
                AND data_fechado_missao_critica >= NOW() - INTERVAL 24 HOUR AND escalonado = 'FIM_COB';
            """)
            return cursor.fetchall()
    finally:
        conn.close()


def obter_lista_reparos():
    conn = conectar_ao_banco()
    if conn is None:
        return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN nv_escalacao = 3 THEN '🚨'
                        WHEN nv_escalacao = 2 THEN '⚠️'
                        ELSE '🟢'
                    END AS status_icone,
                    uf,
                    posto,
                    circuito,
                    data_abertura
                FROM notifica_missao_critica
                WHERE status != 'Fechado'
                ORDER BY nv_escalacao DESC, data_abertura ASC;
            """)
            return cursor.fetchall()
    finally:
        conn.close()

def formatar_tempo_aberto(data_abertura):
    if not isinstance(data_abertura, datetime):
        raise ValueError("data_abertura deve ser um objeto datetime")

    # Usar a data atual se o reparo ainda estiver aberto (data_fechado é None)
    delta = datetime.now() - data_abertura

    horas, resto = divmod(delta.total_seconds(), 3600)
    minutos, segundos = divmod(resto, 60)

    return f"{int(horas):02}:{int(minutos):02}:{int(segundos):02}"

def formatar_tempo_fechado(data_abertura, data_fechado):
    if not isinstance(data_abertura, datetime):
        raise ValueError("data_abertura deve ser um objeto datetime")

    # Usar a data atual se o reparo ainda estiver aberto (data_fechado é None)
    delta = data_fechado - data_abertura

    horas, resto = divmod(delta.total_seconds(), 3600)
    minutos, segundos = divmod(resto, 60)

    return f"{int(horas):02}:{int(minutos):02}:{int(segundos):02}"

def enviar_status_reparo(chat_id=None):
    chat_ids = buscar_chat_ids_todos()
    acima_6h, acima_4h, abaixo_4h, resolvidos = obter_quantidades_reparos()
    lista_reparos = obter_lista_reparos()
    lista_reparos_fechados = obter_lista_reparos_fechados()

    if acima_6h is None or acima_4h is None or abaixo_4h is None or resolvidos is None:
        print("Erro ao obter dados do banco de dados.")
        return

    mensagem = (
        "*STATUS REPARO - HISTÓRICO*\n\n"
        f"🚨    *{acima_6h}  com mais de 6H*\n"
        f"⚠️    *{acima_4h}  Acima de 4H*\n"
        f"🟢    *{abaixo_4h}  Abaixo de 4H*\n"
        f"✔️    *{resolvidos}  Resolvidos*\n\n"
        "       *UF  | Posto     | Circuito         |  Tempo *\n"
    )

    for status, uf, posto, circuito, data_abertura in lista_reparos:
        tempo_formatado = formatar_tempo_aberto(data_abertura)
        mensagem += f"{status}  {uf} | {posto} | {circuito}   | {tempo_formatado} \n"

    mensagem += "\n*Reparos Fechados nas Últimas 24 Horas*\n"

    for status, uf, posto, circuito, data_abertura, data_fechado_missao_critica in lista_reparos_fechados:
        tempo_formatado = formatar_tempo_fechado(data_abertura, data_fechado_missao_critica)
        mensagem += f"{status}  {uf} | {posto} | {circuito}   | {tempo_formatado} \n"

    mensagem += "\n*Comando:*\n/historico\n"
    if chat_id:
        try:
            bot.send_message(chat_id, mensagem, parse_mode='Markdown')
            logging.info(f"Mensagem de histórico enviada para chat_id: {chat_id}")
        except Exception as e:
            logging.error(f"Erro ao enviar mensagem para chat_id {chat_id}: {e}")
    else:
        for chat_id, hierarquia, gestor, uf, regional in chat_ids:
            if chat_id is None or chat_id == 0:
                logging.warning(f"Usuário sem chat_id válido: hierarquia={hierarquia}, gestor={gestor}, uf={uf}, regional={regional}")
                continue  

            try:
                bot.send_message(chat_id, mensagem, parse_mode='Markdown')
                logging.info(f"Mensagem enviada para chat_id: {chat_id}")
            except Exception as e:
                logging.error(f"Erro ao enviar mensagem para chat_id {chat_id}: {e}")
