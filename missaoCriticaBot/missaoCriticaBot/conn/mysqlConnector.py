import pymysql
import os
from dotenv import load_dotenv
import sys
# Adiciona o diretório pai ao sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import logging
from datetime import datetime
from pymysql.cursors import DictCursor
from pymysql import MySQLError
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


def buscar_reparos():
    connection = conectar_ao_banco()
    
    if connection:
        try:
            with connection.cursor(DictCursor) as cursor: 
                query = f"SELECT * FROM notifica_missao_critica WHERE status not in ('Fechado','Blacklist') and escalonado = '-'"
                cursor.execute(query)
                reparos = cursor.fetchall()
                if reparos:
                    return reparos
                else:
                    logging.info("[buscar_reparos] Nenhum Reparo Missão Crítica encontrado para enviar notificação.")
                    return []
        except MySQLError as e:
            logging.error(f"Erro ao acessar o banco de dados: {e}")
        finally:
            connection.close()
    return []

def buscar_reparos_escalamento():
    connection = conectar_ao_banco()
    
    if connection:
        try:
            with connection.cursor(DictCursor) as cursor: 
                query = f"SELECT * FROM notifica_missao_critica WHERE status not in ('Fechado','Blacklist') AND escalonado != 'FIM_COB' AND notificacao_inicial = 'SIM';"
                cursor.execute(query)
                reparos = cursor.fetchall()
                if reparos:
                    return reparos
                else:
                    logging.info("[buscar_reparos_escalamento] Nenhum Reparo Missão Crítica encontrado para enviar notificação.")
                    return []
        except MySQLError as e:
            logging.error(f"Erro ao acessar o banco de dados: {e}")
        finally:
            connection.close()
    return []


def buscar_atualizacao():
    connection = conectar_ao_banco()
    
    if connection:
        try:
            with connection.cursor(DictCursor) as cursor: 
                query = f"SELECT * FROM notifica_missao_critica WHERE status not in ('Fechado','Blacklist') and escalonado = 'atualizar_notificacao'"
                cursor.execute(query)
                reparos = cursor.fetchall()
                if reparos:
                    return reparos
                else:
                    logging.info("[buscar_atualizacao] Nenhum Reparo Missão Crítica encontrado para enviar notificação.")
                    return []
        except MySQLError as e:
            logging.error(f"Erro ao acessar o banco de dados: {e}")
        finally:
            connection.close()
    return []

def atualizar_notificacao(circuito, numero):
    connection = conectar_ao_banco()
    if connection:
        try:
            with connection.cursor() as cursor:
                update_query = "UPDATE notifica_missao_critica SET escalonado = 'atualizar_notificacao' WHERE status not in ('Fechado','Blacklist') and circuito = %s and numero = %s"
                cursor.execute(update_query, (circuito, numero))
                connection.commit()
                logging.info(f"[atualizar_notificacao] Registro atualizado com sucesso para circuito: {circuito} numero: {numero}")
        except MySQLError as e:
            logging.error(f"[atualizar_notificacao] Erro ao atualizar o banco de dados: {e}")
        finally:
            connection.close()




def buscar_cobranca():
    connection = conectar_ao_banco()
    
    if connection:
        try:
            with connection.cursor(DictCursor) as cursor:  
                data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logging.info(f"[buscar_cobranca] data_atual: {data_atual}")
                query = "SELECT * FROM notifica_missao_critica WHERE escalonado = 'COBRANCA' AND data_proxima_cobranca <= %s and notificacao_inicial = 'SIM' and nv_escalacao >= 2"
                cursor.execute(query, (data_atual,))
                reparos = cursor.fetchall()

                if reparos:
                    return reparos
                else:
                    logging.info("[processar_reparos] Nenhum Reparo Missão Crítica encontrado para cobrança")
                    return []
        except MySQLError as e:
            logging.error(f"Erro ao acessar o banco de dados: {e}")
        finally:
            connection.close()
    return []

def buscar_cobranca_fechados():
    connection = conectar_ao_banco()
    
    if connection:
        try:
            with connection.cursor(DictCursor) as cursor:  
                logging.info(f"[buscar_cobranca_fechados] Buscando reparos fechados!")
                query = "SELECT * FROM notifica_missao_critica WHERE escalonado = 'COBRANCA' AND notificacao_inicial = 'SIM'"
                cursor.execute(query)
                reparos = cursor.fetchall()

                if reparos:
                    return reparos
                else:
                    logging.info("[processar_reparos] Nenhum Reparo Missão Crítica encontrado para cobrança")
                    return []
        except MySQLError as e:
            logging.error(f"Erro ao acessar o banco de dados: {e}")
        finally:
            connection.close()
    return []

def fechados_n_notificados():
    connection = conectar_ao_banco()
    
    if connection:
        try:
            with connection.cursor(DictCursor) as cursor:  
                logging.info(f"[fechados_n_notificados] Buscando reparos fechados não notificados!")
                query = "SELECT * FROM notifica_missao_critica WHERE escalonado = '-' and status in ('Fechado', 'Blacklist')"
                cursor.execute(query)
                reparos = cursor.fetchall()

                if reparos:
                    return reparos
                else:
                    logging.info("[fechados_n_notificados] Nenhum Reparo Missão Crítica encontrado para cobrança")
                    return []
        except MySQLError as e:
            logging.error(f"Erro ao acessar o banco de dados: {e}")
        finally:
            connection.close()
    return []


def atualizar_data_proxima_cobranca(circuito, proxima_cobranca, numero):
    connection = conectar_ao_banco()
    if connection:
        try:
            with connection.cursor() as cursor:
                update_query = "UPDATE notifica_missao_critica SET data_proxima_cobranca = %s WHERE circuito = %s and numero = %s"
                cursor.execute(update_query, (proxima_cobranca, circuito, numero))
                connection.commit()
                logging.info(f"[atualizar_data_proxima_cobranca] Data da próxima cobrança atualizada para o circuito {circuito} numero{numero}: {proxima_cobranca}.")
        except MySQLError as e:
            logging.error(f"[atualizar_data_proxima_cobranca]  Erro ao atualizar a data da próxima cobrança: {e}")
        finally:
            connection.close()

def atualizar_escalamento_inicial(escala_inicial, nv_escalacao, notificacao_inicial, circuito, numero):
    connection = conectar_ao_banco()
    if connection:
        try:
            with connection.cursor() as cursor:
                update_query = "UPDATE notifica_missao_critica SET escala_inicial = %s, nv_escalacao = %s, escalonado = 'COBRANCA', notificacao_inicial = %s WHERE circuito = %s and numero = %s"
                cursor.execute(update_query, (escala_inicial, nv_escalacao, notificacao_inicial, circuito, numero))
                connection.commit()
                logging.info(f"[atualizar_escalamento_inicial] Registro atualizado com sucesso para circuito: {circuito} numero: {numero}")
        except MySQLError as e:
            logging.error(f"[atualizar_escalamento_inicial] Erro ao atualizar o banco de dados: {e}")
        finally:
            connection.close()

def atualizar_escalamento_inicial_notificacao(nv_escalacao, escala_inicial, circuito, numero):
    connection = conectar_ao_banco()
    if connection:
        try:
            with connection.cursor() as cursor:
                update_query = "UPDATE notifica_missao_critica SET nv_escalacao = %s, escala_inicial = %s, escalonado = '-' WHERE circuito = %s and numero = %s"
                cursor.execute(update_query, (nv_escalacao, escala_inicial, circuito, numero))
                connection.commit()
                logging.info(f"Registro atualizado com sucesso para circuito: {circuito}")
        except MySQLError as e:
            logging.error(f"[atualizar_escalamento_inicial_notificacao] Erro ao atualizar o banco de dados: {e}")
        finally:
            connection.close()

def busca_nv_escalacao(circuito, numero):
    connection = conectar_ao_banco()
    if connection:
        try:
            with connection.cursor(DictCursor) as cursor:
                query = "SELECT nv_escalacao FROM notifica_missao_critica WHERE circuito = %s and numero = %s"
                cursor.execute(query, (circuito,numero))
                resultado = cursor.fetchone()  # Buscar um único resultado
                connection.commit()
                logging.info(f"Buscando nv_escalacao para circuito: {circuito} numero: {numero}")

                if resultado:
                    return resultado  # Retorna o dicionário com os dados
                else:
                    logging.error(f"[busca_nv_escalacao] Nenhum dado encontrado para o circuito {circuito} numero {numero}")
                    return None
        except MySQLError as e:
            logging.error(f"[busca_nv_escalacao] Erro ao acessar o banco de dados: {e}")
            return None
        finally:
            connection.close()
    else:
        logging.error("[busca_nv_escalacao] Falha ao conectar ao banco de dados.")
        return None
            

def atualizar_escalamento_cobranca(escalonado, circuito, numero):
    connection = conectar_ao_banco()
    if connection:
        try:
            with connection.cursor() as cursor:
                data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logging.info(f"[atualizar_escalamento_cobranca] data_atual: {data_atual}")
                update_query = "UPDATE notifica_missao_critica SET escalonado = %s, data_fechado_missao_critica = %s WHERE circuito = %s and numero =%s"
                cursor.execute(update_query, (escalonado, data_atual, circuito, numero))
                connection.commit()
                logging.info(f"[atualizar_escalamento_cobranca] Registro atualizado com sucesso para circuito: {circuito} numero: {numero}")
        except MySQLError as e:
            logging.error(f"[atualizar_escalamento_cobranca] Erro ao atualizar o banco de dados: {e}")
        finally:
            connection.close()

# Função para limpar a coluna chave_busca_info
def limpar_chave_busca_info(circuito, numero):
    connection = conectar_ao_banco()
    if connection:
        try:
            with connection.cursor() as cursor:
                cursor = connection.cursor()
                logging.info(f"[limpar_chave_busca_info] limpando chave_busca_info circuito: {circuito}")
                query = "UPDATE notifica_missao_critica SET chave_busca_info = NULL WHERE circuito = %s and numero = %s;"
                cursor.execute(query, (circuito, numero))
                connection.commit()
            logging.info(f"[limpar_chave_busca_info] chaves limpas para o circuito {circuito} numero {numero}.")
        except Exception as e:
            logging.error(f"[limpar_chave_busca_info] Erro ao limpar chave_busca_info para o circuito {circuito} numero {numero}: {e}")
        finally:
            cursor.close()


def buscar_fluxo_no_bd(circuito, numero):
    connection = conectar_ao_banco()
    if connection:
        try:
            with connection.cursor() as cursor:
                query = "SELECT chave_busca_info FROM notifica_missao_critica WHERE circuito = %s and numero = %s"
                cursor.execute(query, (circuito, numero))
                result = cursor.fetchone()  
                logging.info(f"Registro encontrado para circuito: {circuito} numero: {numero}")
                return result
        except MySQLError as e:
            logging.error(f"Erro ao buscar no banco de dados: {e}")
        finally:
            connection.close()

def atualizar_ult_msg_no_bd(mensagem, circuito, numero):
    connection = conectar_ao_banco()
    if connection:
        try:
            with connection.cursor() as cursor:
                update_query = "UPDATE notifica_missao_critica SET ult_msg_critico = %s WHERE circuito = %s and numero = %s"
                cursor.execute(update_query, (mensagem, circuito, numero))
                connection.commit()
                logging.info(f"Fluxo ult_msg_critico atualizado com sucesso para circuito: {circuito} numero: {numero}")
        except MySQLError as e:
            logging.error(f"[atualizar_ult_msg_no_bd] Erro ao atualizar o banco de dados: {e}")
        finally:
            connection.close()
            
def salvar_fluxo_no_bd(fluxo_atual, circuito, numero):
    connection = conectar_ao_banco()
    if connection:
        try:
            with connection.cursor() as cursor:
                update_query = "UPDATE notifica_missao_critica SET chave_busca_info = %s WHERE circuito = %s and numero = %s"
                cursor.execute(update_query, (fluxo_atual, circuito, numero))
                connection.commit()
                logging.info(f"Fluxo chave_busca_info atualizado com sucesso para circuito: {circuito} numero: {numero}")
        except MySQLError as e:
            logging.error(f"[salvar_fluxo_no_bd] Erro ao atualizar o banco de dados: {e}")
        finally:
            connection.close()
            
def atualizar_previsao_conclusao(previsao_conclusao, circuito, numero):
    connection = conectar_ao_banco()
    if connection:
        try:
            with connection.cursor() as cursor:
                update_query = "UPDATE notifica_missao_critica SET previsao_conclusao = %s WHERE circuito = %s and numero = %s"
                cursor.execute(update_query, (previsao_conclusao, circuito, numero))
                connection.commit()
                logging.info(f"[atualizar_previsao_conclusao] Fluxo previsao_conclusao atualizado com sucesso para circuito: {circuito} numero {numero}")
        except MySQLError as e:
            logging.error(f"[atualizar_previsao_conclusao] Erro ao atualizar o banco de dados: {e}")
        finally:
            connection.close()

def atualizar_data_atualizacao(data, circuito, numero):
    connection = conectar_ao_banco()
    if connection:
        try:
            with connection.cursor() as cursor:
                update_query = "UPDATE notifica_missao_critica SET data_cobranca = %s WHERE circuito = %s and numero = %s"
                cursor.execute(update_query, (data, circuito, numero))
                connection.commit()
                logging.info(f"[atualizar_data_atualizacao] Data última atualização enviada com sucesso para circuito: {circuito} numero {numero}")
        except MySQLError as e:
            logging.error(f"[atualizar_data_atualizacao] Erro ao atualizar o banco de dados: {e}")
        finally:
            connection.close()
            
def atualizar_falha_ou_pendencia(falha_ou_pendencia, circuito, numero):
    connection = conectar_ao_banco()
    if connection:
        try:
            with connection.cursor() as cursor:
                update_query = "UPDATE notifica_missao_critica SET falha_ou_pendencia = %s WHERE circuito = %s and numero = %s"
                cursor.execute(update_query, (falha_ou_pendencia, circuito, numero))
                connection.commit()
                logging.info(f"Fluxo previsao_conclusao atualizado com sucesso para circuito: {circuito} numero: {numero}")
        except MySQLError as e:
            logging.error(f"[atualizar_falha_ou_pendencia] Erro ao atualizar o banco de dados: {e}")
        finally:
            connection.close()

def atualizar_valid_mask(mask, data_atual, circuito, numero):
    connection = conectar_ao_banco()
    if connection:
        try:
            with connection.cursor() as cursor:
                update_query = "UPDATE notifica_missao_critica SET ult_msg_crm = %s, data_cobranca = %s WHERE circuito = %s and numero = %s"
                cursor.execute(update_query, (mask, data_atual, circuito, numero))
                connection.commit()
                logging.info(f"[atualizar_valid_mask]Fluxo previsao_conclusao atualizado com sucesso para circuito: {circuito} numero: {numero}")
        except MySQLError as e:
            logging.error(f"[atualizar_valid_mask] Erro ao atualizar o banco de dados: {e}")
        finally:
            connection.close()
            
def verificar_matricula(matricula):
    logging.info(f"Verificando matrícula: {matricula}")
    connection = conectar_ao_banco()
    if connection:
        try:
            with connection.cursor() as cursor:
                query = "SELECT * FROM cadastro_missao_critica WHERE matricula = %s"
                cursor.execute(query, (matricula,))
                result = cursor.fetchone()
                logging.info(f"[verificar_matricula] Matrícula verificada: {matricula}, Resultado: {result}")
                return result
        except MySQLError as e:
            logging.error(f"[verificar_matricula] Erro ao verificar a matrícula: {e}")
        finally:
            connection.close()
    return None

# Função para atualizar o chat_id do usuário
def atualizar_chatid(chat_id, matricula):
    logging.info(f"Atualizando chat_id para matrícula: {matricula}, chat_id: {chat_id}")
    connection = conectar_ao_banco()
    if connection:
        try:
            with connection.cursor() as cursor:
                update_query = "UPDATE cadastro_missao_critica SET chatid_cadastro = %s, cadastro = 'Cadastrado', data_cadastro = NOW() WHERE matricula = %s"
                cursor.execute(update_query, (chat_id, matricula))
                connection.commit()
                logging.info(f"[atualizar_chatid] Chat_id atualizado com sucesso para matrícula: {matricula}")
        except MySQLError as e:
            logging.error(f"[atualizar_chatid] Erro ao atualizar o chat_id: {e}")
        finally:
            connection.close()
            
def buscar_chatid_responsavel(uf):
    """
    Busca o chat_id do responsável pela cobrança com base na UF do reparo.
    """
    regionais = {
        'SUDESTE': ['RJ', 'SP', 'ES', 'MG'],
        'NE_NO': ['AM', 'PA', 'RR', 'AP', 'MA', 'CE', 'AL', 'BA', 'PE', 'PB', 'PI', 'SE', 'RN'],
        'SUL': ['PR', 'RS', 'SC'],
        'CO':['MT', 'MS', 'GO', 'DF', 'AC', 'RO', 'TO'],
    }

    connection = conectar_ao_banco()

    if connection:
        try:
            with connection.cursor(DictCursor) as cursor:
                # Identifica a região responsável pela UF
                regiao_responsavel = None
                for regiao, ufs in regionais.items():
                    if uf in ufs:
                        regiao_responsavel = regiao
                        break

                if regiao_responsavel:
                    # Consulta o chatid_cadastro e nome do responsável pela região
                    query = "SELECT chatid_cadastro, nome FROM cadastro_missao_critica WHERE regional = %s and chatid_cadastro <> 0;"
                    cursor.execute(query, (regiao_responsavel,))
                    result = cursor.fetchone()
                    if result:
                        return {'chat_id': result['chatid_cadastro'], 'nome': result['nome']}
                    else:
                        logging.warning(f"[buscar_chatid_responsavel] Nenhum responsável encontrado para a região: {regiao_responsavel}")
                else:
                    logging.warning(f"[buscar_chatid_responsavel] UF {uf} não encontrada em nenhuma região")
                
        except MySQLError as e:
            logging.error(f"[buscar_chatid_responsavel] Erro ao acessar o banco de dados: {e}")
        finally:
            connection.close()
    return None





def obter_regional(uf):
    """
    Busca o chat_id do responsável pela cobrança com base na UF do reparo.
    """
    logging.info(f"[obter_regional] Buscando região para UF: {uf}")
    regionais = {
        'SUDESTE': ['RJ', 'SP', 'ES', 'MG'],
        'NE_NO': ['AM', 'PA', 'RR', 'AP', 'MA', 'CE', 'AL', 'BA', 'PE', 'PB', 'PI', 'SE', 'RN'],
        'SUL': ['PR', 'RS', 'SC'],
        'CO':['MT', 'MS', 'GO', 'DF', 'AC', 'RO', 'TO'],
    }

    connection = conectar_ao_banco()

    if connection:
        try:
            with connection.cursor(DictCursor) as cursor:
                # Identifica a região responsável pela UF

                for regiao, ufs in regionais.items():
                    if uf in ufs:
                        return regiao
                return None  # Caso a UF não corresponda a nenhuma região              
        except MySQLError as e:
            logging.error(f"[obter_regional] Erro ao acessar o banco de dados: {e}")
        finally:
            connection.close()
    return None



# Função para buscar todos os chat IDs
def buscar_chat_ids_todos():
    # Conectar ao banco de dados e buscar todos os usuários
    with conectar_ao_banco() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT chatid_cadastro, hierarquia, gestor, uf, regional FROM cadastro_missao_critica where chatid_cadastro <> 0")
        return cursor.fetchall()  # Retorna uma lista de tuplas (chat_id, hierarquia, gestor)

def buscar_gestor_b2b_por_regional(regional):
    """
    Busca todos os gestores B2B associados à regional fornecida no banco de dados.
    
    :param regional: A regional para a qual queremos buscar os gestores B2B.
    :return: Lista de dicionários contendo 'chat_id' e 'nome' dos gestores B2B da regional.
    """
    connection = conectar_ao_banco()
    if connection:
        try:
            with connection.cursor(DictCursor) as cursor:
                query = """
                SELECT chatid_cadastro, nome 
                FROM cadastro_missao_critica 
                WHERE regional = %s AND gestor = 'b2b' AND hierarquia = 'Gerente' and chatid_cadastro <> 0
                """
                cursor.execute(query, (regional))
                gestores_b2b = cursor.fetchone()  # Busca todos os resultados correspondentes
                if gestores_b2b:
                    logging.info(f"[buscar_gestor_b2b_por_regional] Gestor B2B encontrado para a regional {regional}: {gestores_b2b}")
                else:
                    logging.warning(f"[buscar_gestor_b2b_por_regional] Nenhum gestor B2B encontrado para a regional {regional}.")
                return gestores_b2b
                
        except MySQLError as e:
            logging.error(f"[buscar_gestor_b2b_por_regional] Erro ao buscar gestores B2B para a regional {regional}: {e}")
            return None
        finally:
            connection.close()
    else:
        logging.error("[buscar_gestor_b2b_por_regional] Erro ao conectar ao banco de dados.")
        return None


# Função para atualizar o chat_id do usuário
def atualizar_circuito_chatid(chat_id, circuito, numero):
    logging.info(f"Atualizando chat_id para circuito: {circuito}, chat_id: {chat_id}")
    connection = conectar_ao_banco()
    if connection:
        try:
            with connection.cursor() as cursor:
                update_query = "UPDATE notifica_missao_critica SET chat_id = %s WHERE circuito = %s and numero = %s"
                cursor.execute(update_query, (chat_id, circuito, numero))
                connection.commit()
                logging.info(f"[atualizar_circuito_chatid] Chat_id atualizado com sucesso para Circuito: {circuito} numero: {numero}")
        except MySQLError as e:
            logging.error(f"[atualizar_circuito_chatid] Erro ao atualizar o chat_id: {e}")
        finally:
            connection.close()
            
            
def obter_estado_usuario(chat_id, circuito, numero):
    connection = conectar_ao_banco()
    if connection:
        try:
            with connection.cursor(DictCursor) as cursor:
                query = "SELECT circuito, estado_fluxo FROM notifica_missao_critica WHERE chat_id = %s and circuito = %s and numero = %s"
                cursor.execute(query, (chat_id, circuito, numero))
                result = cursor.fetchone()  
                logging.info(f"[obter_estado_usuario]  Registro encontrado para circuito: {circuito} chat_id: {chat_id}")
                return result
        except MySQLError as e:
            logging.error(f"[obter_estado_usuario] Erro ao buscar no banco de dados: {e}")
        finally:
            connection.close()
                        
def salvar_estado_usuario(chat_id, estado_fluxo, circuito, numero):
    connection = conectar_ao_banco()
    if connection:
        try:
            with connection.cursor() as cursor:
                update_query = "UPDATE notifica_missao_critica SET estado_fluxo = %s WHERE chat_id = %s and circuito = %s and numero = %s"
                cursor.execute(update_query, (estado_fluxo, chat_id, circuito, numero))
                connection.commit()
                logging.info(f"[salvar_estado_usuario] Chat_id atualizado com sucesso para Circuito: {circuito} numero: {numero}")
        except MySQLError as e:
            logging.error(f"[salvar_estado_usuario] Erro ao atualizar o chat_id: {e}")
        finally:
            connection.close()
            
def obter_circuito_usuario(user_id):
    connection = conectar_ao_banco()
    if connection:
        try:
            with connection.cursor(DictCursor) as cursor:
                query = "SELECT circuito, numero FROM notifica_missao_critica WHERE chat_id = %s and estado_fluxo = 'esperando_opcao'"
                cursor.execute(query, (user_id,))
                result = cursor.fetchone()  
                logging.info(f"[obter_circuito_usuario] Registro encontrado para chat_id: {user_id}")
                return result
        except MySQLError as e:
            logging.error(f"[obter_circuito_usuario] Erro ao buscar circuito no banco de dados: {e}")
        finally:
            connection.close()
    return None


def existe_cobranca_ativa_por_chat_id(chat_id):
    connection = conectar_ao_banco()
    if connection:
        try:
            with connection.cursor(DictCursor) as cursor:
                query = "SELECT 1 FROM notifica_missao_critica WHERE chat_id = %s AND estado_fluxo = 'esperando_opcao' LIMIT 1"
                cursor.execute(query, (chat_id,))
                result = cursor.fetchone()
                if result:
                    logging.info(f"[existe_cobranca_ativa_por_chat_id] Cobrança ativa encontrada para chat_id {chat_id}")
                    return True
        except MySQLError as e:
            logging.error(f"[existe_cobranca_ativa_por_chat_id] Erro ao buscar no banco de dados: {e}")
        finally:
            connection.close()
    return False