import telebot
import os
import schedule
import time
import threading
import requests
from requests.exceptions import ReadTimeout
import logging
from libs.enviaNotificacao import notifica_reparos_criticos, atualiza_notificacao_escala
import re
from libs.tools import valid_mask, obter_regional
from datetime import datetime, timedelta
from requests.exceptions import ReadTimeout
from cron.envia_historico import enviar_status_reparo
from conn.mysqlConnector import buscar_cobranca, fechados_n_notificados, atualizar_data_proxima_cobranca, atualizar_escalamento_cobranca, atualizar_ult_msg_no_bd, atualizar_falha_ou_pendencia, buscar_fluxo_no_bd, salvar_fluxo_no_bd ,atualizar_previsao_conclusao, atualizar_chatid, verificar_matricula, atualizar_circuito_chatid, salvar_estado_usuario, buscar_gestor_b2b_por_regional, buscar_cobranca_fechados, atualizar_notificacao, limpar_chave_busca_info, atualizar_data_atualizacao, atualizar_valid_mask, buscar_chat_ids_todos, obter_estado_usuario, obter_circuito_usuario, existe_cobranca_ativa_por_chat_id

# Configuração do logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

bot_token = os.getenv('TOKEN_TELEGRAM')
bot = telebot.TeleBot(bot_token)
circuitos_usuario = {}
estado_resposta_usuario = {} # estado é por chat_id
fila_circuitos = []
respostas_gestor = {}


#################################################### Bot Handlers config #####################################################
# Handlers de mensagens
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    bot.reply_to(message, "Bem-vindo ao *MissãoCrítica*! Aguarde as notificações sobre o status dos reparos.", parse_mode="Markdown")
    logging.info(f"Usuário {chat_id} iniciou o bot.")

@bot.message_handler(commands=['historico'])
def send_historico(message):
    chat_id = message.chat.id
    enviar_status_reparo(chat_id)  # Chama a função, que envia a mensagem diretamente
    logging.info(f"Usuário {chat_id} iniciou o bot.")

@bot.message_handler(commands=['test'])
def test_notification(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Esta é uma mensagem de teste.")
    logging.info(f"Mensagem de teste enviada para {chat_id}.")

@bot.message_handler(commands=['cadastro'])
def handle_cadastro(message):
    nome = message.from_user.first_name
    response_text = f"Olá {nome},\nbem-vindo ao *MissãoCrítica*!\nPode me informar seu login V.tal?"
    bot.reply_to(message, response_text, parse_mode="Markdown")
    bot.register_next_step_handler(message, processar_matricula)
#################################################### Bot Handlers config #####################################################


def processar_reparos():
    """
    Processa os reparos críticos e envia notificações.
    """
    global estado_resposta_usuario, fila_circuitos

    reparos_criticos = buscar_cobranca()
    reparos_fechados = buscar_cobranca_fechados()
    reparos_fechados_notificados = fechados_n_notificados()
    logging.info(f"[processar_reparos] Reparos críticos encontrados: {reparos_criticos}")
    try:

        if reparos_criticos:
            for reparo in reparos_criticos:
                logging.info(f"reparo['status']: {reparo['status']}, reparo['escalonado']: {reparo['escalonado']}")
                uf = reparo['uf']
                regional = obter_regional(uf)
                gestor_b2b = buscar_gestor_b2b_por_regional(regional)  # Buscar gestores B2B pela regional
                proxima_cobranca = reparo['data_proxima_cobranca']
                circuito = reparo['circuito']
                numero = reparo['numero']
                nv_escalacao = reparo['nv_escalacao']
                data_atual = datetime.now()

                if gestor_b2b is None:
                    logging.warning(f"[processar_reparos] Nenhum gestor B2B encontrado para a UF: {uf}")
                    continue

                chat_id = gestor_b2b['chatid_cadastro']
                if not chat_id:
                    logging.warning(f"[processar_reparos] Usuário ainda não possui chat_id para UF:{uf} e regional: {regional}")
                    continue

                nome = gestor_b2b['nome']
                logging.info(f"[processar_reparos] chat_id encontrado: {chat_id} para uf: {uf} nome: {nome}, circuito: {circuito}, gestor_b2b: {gestor_b2b}")

                # Evitar que reparos "Fechados" ou "Blacklist" sejam processados
                if reparo['status'] not in ('Fechado', 'Blacklist') and reparo['escalonado'] == 'COBRANCA':
                    tempo_bd_aberto = reparo['tempo_bd_aberto']

                    # Determinar o novo nível de escalonamento com base no tempo aberto
                    if tempo_bd_aberto < 4:
                        nv_escalacao = 1
                    elif 4 <= tempo_bd_aberto < 6:
                        nv_escalacao = 2
                    elif tempo_bd_aberto >= 6:
                        nv_escalacao = 3

                    # estado_circuito = estado_resposta_usuario.get(f"{chat_id}_{circuito}_{numero}")
                    estado_circuito = obter_estado_usuario(chat_id, circuito, numero)
                    logging.info(f"[processar_reparos] estado_circuito {estado_circuito}, chat_id {chat_id}, circuito {circuito}, numero {numero}")
                    # Verifica se está aguardando a previsão de conclusão ou outro estado de espera
                    if estado_circuito and estado_circuito['estado_fluxo'] in ['aguardando_previsao']:
                        logging.info(f"[processar_reparos] Circuito {circuito} já está aguardando resposta. Não será processada nova cobrança.")
                        continue

                    # Verifica se o estado é "cobrança_encerrada" e se a próxima cobrança é válida
                    if estado_circuito and estado_circuito['estado_fluxo'] == "cobrança_encerrada" and proxima_cobranca and proxima_cobranca <= data_atual:
                        # Se a próxima cobrança foi atingida, reiniciar o processo de cobrança
                        # estado_resposta_usuario[f"{chat_id}_{circuito}_{numero}"] = 'esperando_opcao'
                        existe_cobranca_ativa = existe_cobranca_ativa_por_chat_id(chat_id)
                        logging.info(f"[processar_reparos] Estados associados ao chat_id {chat_id}: {existe_cobranca_ativa}")

                        # Processa o circuito atual apenas se não houver cobrança ativa
                        if not existe_cobranca_ativa:
                            salvar_estado_usuario(chat_id, 'esperando_opcao', circuito, numero)
                            logging.info(f"[processar_reparos] Reiniciando cobrança para o circuito {circuito}.")
                            # Atualiza a data da próxima cobrança
                            if nv_escalacao == 2:
                                proxima_cobranca = data_atual + timedelta(minutes=60)
                            elif nv_escalacao == 3:
                                proxima_cobranca = data_atual + timedelta(minutes=30)

                            atualizar_data_proxima_cobranca(circuito, proxima_cobranca, numero)
                            enviar_opcoes_escalacao(chat_id, circuito, numero)
                            break

                    # Verifica se há cobrança pendente para esse circuito específico
                    if estado_circuito and estado_circuito['estado_fluxo'] == 'esperando_opcao':
                        # Recobrar apenas se a data_proxima_cobranca foi atingida
                        if proxima_cobranca is None or proxima_cobranca <= data_atual:
                            try:
                                logging.info(f"[processar_reparos] Enviando recobrança para o circuito {circuito}.")
                                # Envia a recobrança
                                enviar_opcoes_escalacao(chat_id, circuito, numero)
                                logging.info(f"[processar_reparos] Recobrança enviada para o circuito {circuito}.")

                                # Atualiza a data da próxima cobrança
                                if nv_escalacao == 2:
                                    proxima_cobranca = data_atual + timedelta(minutes=60)
                                elif nv_escalacao == 3:
                                    proxima_cobranca = data_atual + timedelta(minutes=30)

                                atualizar_data_proxima_cobranca(circuito, proxima_cobranca, numero)
                                logging.info(f"[processar_reparos] Próxima cobrança agendada para {proxima_cobranca} para o circuito {circuito}.")
                            except telebot.apihelper.ApiTelegramException as e:
                                logging.error(f"Erro ao enviar recobrança para {chat_id}: {e}")
                        else:
                            logging.info(f"[processar_reparos] Próxima cobrança ainda não atingida para o circuito {circuito}. Data atual: {data_atual}, Próxima cobrança: {proxima_cobranca}")
                        continue  # Pula para o próximo reparo, já que este está em recobrança

                    # Adicionar o circuito associado ao chat_id na fila, se ainda não estiver lá
                    if (circuito, chat_id, numero) not in fila_circuitos:
                        fila_circuitos.append((circuito, chat_id, numero))
                        logging.info(f"[processar_reparos] Circuito {circuito} associado ao chat_id {chat_id} adicionado à fila.")

                    logging.info(f"[processar_reparos] fila_circuitos após adição: {fila_circuitos}")
                    
                # Processa a fila de circuitos, garantindo que não haja múltiplas cobranças simultâneas no mesmo circuito
                if len(fila_circuitos) > 0:
                    circuito_atual, chat_id, numero = fila_circuitos.pop(0)
                    logging.info(f"[processar_reparos] Iniciando processamento para o circuito: {circuito_atual}, chat_id: {chat_id}, numero: {numero}")
                    # Obtém todos os estados de cobrança associados ao chat_id, independentemente do circuito e número
                    existe_cobranca_ativa = existe_cobranca_ativa_por_chat_id(chat_id)
                    logging.info(f"[processar_reparos] Estados associados ao chat_id {chat_id}: {existe_cobranca_ativa}")

                    # Processa o circuito atual apenas se não houver cobrança ativa
                    if not existe_cobranca_ativa:
                        try:
                            # Obtendo estado do circuito atual
                            estado_circuito_atual = obter_estado_usuario(chat_id, circuito_atual, numero)
                            logging.info(f"[processar_reparos] Estado atual do circuito {circuito_atual}: {estado_circuito_atual}")
                            logging.info(f"[processar_reparos] estado_circuito_atual {estado_circuito_atual}")

                            # Processa o circuito atual apenas se não estiver em cobrança
                            if estado_circuito_atual is None or estado_circuito_atual['estado_fluxo'] != 'esperando_opcao':
                                # Marca o circuito atual como em cobrança
                                salvar_estado_usuario(chat_id, 'esperando_opcao', circuito_atual, numero)
                                logging.info(f"[processar_reparos] Estado atualizado para 'esperando_opcao' para o circuito {circuito_atual}, chat_id {chat_id}")

                                # Definindo a próxima data de cobrança de acordo com o nível de escalonamento
                                if nv_escalacao == 2:
                                    proxima_cobranca = data_atual + timedelta(minutes=60)
                                elif nv_escalacao == 3:
                                    proxima_cobranca = data_atual + timedelta(minutes=30)

                                atualizar_data_proxima_cobranca(circuito_atual, proxima_cobranca, numero)
                                logging.info(f"[processar_reparos] Próxima cobrança agendada para {proxima_cobranca} para o circuito {circuito_atual}, número {numero}")

                                # Atualiza o circuito associado ao chat_id e envia a cobrança
                                atualizar_circuito_chatid(chat_id, circuito_atual, numero)
                                enviar_opcoes_escalacao(chat_id, circuito_atual, numero)
                                logging.info(f"[processar_reparos] Cobrança enviada para o circuito {circuito_atual}, chat_id {chat_id}, número {numero}")

                        except telebot.apihelper.ApiTelegramException as e:
                            logging.error(f"[processar_reparos] Erro ao enviar mensagem para {chat_id}: {e}")
                    else:
                        # Casos onde já existe uma cobrança ativa ou o circuito atual já está em cobrança
                        if existe_cobranca_ativa:
                            logging.info(f"[processar_reparos] Cobrança já ativa para o chat_id {chat_id}. Não enviando nova cobrança para o circuito {circuito_atual}.")

                        estado_circuito_atual = obter_estado_usuario(chat_id, circuito_atual, numero)    
                        if estado_circuito_atual and estado_circuito_atual['estado_fluxo'] == 'esperando_opcao':
                            
                            logging.info(f"[processar_reparos] Circuito {circuito_atual} já está em cobrança (estado 'esperando_opcao'). Verificando respostas.")

                            # Reset do estado do circuito após resposta
                            salvar_estado_usuario(chat_id, None, circuito_atual, numero)
                            logging.info(f"[processar_reparos] Estado resetado para o circuito {circuito_atual}, chat_id {chat_id}")

        if reparos_fechados:
            for reparo in reparos_fechados:
                escalonado = reparo['escalonado']
                data_atualizacao = reparo['data_atualizacao']
                posto = reparo['posto']

                if reparo['status'] in ('Fechado', 'Blacklist') and escalonado == 'COBRANCA':
                    if data_atualizacao > datetime.now() - timedelta(minutes=25):
                        logging.info(f"[processar_reparos_fechados] Aguardando 25 minutos para encerrar a cobrança do posto '{posto}'.")
                        continue

                    uf = reparo['uf']
                    gestor_b2b = buscar_gestor_b2b_por_regional(regional)
                    circuito = reparo['circuito']
                    numero = reparo['numero']
                    usuarios = buscar_chat_ids_todos()
                    mensagem = f"Olá, o reparo do circuito *{circuito}* está encerrado. As cobranças e as notificações estão sendo encerradas para esse circuito."
                    escala_inicial = reparo['escala_inicial']

                    for chat_id, hierarquia, gestor, uf_usuario, regional_usuario in usuarios:
                        if chat_id is None or not isinstance(chat_id, int):
                            logging.warning(f"[processar_reparos_fechados] Usuário {hierarquia} com gestor {gestor} não tem um chat_id válido. Ignorando envio.")
                            continue  

                        regional_responsavel = obter_regional(uf) 
                        logging.warning(f"[processar_reparos_fechados] regional_responsavel: {regional_responsavel}, regional_usuario: {regional_usuario} uf: {uf}")

                        # Verifica se o usuário é o gestor B2B da regional
                        if gestor == 'b2b' and regional_usuario == regional_responsavel:
                            try:
                                logging.warning(f"[processar_reparos_fechados] Enviando notificação para gestor B2B {chat_id}, região: {uf}")
                                bot.send_message(chat_id=chat_id, text=mensagem, parse_mode="Markdown")
                                logging.info(f"[processar_reparos_fechados] Notificação enviada para o gestor B2B {chat_id} da região {uf}")
                            except Exception as e:
                                logging.error(f"[processar_reparos_fechados] Erro ao enviar mensagem para o usuário {chat_id}: {e}")
                            continue 

                        # if escala_inicial in (1, 2) and hierarquia == 'Diretor' and gestor == 'b2b':
                        #     continue 

                        if escala_inicial >= 3 and hierarquia == 'Diretor' and gestor == 'b2b':
                            try:
                                logging.warning(f"[processar_reparos_fechados] Enviando notificação para Diretor B2B {chat_id} (escala 3 ou superior), região: {uf}")
                                bot.send_message(chat_id=chat_id, text=mensagem, parse_mode="Markdown")
                                logging.info(f"[processar_reparos_fechados] Notificação enviada para o Diretor B2B {chat_id} na escala 3 ou superior.")
                            except Exception as e:
                                logging.error(f"[processar_reparos_fechados] Erro ao enviar mensagem para o Diretor B2B {chat_id}: {e}")
                            continue  

                        # Envio para usuários que não são gestores B2B
                        if gestor != 'b2b':
                            try:
                                logging.warning(f"[processar_reparos_fechados] Enviando notificação para usuário {chat_id} (não gestor B2B), região: {uf}")
                                bot.send_message(chat_id=chat_id, text=mensagem, parse_mode="Markdown")
                                logging.info(f"[processar_reparos_fechados] Notificação enviada para o usuário {chat_id} (não gestor B2B)")
                            except Exception as e:
                                logging.error(f"[processar_reparos_fechados] Erro ao enviar mensagem para o usuário {chat_id}: {e}")

                    # Atualizar status do reparo e encerrar cobrança
                    escalonado = 'FIM_COB'
                    atualizar_escalamento_cobranca(escalonado, circuito, numero)

                    # Remover o circuito da fila e limpar o estado de resposta
                    fila_circuitos = [item for item in fila_circuitos if item[0] != circuito]

                    # Limpar o estado de resposta no banco de dados
                    salvar_estado_usuario(chat_id, None, circuito, numero)
                    logging.info(f"[processar_reparos_fechados] Circuito {circuito} removido da fila e estado de resposta limpo no banco de dados.")
                    logging.info(f"[processar_reparos_fechados] A cobrança está sendo encerrada para o circuito {circuito}.")

        if reparos_fechados_notificados:
            for reparo in reparos_fechados_notificados:
                posto = reparo['posto']
                data_atualizacao = reparo['data_atualizacao']

                if reparo['status'] in ('Fechado', 'Blacklist') and reparo['escalonado'] == '-' and reparo['notificacao_inicial'] != 'SIM' :
                    if data_atualizacao > datetime.now() - timedelta(minutes=25):
                        logging.info(f"[processar_reparos_fechados] Aguardando 25 minutos para encerrar a cobrança do posto '{posto}'.")
                        continue
                    logging.info(f"[processar_reparos_fechados] Entrou aqui 4")
                    circuito = reparo['circuito']
                    numero = reparo['numero']
                    escalonado = 'FIM_COB'
                    atualizar_escalamento_cobranca(escalonado, circuito, numero)
                    logging.info(f"[processar_reparos_fechados] O reparo do circuito:{circuito} numero: {numero} foi encerrado sem cobrança e notificações ativas.")

        else:
            logging.info("[processar_reparos_fechados] Nenhum reparo crítico encontrado.")

    except Exception as e:
        logging.error(f"[enviar_opcoes_escalacao] Erro crítico: {e}")
        os._exit(1)  # Encerra o processo imediatamente

# Resposta inicial para a notificação do status do circuito
def enviar_opcoes_escalacao(chat_id, circuito, numero):
    try:
        salvar_estado_usuario(chat_id, 'esperando_opcao', circuito, numero)

        logging.info(f"[enviar_opcoes_escalacao] Opções de escalacao enviadas para chat_id: {chat_id}, circuito: {circuito} numero: {numero}")

        # Armazena o circuito associado ao chat_id

        msg = (
            f"Olá, me chamo *MissãoCrítica*, encontrei o reparo do circuito *{circuito}* na sua região."
            " Por favor, escolha uma opção para atualizar o reparo:\n"
            " 🔧*Atualizar:*\n"
            "1 - Causa da Falha e Tempo de Conclusão\n"
            "2 - Reparo em Pendência"
        )
        bot.send_message(chat_id, msg, parse_mode="Markdown")

    except Exception as e:
        if "403" in str(e) and "bot was blocked by the user" in str(e):
            logging.warning(f"[enviar_opcoes_escalacao] Bot bloqueado pelo usuário com chat_id: {chat_id}")
            
        else:
            # Opcional: Marcar o usuário como bloqueado na base de dados ou estado do bot
            logging.error(f"[enviar_opcoes_escalacao] Erro crítico: {e}")
            os._exit(1)  # Encerra o processo imediatamente

# Resposta ao usuário após a escolha de uma opção
@bot.message_handler(func=lambda message: True)
def tratar_resposta_escolha(message):
    try:
        user_id = message.chat.id
        circuito_info = obter_circuito_usuario(user_id)
        if circuito_info is None:
            logging.info(f"[tratar_resposta_escolha] Nenhum circuito associado ao usuário {user_id}")
            bot.reply_to(message, "Favor aguardar as próximas notificações e atualizações dos reparos.")
            return
        circuito = circuito_info['circuito']
        numero = circuito_info['numero']
        if circuito_info is None or numero is None:
            logging.info(f"[tratar_resposta_escolha] Nenhum circuito associado ao usuário {user_id}")
            bot.reply_to(message, "Favor aguardar as próximas notificações e atualizações dos reparos.")
            return
        estado_fluxo = obter_estado_usuario(user_id, circuito, numero)
        logging.info(f"[tratar_resposta_escolha] estado_fluxo: {estado_fluxo} estado_fluxo['estado_fluxo']: {estado_fluxo['estado_fluxo']}")
        if estado_fluxo and estado_fluxo['estado_fluxo'] != 'esperando_opcao':
            # Se não há fluxo ativo, responde com uma mensagem padrão
            bot.reply_to(message, "Favor aguardar as próximas notificações e atualizações dos reparos.")
            logging.info(f"[tratar_resposta_escolha] Resposta recebida sem fluxo ativo para o usuário {user_id}")
            return

        escolha = message.text.strip()
        logging.info(f"[tratar_resposta_escolha] Usuário {message.from_user.username} escolheu: {escolha}")  
        logging.info(f"[tratar_resposta_escolha] circuito: {circuito} numero: {numero}")

        if circuito:
            # Atualiza o fluxo do usuário com a nova escolha
            atualizar_fluxo_usuario(circuito, escolha, numero)
            # Salva a última mensagem enviada pelo usuário
            atualizar_ult_msg_no_bd(escolha, circuito, numero)

            if escolha == '1':
                salvar_estado_usuario(user_id, 'esperando_opcao', circuito, numero)
                bot.reply_to(message, f"Bom trabalho! Qual a falha encontrada?\n*Falha Equipamento:*\n1- Cliente \n2- Vtal \n*Rompimento de Fibra:*\n3- Backbone \n4- Acesso \n*Outros:*\n5- Transmissão \n6- Cabo de acesso", parse_mode="Markdown")
                bot.register_next_step_handler(message, tratar_causa_falha, circuito, numero)
                logging.info(f"[tratar_resposta_escolha] Iniciando fluxo de falha para circuito {circuito} numero: {numero}")
            elif escolha == '2':
                salvar_estado_usuario(user_id, 'esperando_opcao', circuito, numero)
                bot.reply_to(message, "*Qual o tipo de pendência?*\n1- Pendência Cliente\n2- Pendência Área de Risco", parse_mode="Markdown")
                bot.register_next_step_handler(message, tratar_pendencia, circuito, numero)
                logging.info(f"[tratar_resposta_escolha] Iniciando fluxo de pendência para circuito {circuito} numero: {numero}")
            else:
                bot.reply_to(message, "Opção inválida. Escolha novamente.")
                logging.warning(f"[tratar_resposta_escolha] Opção inválida escolhida pelo usuário {message.from_user.username}: {escolha}")
        else:
            logging.error(f"[tratar_resposta_escolha] Nenhum circuito associado ao usuário {user_id}")

    except Exception as e:
        logging.error(f"[tratar_resposta_escolha] Erro crítico: {e}")
        os._exit(1)  # Encerra o processo imediatamente


def tratar_causa_falha(message, circuito, numero):
    try:
            
        user_id = message.chat.id
        resposta = message.text.strip()
        falha_ou_pendencia = None

        logging.info(f"[tratar_causa_falha] Resposta do usuário {message.from_user.username} para circuito {circuito} numero {numero}: {resposta}")

        # Validação da causa da falha
        if resposta == '1':
            falha_ou_pendencia = "Falha Equipamento - Cliente"
        elif resposta == '2':
            falha_ou_pendencia = "Falha Equipamento - Vtal"
        elif resposta == '3':
            falha_ou_pendencia = "Rompimento de Fibra - Backbone"
        elif resposta == '4':
            falha_ou_pendencia = "Rompimento de Fibra - Acesso"
        elif resposta == '5':
            falha_ou_pendencia = "Outros - Transmissão"
        elif resposta == '6':
            falha_ou_pendencia = "Outros - Cabo de acesso"
        else:
            bot.reply_to(message, "Opção inválida. Escolha novamente.")
            logging.warning(f"[tratar_causa_falha] Resposta inválida do usuário {message.from_user.username}: {resposta}")
            return

        bot.reply_to(message, f"{falha_ou_pendencia} registrado com sucesso!")
        logging.info(f"{falha_ou_pendencia} registrado pelo usuário {message.from_user.username}.")
        try:
            # Atualiza o fluxo do usuário com a nova escolha
            atualizar_fluxo_usuario(circuito, resposta, numero)
            # Salva a última mensagem enviada pelo usuário
            atualizar_ult_msg_no_bd(resposta, circuito, numero)
            
            atualizar_falha_ou_pendencia(falha_ou_pendencia, circuito, numero)
            logging.info(f"[tratar_causa_falha] Falha registrada com sucesso: {falha_ou_pendencia} para o circuito {circuito} numero: {numero}")
        except Exception as e:
            bot.send_message(message.chat.id, "Ocorreu um erro ao registrar a falha. Por favor, tente novamente.")
            logging.error(f"[tratar_causa_falha] Erro ao registrar falha {falha_ou_pendencia} para o circuito {circuito} numero {numero}: {e}")

        salvar_estado_usuario(user_id, 'esperando_opcao', circuito, numero)
        bot.send_message(message.chat.id, "*Qual a previsão de conclusão?* Favor informar no formato: *DD/MM/AAAA HH:MM*", parse_mode="Markdown")
        bot.register_next_step_handler(message, tratar_previsao, circuito, numero, falha_ou_pendencia)

    except Exception as e:
        logging.error(f"[tratar_causa_falha] Erro crítico: {e}")
        os._exit(1)  # Encerra o processo imediatamente

def tratar_pendencia(message, circuito, numero):
    try:
        user_id = message.chat.id
        resposta = message.text.strip()
        falha_ou_pendencia = None

        # Validação da pendência
        if resposta == '1':
            falha_ou_pendencia = "Pendência Cliente"
        elif resposta == '2':
            falha_ou_pendencia = "Pendência Área de Risco"
        else:
            bot.reply_to(message, "Opção inválida. Escolha novamente.")
            return

        bot.reply_to(message, f"{falha_ou_pendencia} registrado com sucesso!")
        logging.info(f"{falha_ou_pendencia} registrado pelo usuário {message.from_user.username}.")
            # Atualizar o estado para "aguardando_previsao"
        salvar_estado_usuario(user_id, 'esperando_opcao', circuito, numero)
        try:
            atualizar_falha_ou_pendencia(falha_ou_pendencia, circuito, numero)
            logging.info(f"Pendência registrada: {falha_ou_pendencia} pelo usuário {message.from_user.username}.")
        except Exception as e:
            bot.send_message(message.chat.id, "Ocorreu um erro ao registrar a pendência. Por favor, tente novamente.")
            logging.error(f"Erro ao registrar pendência: {e}")


        bot.send_message(message.chat.id, "*Qual a previsão de conclusão?* Favor informar no formato: *DD/MM/AAAA HH:MM*", parse_mode="Markdown")
        bot.register_next_step_handler(message, tratar_previsao, circuito, numero, falha_ou_pendencia)
    except Exception as e:
        logging.error(f"[tratar_pendencia] Erro crítico: {e}")
        os._exit(1)  # Encerra o processo imediatamente

def atualizar_fluxo_usuario(circuito, nova_opcao, numero):
    try:
        fluxo_atual = buscar_fluxo_no_bd(circuito, numero)

        logging.info(f"Fluxo atual antes da atualização: {fluxo_atual}")

        if fluxo_atual and isinstance(fluxo_atual, tuple):
            fluxo_atual = fluxo_atual[0]

        if fluxo_atual is None:
            fluxo_atual = ""

        # Adicione um delimitador, como uma vírgula, para separar as opções
        if fluxo_atual:
            fluxo_atual += ","  # Usando vírgula como delimitador
        fluxo_atual += nova_opcao

        salvar_fluxo_no_bd(fluxo_atual, circuito, numero)

        return fluxo_atual
    
    except Exception as e:
        logging.error(f"[atualizar_fluxo_usuario] Erro crítico: {e}")
        os._exit(1)  # Encerra o processo imediatamente

def finaliza_informacao(message, chat_id, previsao_data, circuito, numero):
    try:
        global fila_circuitos

        resposta = message.text.strip()
        logging.info(f"[finaliza_informacao] Resposta recebida do usuário {message.from_user.username} para o circuito {circuito}: {resposta}")
        salvar_estado_usuario(chat_id, 'esperando_opcao', circuito, numero)
        if resposta == '1':
            try:
                # Atualiza informações no banco de dados
                atualizar_fluxo_usuario(circuito, resposta, numero)

                # Reinicia o fluxo do usuário
                logging.info(f"[finaliza_informacao] Reiniciando fluxo do usuário {message.from_user.username} para o circuito {circuito} numero: {numero}.")
                bot.send_message(message.chat.id, "*OK*! Vamos reiniciar a nossa conversa...", parse_mode="Markdown")
                logging.info(f"[finaliza_informacao] chat_id : {chat_id} circuito: {circuito} numero: {numero}")
                logging.info(f"[finaliza_informacao] chat_id : {type(chat_id)} circuito: {type(circuito)} numero: {type(numero)}")
                # bot.register_next_step_handler(message, lambda msg: enviar_opcoes_escalacao(chat_id, circuito))
                enviar_opcoes_escalacao(chat_id, circuito, numero)
                limpar_chave_busca_info(circuito, numero)
                # bot.register_next_step_handler(enviar_opcoes_escalacao, chat_id, circuito)
                logging.info(f"[finaliza_informacao] Depois do enviar_opcoes_escalacao")
            except Exception as e:
                bot.send_message(message.chat.id, "Ocorreu um erro ao registrar a informação final. Por favor, tente novamente.")
                logging.error(f"[finaliza_informacao] Erro ao registrar informação final para o circuito {circuito} numero {numero}: {e}")

        elif resposta == '2':
            try:
                # Atualiza banco de dados
                data = datetime.now()
                atualizar_ult_msg_no_bd(resposta, circuito, numero)
                atualizar_fluxo_usuario(circuito, resposta, numero)
                atualizar_data_proxima_cobranca(circuito, previsao_data, numero)
                atualizar_previsao_conclusao(previsao_data, circuito, numero)
                atualizar_data_atualizacao(data, circuito, numero)


                # Envia mensagem de agradecimento e conclui o fluxo
                bot.send_message(message.chat.id, "Obrigado pelas informações! Foi *V.tal* o seu contato, até a próxima!", parse_mode="Markdown")
                logging.info(f"[finaliza_informacao] Previsão de conclusão registrada: {previsao_data}. Encerrando fluxo do circuito {circuito} numero {numero}.")
                atualizar_notificacao(circuito, numero)
                # Finaliza o estado do usuário para o circuito atual
                salvar_estado_usuario(chat_id, 'cobrança_encerrada', circuito, numero)

                # Remove o circuito atual da fila, já que a interação foi concluída
                if circuito in fila_circuitos:
                    fila_circuitos.remove(circuito)
                    logging.info(f"[finaliza_informacao] Circuito {circuito} numero {numero} removido da fila após conclusão do fluxo.")

            except Exception as e:
                logging.error(f"[finaliza_informacao] Erro ao registrar previsão de conclusão para o circuito {circuito} numero {numero}: {e}")

        else:
            # Resposta inválida, pede ao usuário para escolher novamente
            bot.reply_to(message, "Opção inválida. Escolha novamente.")
            logging.warning(f"[finaliza_informacao] Opção inválida escolhida pelo usuário {message.from_user.username}: {resposta}")

    except Exception as e:
        logging.error(f"[finaliza_informacao] Erro crítico: {e}")
        os._exit(1)  # Encerra o processo imediatamente

def tratar_previsao(message, circuito, numero, falha_ou_pendencia):
    try:
        previsao = message.text.strip()
        user_id = message.chat.id

        # Regex para validar o formato DD/MM/AA HH:MM
        formato_data = r"\d{2}/\d{2}/(\d{4}|\d{2}) \d{2}:\d{2}"

        # Verifica se o formato é válido
        if not re.match(formato_data, previsao):
            bot.reply_to(message, "Formato de data inválido. Favor informar a data no formato: DD/MM/AAAA HH:MM")
            bot.register_next_step_handler(message, tratar_previsao, circuito, numero, falha_ou_pendencia)
            return

        try:
            # Define o formato de parsing baseado no comprimento do ano
            if len(previsao.split()[0].split('/')[2]) == 2:
                previsao_data = datetime.strptime(previsao, "%d/%m/%y %H:%M")
            else:
                previsao_data = datetime.strptime(previsao, "%d/%m/%Y %H:%M")
            
            # Verifica se a data de previsão é no futuro
            if previsao_data <= datetime.now():
                bot.reply_to(message, "A data e hora de previsão deve ser maior que a data e hora atual. Informe uma nova data no formato: DD/MM/AAAA HH:MM")
                bot.register_next_step_handler(message, tratar_previsao, circuito, numero, falha_ou_pendencia)
                return

            chat_id = message.chat.id
            data_atual = datetime.now()
            atualizar_previsao_conclusao(previsao_data, circuito, numero)
            mask = valid_mask(falha_ou_pendencia, previsao_data)
            atualizar_valid_mask(mask, data_atual, circuito, numero)
            # Reinicia o fluxo após atualizar a previsão
            bot.reply_to(message, "As informações repassadas foram registradas.\n*Gostaria de alterar as informações?*\n1 - Sim, desejo alterar.\n2 - Não. Até a próxima!", parse_mode="Markdown")
            bot.register_next_step_handler(message, finaliza_informacao, chat_id, previsao_data, circuito, numero)
            

        except ValueError:
            bot.reply_to(message, "Formato de data inválido. Tente novamente no formato: *DD/MM/AAAA HH:MM*", parse_mode="Markdown")
            logging.error(f"Formato de data inválido recebido do usuário {message.from_user.username}: {previsao}")
            bot.register_next_step_handler(message, tratar_previsao, circuito, numero, falha_ou_pendencia)

    except Exception as e:
        logging.error(f"[tratar_previsao] Erro crítico: {e}")
        os._exit(1)  # Encerra o processo imediatamente

def processar_matricula(message):
    matricula = message.text.strip()
    usuario = verificar_matricula(matricula)

    if usuario:
        chat_id = message.chat.id
        atualizar_chatid(chat_id, matricula)
        bot.reply_to(message, f"Cadastro realizado com sucesso para a matrícula: {matricula}.")
    else:
        bot.reply_to(message, "Matrícula não encontrada. Por favor, verifique e tente novamente.")

##################################################### Bot config #####################################################

# Função para agendar o job de envio de notificações a cada 1 minuto
def agendar_jobs():
    logging.info("Agendando job de notificações...")
    logging.info("JOB de Notificações críticas agendado!")
    schedule.every(1).minutes.do(notifica_reparos_criticos)  # Chama a função de notificação

    logging.info("JOB de Cobrança reparo crítico agendado!")
    schedule.every(1).minutes.do(processar_reparos)

    logging.info("JOB de Atualização de nível notificação!")
    schedule.every(1).minutes.do(atualiza_notificacao_escala)

    logging.info("JOB de historico agendamento diário às 08:00")
    schedule.every().day.at("08:00").do(enviar_status_reparo)

    while True:
        schedule.run_pending()
        time.sleep(1)  # Evita sobrecarga de CPU

# Função principal para executar o bot e agendar o job
if __name__ == '__main__':
    logging.info("Iniciando o bot...")

    # Inicia o agendamento em uma thread separada para não bloquear o bot
    threading.Thread(target=agendar_jobs, daemon=True).start()


    # retry_time = 5  # Tempo inicial de espera em segundos
    while True:
        try:
            logging.info("Bot está rodando...")
            bot.polling(none_stop=True, interval=1)
        except Exception as e:
            logging.error(f"Ocorreu um erro: {e}")
            time.sleep(5)  # Aguarde 5 segundos antes de tentar novamente
            os._exit(1)

    # while True:
    #     try:
    #         bot.polling(none_stop=True, interval=1)  # Inicia o bot e mantém o polling contínuo
    #     except ReadTimeout:
    #         logging.error(f"ReadTimeout. Tentando novamente em {retry_time} segundos...")
    #         time.sleep(retry_time)
    #         retry_time = min(retry_time * 2, 60)  # Exponencial backoff, máximo de 60 segundos
    #     except requests.exceptions.ConnectionError:
    #         logging.error(f"ConnectionError. Tentando novamente em {retry_time} segundos...")
    #         time.sleep(retry_time)
    #         retry_time = min(retry_time * 2, 60)  # Exponencial backoff para falhas de conexão
    #     except Exception as e:
    #         logging.error(f"Ocorreu um erro inesperado: {e}")
    #         time.sleep(5)
    #         retry_time = 5  # Reseta o tempo de espera para exceções genéricas


