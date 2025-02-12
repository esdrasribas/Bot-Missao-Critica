import logging
from telebot import TeleBot
from conn.mysqlConnector import atualizar_escalamento_inicial, buscar_reparos, atualizar_data_proxima_cobranca, buscar_chat_ids_todos, buscar_atualizacao, buscar_chatid_responsavel, buscar_reparos_escalamento, atualizar_escalamento_inicial_notificacao
import os
from dotenv import load_dotenv
from libs.tools import obter_regional
from datetime import datetime, timedelta


load_dotenv()

# Inicializar o bot com TeleBot
bot = TeleBot(os.environ.get('TOKEN_TELEGRAM'))

# Função para enviar notificações de reparos críticos e escalá-los conforme necessário
def notifica_reparos_criticos():
    reparos_criticos = buscar_reparos()
    atualiza_notificacao = buscar_atualizacao()
    
    if reparos_criticos:
        logging.info(f"[notifica_reparos_criticos] Total de reparos críticos a serem processados: {len(reparos_criticos)}")
        usuarios = buscar_chat_ids_todos()
        
        for reparo in reparos_criticos:
            logging.info(f"[notifica_reparos_criticos] Processando reparo: {reparo}")
            atualizacao = ' '
            circuito = reparo['circuito']
            numero = reparo['numero']
            tempo_bd_aberto = reparo['tempo_bd_aberto']
            data_atual = datetime.now()
            nv_escalacao = reparo['nv_escalacao']
            uf = reparo['uf']
            escala_inicial = reparo['escala_inicial']
            data_proxima_cobranca = reparo['data_proxima_cobranca']
            ult_msg_crm = reparo['ult_msg_crm']
            data_abertura = reparo['data_abertura']
            data_abertura_formatada = data_abertura.strftime('%d/%m/%y %H:%M')
            ult_atualizacao = reparo['data_cobranca'].strftime('%d/%m/%y %H:%M') if reparo.get('data_cobranca') else "_Sem atualizações anteriores._"
            ultima_mensagem = reparo['ult_msg_crm'] if reparo.get('ult_msg_crm') else "_Sem mensagens anteriores._"
  
                
            logging.info(f"[notifica_reparos_criticos] Circuito: {circuito}, nv_escalacao: {nv_escalacao}, tempo_bd_aberto: {tempo_bd_aberto}")
            if data_proxima_cobranca:
                if data_proxima_cobranca > data_atual:
                    logging.info(f"[notifica_reparos_criticos] if data_proxima_cobranca > data_atual:{data_proxima_cobranca} ")
                    pass
                else:
                    data_proxima_cobranca = data_atual
                    logging.info(f"[notifica_reparos_criticos] data_proxima_cobranca = data_atual :{data_proxima_cobranca} ")
            else:
                data_proxima_cobranca = data_atual
                logging.info(f"[notifica_reparos_criticos] if data_proxima_cobranca: ELSE{data_proxima_cobranca} ")
            
            if isinstance(tempo_bd_aberto, (int, float)):
                if tempo_bd_aberto < 4:
                    escala_inicial = 1
                    nv_escalacao = 1
                    
                elif 4 <= tempo_bd_aberto < 6:
                    escala_inicial = 2
                    nv_escalacao = 2
                    
                elif tempo_bd_aberto >= 6:
                    escala_inicial = 3
                    nv_escalacao = 3
                    
                if escala_inicial is not None:
                    
                    logging.info(f"[notifica_reparos_criticos] Validando gestor.")
                    logging.info(f"[notifica_reparos_criticos] Data Atual: {data_atual}, Data_proxima_cobranca: {data_proxima_cobranca}")
                    atualizar_data_proxima_cobranca(circuito, data_proxima_cobranca, numero)
                    mensagem_inicial = gerar_mensagem_critica(escala_inicial, reparo, tempo_bd_aberto, data_abertura_formatada, ultima_mensagem, atualizacao, ult_atualizacao)
                    logging.info(f"[notifica_reparos_criticos] Mensagem gerada: {mensagem_inicial}")
                    logging.info(f"[notifica_reparos_criticos] Enviando notificação Critica.")

                    logging.info(f"[notifica_reparos_criticos] Atualizando escalonamento: {nv_escalacao} para circuito {circuito} numero: {numero}")
                    atualizar_escalamento_inicial(escala_inicial, nv_escalacao, 'SIM', circuito, numero)
                    logging.info(f"[notifica_reparos_criticos] Atualização concluída para {circuito}. Escalonamento atualizado para {nv_escalacao}")            

                    for chat_id, hierarquia, gestor, uf_usuario, regional_usuario in usuarios:
                        if chat_id is None or not isinstance(chat_id, int):
                            logging.warning(f"Usuário {hierarquia} com gestor {gestor} não tem um chat_id válido. Ignorando envio.")
                            continue  
                        
                        regional_responsavel = obter_regional(uf) 
                        logging.warning(f"[notifica_reparos_criticos] regional_responsavel: {regional_responsavel}, regional_usuario: {regional_usuario} uf: {uf}")

                        if gestor == 'b2b' and regional_usuario == regional_responsavel:
                            try:
                                logging.warning(f"Verificando gestor: {gestor}, hierarquia: {hierarquia}, chat_id: {chat_id}, escala_inicial: {escala_inicial}, uf: {uf}, regional_responsavel: {regional_responsavel}, regional_usuario: {regional_usuario}")
                                bot.send_message(chat_id=chat_id, text=mensagem_inicial, parse_mode="Markdown")
                                logging.info(f"[notifica_reparos_criticos] Notificação enviada para o gestor B2B {chat_id} da região {reparo['uf']}")
                            except Exception as e:
                                logging.error(f"[notifica_reparos_criticos] Erro ao enviar mensagem para o usuário {chat_id}: {e}")
                            continue 
                        
                        if escala_inicial in (1, 2) and hierarquia == 'Diretor' and gestor == 'b2b':
                            continue 

                        if escala_inicial >= 3 and hierarquia == 'Diretor' and gestor == 'b2b':
                            try:
                                logging.warning(f"Verificando gestor: {gestor}, hierarquia: {hierarquia}, chat_id: {chat_id}, escala_inicial: {escala_inicial}, uf: {uf}, regional_responsavel: {regional_responsavel}, regional_usuario: {regional_usuario}")
                                bot.send_message(chat_id=chat_id, text=mensagem_inicial, parse_mode="Markdown")
                                logging.info(f"[notifica_reparos_criticos] Notificação enviada para o Diretor B2B {chat_id} na escala 3 ou superior.")
                            except Exception as e:
                                logging.error(f"[notifica_reparos_criticos] Erro ao enviar mensagem para o Diretor B2B {chat_id}: {e}")
                            continue  

                        try:
                            if gestor != 'b2b':
                                logging.warning(f"Verificando gestor: {gestor}, hierarquia: {hierarquia}, chat_id: {chat_id}, escala_inicial: {escala_inicial}, uf: {uf}, regional_responsavel: {regional_responsavel}, regional_usuario: {regional_usuario}")
                                bot.send_message(chat_id=chat_id, text=mensagem_inicial, parse_mode="Markdown")
                                logging.info(f"[notifica_reparos_criticos] Notificação enviada para o usuário {chat_id} (não é gestor B2B)")
                        except Exception as e:
                            logging.error(f"[notifica_reparos_criticos] Erro ao enviar mensagem para o usuário {chat_id}: {e}")

    elif atualiza_notificacao:
        logging.info(f"[atualiza_notificacao] Total de reparos críticos a serem processados: {len(atualiza_notificacao)}")
        usuarios = buscar_chat_ids_todos()
        for notificacao in atualiza_notificacao:
            logging.info(f"atualiza_notificacao Processando notificacao: {notificacao}")
            atualizacao = 'ATUALIZAÇÃO'
            circuito = notificacao['circuito']
            numero = notificacao['numero']
            tempo_bd_aberto = notificacao['tempo_bd_aberto']
            uf = notificacao['uf']
            data_atual = datetime.now()
            nv_escalacao = notificacao['nv_escalacao']
            ult_atualizacao = notificacao['data_cobranca'].strftime('%d/%m/%y %H:%M') if notificacao.get('data_cobranca') else "_Sem atualizações anteriores._"
            escala_inicial = notificacao['escala_inicial']
            ultima_mensagem = notificacao['ult_msg_crm'] if notificacao.get('ult_msg_crm') else "_Sem mensagens anteriores._"
            data_proxima_cobranca = notificacao['data_proxima_cobranca']
            data_abertura = notificacao['data_abertura']
            data_abertura_formatada = data_abertura.strftime('%d/%m/%y %H:%M')
                
                
            logging.info(f"[atualiza_notificacao] Circuito: {circuito} numero:{numero}, nv_escalacao: {nv_escalacao}, tempo_bd_aberto: {tempo_bd_aberto}")
            if data_proxima_cobranca:
                if data_proxima_cobranca > data_atual:
                    pass
                else:
                    data_proxima_cobranca = data_atual
            else:
                data_proxima_cobranca = data_atual
            
            if isinstance(tempo_bd_aberto, (int, float)):
                if tempo_bd_aberto < 4:
                    escala_inicial = 1
                    nv_escalacao = 1
                    
                elif 4 <= tempo_bd_aberto < 6:
                    escala_inicial = 2
                    nv_escalacao = 2
                    
                elif tempo_bd_aberto >= 6:
                    escala_inicial = 3
                    nv_escalacao = 3
                    
                if escala_inicial is not None:
                    
                    logging.info(f"[atualiza_notificacao] Validando gestor.")
                    logging.info(f"[atualiza_notificacao] Data Atual: {data_atual}, Data_proxima_cobranca: {data_proxima_cobranca}")
                    atualizar_data_proxima_cobranca(circuito, data_proxima_cobranca, numero)
                    mensagem_inicial = gerar_mensagem_critica(escala_inicial, notificacao, tempo_bd_aberto, data_abertura_formatada, ultima_mensagem, atualizacao, ult_atualizacao)
                    logging.info(f"[atualiza_notificacao] Mensagem gerada: {mensagem_inicial}")
                    logging.info(f"[atualiza_notificacao] Enviando notificação Critica.")
                    
                    atualizar_escalamento_inicial(escala_inicial, nv_escalacao, 'SIM', circuito, numero)

                    for chat_id, hierarquia, gestor, uf_usuario, regional_usuario in usuarios:
                        if chat_id is None or not isinstance(chat_id, int):
                            logging.warning(f"Usuário {hierarquia} com gestor {gestor} não tem um chat_id válido. Ignorando envio.")
                            continue  
                        
                        regional_responsavel = obter_regional(uf)  
                        logging.warning(f"[notifica_reparos_criticos] Chatid: {chat_id}, regional_responsavel: {regional_responsavel}, regional_usuario: {regional_usuario} uf: {uf}")

                        if gestor == 'b2b' and regional_usuario == regional_responsavel:
                            try:
                                logging.warning(f"Verificando gestor: {gestor}, hierarquia: {hierarquia}, chat_id: {chat_id}, escala_inicial: {escala_inicial}, uf: {uf}, regional_responsavel: {regional_responsavel}, regional_usuario: {regional_usuario}")
                                bot.send_message(chat_id=chat_id, text=mensagem_inicial, parse_mode="Markdown")
                                logging.info(f"[notifica_reparos_criticos] Notificação enviada para o gestor B2B {chat_id}")
                            except Exception as e:
                                logging.error(f"[notifica_reparos_criticos] Erro ao enviar mensagem para o usuário {chat_id}: {e}")
                            continue  
                        
                        if escala_inicial in (1, 2) and hierarquia == 'Diretor' and gestor == 'b2b':
                            continue  

                        try:
                            if gestor != 'b2b':
                                logging.warning(f"Verificando gestor: {gestor}, hierarquia: {hierarquia}, chat_id: {chat_id}, escala_inicial: {escala_inicial}, uf: {uf}, regional_responsavel: {regional_responsavel}, regional_usuario: {regional_usuario}")
                                bot.send_message(chat_id=chat_id, text=mensagem_inicial, parse_mode="Markdown")
                                logging.info(f"[notifica_reparos_criticos] Notificação enviada para o usuário {chat_id} (não é gestor B2B)")
                        except Exception as e:
                            logging.error(f"[notifica_reparos_criticos] Erro ao enviar mensagem para o usuário {chat_id}: {e}")

def atualiza_notificacao_escala():
    atualizar_reparos_escala = buscar_reparos_escalamento()
    logging.info(f"[atualiza_notificacao_escala] Total de reparos críticos a serem processados: {len(atualizar_reparos_escala)}")
    if atualizar_reparos_escala:
        for reparo in atualizar_reparos_escala:
            escala_inicial = reparo['escala_inicial']
            tempo_bd_aberto = reparo['tempo_bd_aberto']
            nv_escalacao = reparo['nv_escalacao']
            circuito = reparo['circuito']
            numero = reparo['numero']

            if isinstance(tempo_bd_aberto, (int, float)):
                if tempo_bd_aberto < 4:
                    nv_escalacao = 1                
                elif 4 <= tempo_bd_aberto < 6:
                    nv_escalacao = 2                   
                elif tempo_bd_aberto >= 6:
                    nv_escalacao = 3

            logging.info(f"[atualiza_notificacao_escala] Validando circuito: {circuito} nv_escalacao: {nv_escalacao} escala_inicial: {escala_inicial}")
            if escala_inicial != nv_escalacao:
                escala_inicial = nv_escalacao
                logging.info(f"[atualiza_notificacao_escala] chamou atualizar_escalamento_inicial_notificacao")
                atualizar_escalamento_inicial_notificacao(nv_escalacao, escala_inicial, circuito, numero)
            else:
                logging.info(f"[atualiza_notificacao_escala] nv_escalacao: {nv_escalacao} escala_inicial: {escala_inicial}")

def gerar_mensagem_critica(escala, reparo, tempo_bd_aberto, data_abertura_formatada, ultima_mensagem, atualizacao, ult_atualizacao):

    if escala in(0,1):
        return (
            f"🟢 *ATENÇÃO: CLIENTE CRÍTICO! {atualizacao}*\n\n"
            f"Cliente: *{reparo['cliente']}*\nCircuito: *{reparo['circuito']}*\n"
            f"Chamado: *{reparo['numero']}*\nData Abertura: {data_abertura_formatada}\n"
            f"Perímetro: {reparo['perimetro']}\nAcesso: {reparo['tecn_acesso']}\n"
            f"Segmento: {reparo['segmento']}\nUF: {reparo['uf']}\nProduto: {reparo['produto']}\n"
            f"Velocidade: {reparo['velocidade']}\nReclamação: *{reparo['causa']}*\n"
        )
    elif escala == 2:
        return (
            f"⚠️ *ATENÇÃO: CLIENTE CRÍTICO! {atualizacao}*\n\n"
            f"Cliente: *{reparo['cliente']}*\nCircuito: *{reparo['circuito']}*\n"
            f"Chamado: *{reparo['numero']}*\nData Abertura: {reparo['data_abertura']}\n"
            f"Tempo BD aberto: *{tempo_bd_aberto} Horas*\nPosto Atual: {reparo['posto']}\n"
            f"Última atualização: {ult_atualizacao}\nStatus: {reparo['status']}\n"
            f"Já escalonado: *Sim*\nNível Escalonamento: Gestor B2B\n"
            f"Perímetro: {reparo['perimetro']}\nSegmento: {reparo['segmento']}\n"
            f"UF: {reparo['uf']}\nProduto: {reparo['produto']}\nVelocidade: {reparo['velocidade']}\n"
            f"Reclamação: *{reparo['causa']}*\n*Última mensagem:* _{ultima_mensagem}_\n"
        )
    elif escala == 3:
        return (
            f"🚨 *ATENÇÃO: CLIENTE CRÍTICO! {atualizacao}*\n\n"
            f"Cliente: *{reparo['cliente']}*\nCircuito: *{reparo['circuito']}*\n"
            f"Chamado: *{reparo['numero']}*\nData Abertura: {reparo['data_abertura']}\n"
            f"Tempo BD aberto: *{tempo_bd_aberto} horas*\nPosto Atual: {reparo['posto']}\n"
            f"Última atualização: {ult_atualizacao}\nStatus: {reparo['status']}\n"
            f"Já escalonado: *Sim*\nNível Escalonamento: Diretor B2B\n"
            f"Perímetro: {reparo['perimetro']}\nSegmento: {reparo['segmento']}\n"
            f"UF: {reparo['uf']}\nProduto: {reparo['produto']}\nVelocidade: {reparo['velocidade']}\n"
            f"Reclamação: {reparo['causa']}\n*Última mensagem:* _{ultima_mensagem}_\n"
        )
