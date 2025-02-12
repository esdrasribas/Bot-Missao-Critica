import logging
import pymysql
import os
from dotenv import load_dotenv
from pymysql.cursors import DictCursor
from datetime import datetime
import math

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


# Configurar o logger
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


# Lista de circuitos de missão crítica
circuitos_missao_critica = [
    'BLM5700849', 'BLM5701316', 'CBA0473398', 'BET5164323', 'BET5164324', 'LAD5014497', 'MRN5025086', 'PNV5025849',
    'TCS10540972', 'TCS10540972', 'PJS7213061', 'TCS7213062', 'CBO7212232', 'CBO7213092', 'BNU7213063', 'SBO5011962',
    'SPO5339781', 'AQZ7212558', 'IAGA7211734', 'PJS7206629', 'BHE7211801', 'CDU7205707', 'LAV7207515', 'TCS7207305',
    'CBO7207539', 'CBO7210966', 'RJO7208941', 'PJS5060500', 'TCS5032064', 'CBO5027669', 'CBO5027702', 'CBX5010112',
    'BNU5010413', 'SBO5011961', 'SPO5332845', 'SPO5335557', 'SPO5339779', 'SPO5339780', 'TCS10541084', 'TCS10540601',
    'TCS10540834', 'TCS10599520', 'TCS10540064', 'TCS10540547', 'TCS10540066', 'TCS10540230', 'TCS10540249', 'TCS10541082',
    'SPO0436834', 'SPO0438122', 'SPO0443356', 'SPO0447164', 'TCS10540064', 'TCS10540066', 'TCS10540230', 'TCS10540249',
    'TCS10540547', 'TCS10540601', 'TCS10540834', 'TCS10541082', 'TCS10541084', 'TCS10599520', 'SPO0445361', 'SPO0445362',
    'BLM5701098', 'PVO0446537', 'PVO0446579', 'CAH5044142', 'GNA0748127', 'SLS5373423', 'SLS5374196', 'FLA7211744',
    'RBO0420970', 'RBO0421767', 'TCS10540968', 'TCS10540968', 'PVO0446485', 'PVO0446561', 'PVO0446562', 'PVO0446563',
    'PVO0446885', 'SNO5010255', 'NMM5010125', 'SSZ5010138', 'RBO0420467', 'VTA7211908', 'VTA5270049', 'BRE7211908',
    'MPA5088504', 'BRE7211890', 'CBA0475337', 'CBA0475395', 'BSA0774245', 'MNS5401135', 'CPE0471454', 'CPE0473193',
    'RLIS5012906', 'TCS10541123', 'BRE7211362', 'RJO60004042', 'MNS7212200', 'MNS7212403', 'MPA7212201', 'SPO0439937',
    'CBA0472612', 'CBA0476835', 'PVO0443458', 'PVO0444915', 'PVO0445952', 'PVO0446525', 'PVO0446526', 'PVO0446527',
    'PVO0446528', 'PVO0446529', 'PVO0446577', 'PVO0446578', 'CBA0471496', 'SDR6438088', 'IPJ5012957', 'RJO60016481',
    'RJO60016482', 'NTL5274675', 'RJO60019513', 'CTA0839537', 'PAE0860565', 'PAE0498378', 'PAE0607361'
]

# Função para inserir ou atualizar os dados na tabela notifica_missao_critica
def inserir_ou_atualizar_notificacao(reparo):
    connection = conectar_ao_banco()
    
    if connection:
        try:
            with connection.cursor() as cursor:
                # Calcula o tempo que o BD está aberto
                data_abertura = reparo['data_abertura']  # Supondo que este campo seja datetime
                tempo_bd_aberto = (datetime.now() - data_abertura).total_seconds() / 3600  # Em horas
                tempo_bd_aberto = math.floor(tempo_bd_aberto)
                circuito = reparo['circuito']
                numero = reparo['numero']
                data_hora_atual = datetime.now()
                data_etl = data_hora_atual.strftime('%Y-%m-%d %H:%M:%S')

                # Verificar o status atual na tabela notifica_missao_critica
                query_verificar_status_notifica = """
                    SELECT status FROM notifica_missao_critica
                    WHERE circuito = %s AND numero = %s
                """
                cursor.execute(query_verificar_status_notifica, (circuito, numero))
                resultado_status_notifica = cursor.fetchone()

                # Verificar o status atual na tabela acionamento_tecnico.  Regra se estiver na tabela de notifica_missao_critica não inserir e nem atualizar na tabela notifica_missao_critica
                query_verificar_status_acionamento = """
                    SELECT status FROM acionamento_tecnico
                    WHERE circuito = %s AND numero = %s
                """
                cursor.execute(query_verificar_status_acionamento, (circuito, numero))
                resultado_status_acionamento = cursor.fetchone()

                # Verificar o status atual na tabela notifica_missao_critica_hist. Regra se estiver na tabela de historico não inserir na tabela notifica_missao_critica
                query_verificar_historico = """
                    SELECT status FROM notifica_missao_critica_hist
                    WHERE circuito = %s AND numero = %s
                """
                cursor.execute(query_verificar_historico, (circuito,numero))
                resultado_status_historico = cursor.fetchone()
                
                # Se o status for "Fechado" em ambas as tabelas, não atualizar o reparo
                # Se estiver na tabela de historico não inserir na tabela notifica_missao_critica
                if (resultado_status_notifica and resultado_status_notifica[0] == "Fechado") and \
                (resultado_status_acionamento and resultado_status_acionamento[0] == "Fechado") or \
                (resultado_status_historico and resultado_status_historico[0] == "Fechado"):
                    logging.info(f"O reparo {numero} no circuito {circuito} já está fechado em ambas as tabelas e não será atualizado.")
                    return  # Pular para o próximo reparo

                query_ajusta_base_stc = """
                    SELECT data_entrada_posto, ult_msg
                    FROM ajuste_base_stc
                    WHERE circuito = %s AND caso = %s
                """
                cursor.execute(query_ajusta_base_stc, (circuito, numero))
                resultado_ajusta_base = cursor.fetchone()


                if resultado_ajusta_base:
                    data_entrada_posto = resultado_ajusta_base[0]
                    ult_msg = resultado_ajusta_base[1]
                else:
                    data_entrada_posto = None
                    ult_msg = None

                insert_query = """
                    INSERT INTO notifica_missao_critica (numero, num_ba, status_ba, estacao_ba, caso_stc, causa, posto, status, circuito, segmento, cliente, velocidade, tecn_acesso, perimetro, cidade, uf, psr, data_abertura, produto, tempo_bd_aberto, data_entrada_posto, data_atualizacao, ult_msg, sistema, data_etl)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s)
                    ON DUPLICATE KEY UPDATE
                        num_ba = VALUES(num_ba),
                        status_ba = VALUES(status_ba),
                        estacao_ba = VALUES(estacao_ba),
                        caso_stc = VALUES(caso_stc),
                        causa = VALUES(causa),
                        posto = VALUES(posto),
                        status = VALUES(status),
                        segmento = VALUES(segmento),
                        cliente = VALUES(cliente),
                        velocidade = VALUES(velocidade),
                        tecn_acesso = VALUES(tecn_acesso),
                        perimetro = VALUES(perimetro),
                        cidade = VALUES(cidade),
                        uf = VALUES(uf),
                        psr = VALUES(psr),
                        data_abertura = VALUES(data_abertura),
                        tempo_bd_aberto = VALUES(tempo_bd_aberto),
                        data_entrada_posto = VALUES(data_entrada_posto),
                        data_atualizacao = VALUES(data_atualizacao),
                        ult_msg = VALUES(ult_msg),
                        sistema = VALUES(sistema),
                        data_etl = VALUES(data_etl);          
                """

                cursor.execute(insert_query, (
                    reparo['numero'],        # Chave primária
                    reparo['num_ba'],
                    reparo['status_ba'],
                    reparo['estacao_ba'],
                    reparo['caso_stc'],
                    reparo['causa'],
                    reparo['posto'],
                    reparo['status'],
                    reparo['circuito'],
                    reparo['segmento'],
                    reparo['cliente'],
                    reparo['velocidade'],
                    reparo['tecn_acesso'],
                    reparo['perimetro'],
                    reparo['cidade'],
                    reparo['uf'],
                    reparo['psr'],
                    reparo['data_abertura'],
                    reparo['produto'],
                    tempo_bd_aberto,
                    data_entrada_posto,
                    reparo['data_atualizacao'],
                    ult_msg,
                    reparo['sistema'],
                    data_etl
                ))
                connection.commit()  # Confirmando a inserção ou atualização no banco
                logging.info(f"Dados do circuito {reparo['circuito']} inseridos/atualizados na tabela notifica_missao_critica.")
        except pymysql.MySQLError as e:
            logging.error(f"Erro ao inserir/atualizar notificação: {e}")
        finally:
            connection.close()

def monitorar_reparos():
    connection = conectar_ao_banco()
    
    if connection:
        try:
            with connection.cursor(DictCursor) as cursor:  # Usando DictCursor
                # Query para virada para o dia 2024-10-10 00:00:00
                query = f"SELECT * FROM acionamento_tecnico WHERE circuito IN ({', '.join(['%s'] * len(circuitos_missao_critica))}) AND data_abertura >= '2024-10-29 00:00:00';"
                # query = f"SELECT * FROM acionamento_tecnico WHERE circuito IN ({', '.join(['%s']*len(circuitos_missao_critica))}) and numero in ('') and status not in ('Fechado','Blacklist')"
                cursor.execute(query, tuple(circuitos_missao_critica))
                resultado = cursor.fetchall()

                if resultado:
                    for reparo in resultado:
                        logging.info(f"Reparo Missão Crítica encontrado para o circuito {reparo['circuito']}: {reparo}")
                        
                        # Inserindo ou atualizando os dados na tabela notifica_missao_critica
                        inserir_ou_atualizar_notificacao(reparo)
                else:
                    logging.info("Nenhum Reparo Missão Crítica encontrado para os circuitos de missão crítica")

        except pymysql.MySQLError as e:
            logging.error(f"Erro ao acessar o banco de dados: {e}")
        finally:
            connection.close()

def atualizar_circuitos_fechados():
    connection = conectar_ao_banco()
    
    if connection:
        try:
            with connection.cursor() as cursor:
                # Atualiza o status para 'Fechado' na tabela notifica_missao_critica para registros que não existem mais na tabela acionamento_tecnico
                query_circuitos_fechados = """
                    UPDATE notifica_missao_critica AS nmc
                    LEFT JOIN acionamento_tecnico AS at ON nmc.circuito = at.circuito AND nmc.numero = at.numero
                    SET nmc.status = 'Fechado'
                    WHERE at.circuito IS NULL AND nmc.status != 'Fechado';
                """
                cursor.execute(query_circuitos_fechados)
                connection.commit()
                logging.info("[atualizar_circuitos_fechados] Status dos circuitos fechados atualizado na tabela notifica_missao_critica.")
        except pymysql.MySQLError as e:
            logging.error(f"[atualizar_circuitos_fechados] Erro ao atualizar status dos circuitos fechados: {e}")
        finally:
            connection.close()

# Chame a função atualizar_circuitos_fechados logo após monitorar_reparos
monitorar_reparos()
atualizar_circuitos_fechados()

