import pymysql
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

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

def mover_reparos_para_historico():
    conn = conectar_ao_banco()
    if conn is None:
        print("Conexão com o banco de dados falhou. Não é possível mover reparos para o histórico.")
        return

    try:
        cursor = conn.cursor()

        # Selecionar todas as colunas relevantes com status 'Fechado' e escalonado 'FIM_COB'
        select_query = """
        SELECT numero, chat_id, num_ba, status_ba, estacao_ba, caso_stc, causa, posto, status, circuito, 
               segmento, cliente, velocidade, tecn_acesso, perimetro, cidade, ult_msg_crm, uf, psr, 
               produto, tempo_bd_aberto, reincidente, nv_escalacao, escala_inicial, data_abertura, 
               data_atualizacao, data_entrada_posto, data_cobranca, data_fechado_missao_critica, 
               data_escalonamento, data_proxima_cobranca, hierarquia, ult_msg, sistema, 
               ult_msg_critico, previsao_conclusao, falha_ou_pendencia, chave_busca_info, 
               status_questionamento, escalonado, estado_fluxo, notificacao_inicial, data_etl
        FROM notifica_missao_critica
        WHERE status = 'Fechado' AND escalonado = 'FIM_COB'
        """
        cursor.execute(select_query)
        reparos_fechados = cursor.fetchall()

        if not reparos_fechados:
            print("Nenhum reparo para mover para o histórico.")
            return

        # Inserir os reparos na tabela de histórico
        insert_query = """
        INSERT INTO notifica_missao_critica_hist (numero, chat_id, num_ba, status_ba, estacao_ba, caso_stc, 
            causa, posto, status, circuito, segmento, cliente, velocidade, tecn_acesso, perimetro, 
            cidade, ult_msg_crm, uf, psr, produto, tempo_bd_aberto, reincidente, nv_escalacao, 
            escala_inicial, data_abertura, data_atualizacao, data_entrada_posto, data_cobranca, 
            data_fechado_missao_critica, data_escalonamento, data_proxima_cobranca, hierarquia, 
            ult_msg, sistema, ult_msg_critico, previsao_conclusao, falha_ou_pendencia, chave_busca_info, 
            status_questionamento, escalonado, estado_fluxo, notificacao_inicial, data_etl)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        for reparo in reparos_fechados:
            numero = reparo[0]    
            circuito = reparo[9]  
            
            # Verificar se o circuito e o número já existem na tabela de histórico
            cursor.execute("SELECT 1 FROM notifica_missao_critica_hist WHERE circuito = %s AND numero = %s", (circuito, numero))
            existe_no_historico = cursor.fetchone()
            
            if existe_no_historico:
                # Se o circuito e o número já existem no histórico, apenas remover da tabela notifica_missao_critica
                cursor.execute("DELETE FROM notifica_missao_critica WHERE circuito = %s AND numero = %s", (circuito, numero))
            else:
                # Caso não exista no histórico, inserir normalmente
                cursor.execute(insert_query, reparo)

        # Confirmar as alterações
        conn.commit()

        print(f"{cursor.rowcount} reparos movidos para o histórico.")

    except Exception as e:
        print(f"Erro ao mover reparos para o histórico: {e}")
        conn.rollback()
    finally:
        if 'cursor' in locals():
            cursor.close()
        if conn:
            conn.close()

mover_reparos_para_historico()
