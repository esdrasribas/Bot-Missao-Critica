from datetime import datetime

def valid_mask(falha_ou_pendencia, data_previsao):
    data_previsao_formatada = data_previsao.strftime("%d/%m/%Y %H:%M")
    mask = {
        "Falha Equipamento - Cliente" : f"Equipe já identificou a falha para o equipamento do cliente com previsão de finalizar atuação em {data_previsao_formatada}.",
        "Falha Equipamento - Vtal" : f"Equipe já identificou a falha para o equipamento da V.tal com previsão de finalizar atuação em {data_previsao_formatada}.",
        "Rompimento de Fibra - Backbone" : f"Equipe já identificou a falha para rompimento de fibra backbone com previsão de finalizar atuação em {data_previsao_formatada}.",
        "Rompimento de Fibra - Acesso": f"Equipe já identificou a falha para rompimento de fibra acesso com previsão de finalizar atuação em {data_previsao_formatada}.",
        "Outros - Transmissão": f"Equipe já identificou a falha para transmissão com previsão de finalizar atuação em {data_previsao_formatada}.",
        "Outros - Cabo de acesso": f"Equipe já identificou a falha para cabo de acesso com previsão de finalizar atuação em {data_previsao_formatada}.",
        "Pendência Cliente" : f"Reparo em pendência por motivo do cliente com previsão de retorno da atuação em {data_previsao_formatada}.",
        "Pendência Área de Risco" : f"Reparo em pendência por motivo área de risco com previsão de retorno da atuação em {data_previsao_formatada}."}
    if falha_ou_pendencia in mask:
        return mask[f'{falha_ou_pendencia}']



def obter_regional(uf):
    """
    Retorna a região responsável pela UF fornecida.
    """
    import logging  # Importação de logging para registrar o processo
    logging.info(f"[obter_regional] Buscando região para UF: {uf}")
    
    regionais = {
        'SUDESTE': ['RJ', 'SP', 'ES', 'MG'],
        'NE_NO': ['AM', 'PA', 'RR', 'AP', 'MA', 'CE', 'AL', 'BA', 'PE', 'PB', 'PI', 'SE', 'RN'],
        'SUL': ['PR', 'RS', 'SC'],
        'CO': ['MT', 'MS', 'GO', 'DF', 'AC', 'RO', 'TO'],
    }

    for regiao, ufs in regionais.items():
        if uf in ufs:
            return regiao
    return None  # Retorna None se a UF não corresponder a nenhuma região