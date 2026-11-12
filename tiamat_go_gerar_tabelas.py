#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tiamat / ATP-203: SGFs do Joe's Go Database -> CSVs por lance.

Sem dependências externas. Entrada: data/{train,val,test}.txt e data/sgf/...
Saída: data/processed/lance_040.csv (ou lance_000/120), auditoria e resumo.

Uso piloto:
  python tiamat_go_gerar_tabelas.py --data data --lances 40 \
      --amostra-train 5000 --amostra-val 300 --amostra-test 300
Uso completo:
  python tiamat_go_gerar_tabelas.py --data data --lances 40
Uso futuro (uma leitura por SGF para os três marcos):
  python tiamat_go_gerar_tabelas.py --data data --lances 0 40 120

Representação: uma linha por partida por lance; 'split' preserva o índice oficial.
'vencedor' é o único alvo; 'game_id', 'split', 'sgf_path', 'hash_sgf' e
'lance' são campos administrativos, não atributos preditivos.
'resultado_sgf' e 'motivo_derrota' são desfechos, PROIBIDOS como entrada
do modelo no lance 40 (vazamento de dados).
Ranks: xd=x; yp=y+6; zk=-z (escala proposta pelo usuário).
Partidas com ranks ausentes ou fora de k/d/p numérico são descartadas.
Passes: B[], W[], B[tt], W[tt] (tabuleiro 19x19) contam como jogadas.

Limitações: processa a linha principal de SGF; tabuleiro 19x19, sem verificação
de ko/superko nem suporte a suicídio. Partidas não suportadas são auditadas.
As regras de pontuação não são inferidas. Capturas = jogadas até o marco.
"""

import argparse
import csv
from collections import Counter, deque
import hashlib
import json
import math
from pathlib import Path
import random
import re
from contextlib import ExitStack


COLUNAS = [
    'game_id', 'split', 'sgf_path', 'hash_sgf', 'lance',
    'rank_b_original', 'rank_w_original',
    'rank_b', 'rank_w',
    'komi', 'handicap',
    'maior_grupo_b', 'maior_grupo_w',
    'liberdades_maior_grupo_b', 'liberdades_maior_grupo_w',
    'pedras_em_jogo_b', 'pedras_em_jogo_w',
    'pedras_capturadas_por_b', 'pedras_capturadas_por_w',
    'distancia_media_tengen_b', 'distancia_media_tengen_w',
    'quantidade_grupos_b', 'quantidade_grupos_w',
    'tamanho_medio_grupos_b', 'tamanho_medio_grupos_w',
    'liberdades_medias_grupos_b', 'liberdades_medias_grupos_w',
    'grupos_em_atari_b', 'grupos_em_atari_w',
    'pedras_em_atari_b', 'pedras_em_atari_w',
    'vencedor', 'resultado_sgf', 'motivo_derrota',
]

AUDITORIA_COLUNAS = ['split', 'sgf_path', 'status', 'detalhe', 'lances_reconstruidos', 'hash_sgf']


def ler_linha_principal_sgf(texto):
    """Parser SGF pequeno: propriedades SGF e primeira variação da árvore.

    É voltado ao subconjunto de registros do JGDB. Não pretende aceitar
    todos os formatos ou extensões possíveis do SGF.
    """
    n = len(texto)
    i = 0

    def espacos():
        nonlocal i
        while i < n and texto[i].isspace():
            i += 1

    def valor():
        nonlocal i
        if i >= n or texto[i] != '[':
            raise ValueError('Valor SGF inválido')
        i += 1
        partes = []
        while i < n:
            ch = texto[i]
            i += 1
            if ch == ']':
                return ''.join(partes)
            if ch == '\\' and i < n:
                ch = texto[i]
                i += 1
                if ch == '\r' or ch == '\n':
                    if ch == '\r' and i < n and texto[i] == '\n':
                        i += 1
                    continue
            partes.append(ch)
        raise ValueError('SGF truncado: valor sem fechamento ]')

    def arvore():
        nonlocal i
        espacos()
        if i >= n or texto[i] != '(':
            raise ValueError('SGF sem abertura (')
        i += 1
        nos = []
        while True:
            espacos()
            if i >= n:
                raise ValueError('SGF incompleto')
            if texto[i] != ';':
                break
            i += 1
            props = {}
            while True:
                espacos()
                if i >= n or not ('A' <= texto[i] <= 'Z'):
                    break
                inicio = i
                while i < n and 'A' <= texto[i] <= 'Z':
                    i += 1
                chave = texto[inicio:i]
                espacos()
                valores = []
                while i < n and texto[i] == '[':
                    valores.append(valor())
                    espacos()
                if not valores:
                    raise ValueError(f'Propriedade sem valor: {chave}')
                props.setdefault(chave, []).extend(valores)
            nos.append(props)
        variacao_primaria = []
        while True:
            espacos()
            if i < n and texto[i] == '(':
                v = arvore()
                if not variacao_primaria:
                    variacao_primaria = v
            else:
                break
        if i >= n or texto[i] != ')':
            raise ValueError('SGF sem fechamento )')
        i += 1
        return nos + variacao_primaria

    resultado = arvore()
    espacos()
    if i != n:
        raise ValueError('SGF contém dados adicionais após a árvore')
    if not resultado:
        raise ValueError('SGF sem nós')
    return resultado


def primeiro(propriedades, chave, padrao=None):
    return propriedades.get(chave, [padrao])[0]


def coordenada_sgf(valor, tamanho=19, jogada=False):
    # Em SGFs históricos 19x19, tt representa passe. [] é passe FF4.
    if jogada and (valor == '' or (valor == 'tt' and tamanho <= 19)):
        return None
    if len(valor) != 2:
        raise ValueError(f'Coordenada SGF inválida: {valor!r}')
    col, lin = ord(valor[0]) - ord('a'), ord(valor[1]) - ord('a')
    if not (0 <= lin < tamanho and 0 <= col < tamanho):
        raise ValueError(f'Coordenada SGF fora do tabuleiro: {valor!r}')
    return lin, col


def expandir_pontos_sgf(valor, tamanho):
    if ':' not in valor:
        return [coordenada_sgf(valor, tamanho)]
    p, q = valor.split(':', 1)
    (r1, c1), (r2, c2) = coordenada_sgf(p, tamanho), coordenada_sgf(q, tamanho)
    if r1 > r2 or c1 > c2:
        raise ValueError(f'Retângulo SGF inválido: {valor!r}')
    return [(r, c) for r in range(r1, r2+1) for c in range(c1, c2+1)]


class Tabuleiro:
    def __init__(self, tamanho=19):
        self.n = tamanho
        self.casas = [['.' for _ in range(tamanho)] for _ in range(tamanho)]

    def vizinhos(self, r, c):
        for rr, cc in ((r-1, c), (r+1, c), (r, c-1), (r, c+1)):
            if 0 <= rr < self.n and 0 <= cc < self.n:
                yield rr, cc

    def grupo(self, r, c):
        cor = self.casas[r][c]
        if cor == '.':
            return set(), set()
        pedras = {(r, c)}
        liberdades = set()
        fila = deque([(r, c)])
        while fila:
            rr, cc = fila.popleft()
            for nr, nc in self.vizinhos(rr, cc):
                if self.casas[nr][nc] == '.':
                    liberdades.add((nr, nc))
                elif self.casas[nr][nc] == cor and (nr, nc) not in pedras:
                    pedras.add((nr, nc))
                    fila.append((nr, nc))
        return pedras, liberdades

    def configurar(self, no):
        # Setup AB/AW/AE nunca equivale a movimentos ou capturas.
        for propriedade, cor in (('AB', 'b'), ('AW', 'w'), ('AE', '.')):
            for valor in no.get(propriedade, []):
                for r, c in expandir_pontos_sgf(valor, self.n):
                    self.casas[r][c] = cor

    def jogar(self, cor, local):
        if local is None:
            return 0
        r, c = local
        if self.casas[r][c] != '.':
            raise ValueError(f'Jogada em interseção ocupada: {local}')
        self.casas[r][c] = cor
        adversaria = 'w' if cor == 'b' else 'b'
        capturadas = set()
        for nr, nc in self.vizinhos(r, c):
            if self.casas[nr][nc] == adversaria:
                pedras, liberdades = self.grupo(nr, nc)
                if not liberdades:
                    capturadas.update(pedras)
        for nr, nc in capturadas:
            self.casas[nr][nc] = '.'
        _, liberdades_proprias = self.grupo(r, c)
        if not liberdades_proprias:
            raise ValueError('Suicídio/auto-captura não suportado pelo extrator')
        return len(capturadas)

    def estatisticas(self):
        grupos = {'b': [], 'w': []}
        visitadas = set()
        distancias = {'b': [], 'w': []}
        tengen = (self.n - 1)/2
        for r in range(self.n):
            for c in range(self.n):
                cor = self.casas[r][c]
                if cor == '.':
                    continue
                distancias[cor].append(math.hypot(r-tengen, c-tengen))
                if (r, c) not in visitadas:
                    pedras, libs = self.grupo(r, c)
                    visitadas.update(pedras)
                    grupos[cor].append((pedras, libs))
        atributos = {}
        for cor in ('b', 'w'):
            pares = grupos[cor]
            tamanhos = [len(p) for p, _ in pares]
            nlibs = [len(l) for _, l in pares]
            maior = max(tamanhos, default=0)
            # Empate de maior grupo: média de liberdades dos grupos empatados.
            libs_maiores = [len(l) for p, l in pares if len(p) == maior]
            atributos[f'maior_grupo_{cor}'] = maior
            atributos[f'liberdades_maior_grupo_{cor}'] = (
                sum(libs_maiores)/len(libs_maiores) if libs_maiores else None
            )
            atributos[f'pedras_em_jogo_{cor}'] = sum(tamanhos)
            atributos[f'distancia_media_tengen_{cor}'] = (
                sum(distancias[cor])/len(distancias[cor]) if distancias[cor] else None
            )
            atributos[f'quantidade_grupos_{cor}'] = len(pares)
            atributos[f'tamanho_medio_grupos_{cor}'] = (
                sum(tamanhos)/len(pares) if pares else None
            )
            atributos[f'liberdades_medias_grupos_{cor}'] = (
                sum(nlibs)/len(pares) if pares else None
            )
            atributos[f'grupos_em_atari_{cor}'] = sum(n == 1 for n in nlibs)
            atributos[f'pedras_em_atari_{cor}'] = sum(
                len(p) for p, l in pares if len(l) == 1
            )
        return atributos


def graduacao(valor):
    if not valor:
        return None, None
    m = re.fullmatch(r'\s*(\d+)\s*([kdp])\s*', valor, re.IGNORECASE)
    if not m:
        return None, None
    return m.group(2).lower(), int(m.group(1))


def rank_numerico(valor):
    """Escala estipulada para a Tiamat: xd=x, yp=y+6 e zk=-z.

    Exemplos: 7d=7, 3p=9, 10k=-10. Valores ausentes ou não
    reconhecidos retornam None; o texto original permanece no CSV.

    Atenção: escala de conveniência definida pelo projeto, NÃO uma medida
    validada de força relativa entre kyu, dan amador e profissional.
    """
    tipo, nivel = graduacao(valor)
    if tipo is None:
        return None
    return {'d': nivel, 'p': nivel + 6, 'k': -nivel}[tipo]


def classificar_motivo_derrota(resultado):
    """Classifica o desfecho do campo RE do SGF.

    Somente metadado do DESFECHO; jamais deve compor X ao prever o vencedor.
    Outros resultados ou sufixos não reconhecidos viram 'outro' ou
    'desconhecido', sem forçar a categoria 'pontos'.
    """
    m = re.fullmatch(r'\s*[BW]\s*\+\s*(.*?)\s*', resultado, re.IGNORECASE)
    if not m:
        return 'desconhecido'
    sufixo = m.group(1).strip().lower()
    if sufixo in {'t', 'time'}:
        return 'tempo'
    if sufixo in {'r', 'resign', 'resignation'}:
        return 'desistencia'
    if re.fullmatch(r'(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)', sufixo):
        return 'pontos'
    return 'outro' if sufixo else 'desconhecido'


def extrair_sgf(conteudo, lances):
    """Retorna dict {lance: linha} e quantidade de jogadas processadas.

    Lê o resultado apenas para o target e não acessa jogadas posteriores ao
    marco necessário para gerar as features.
    """
    # A estrutura das propriedades SGF é ASCII, independentemente dos campos de texto.
    nos = ler_linha_principal_sgf(conteudo.decode('latin-1'))
    raiz = nos[0]
    tamanho = int(primeiro(raiz, 'SZ', '19'))
    if tamanho != 19:
        raise ValueError(f'Tabuleiro {tamanho}x{tamanho}: esperado 19x19')
    resultado = (primeiro(raiz, 'RE', '') or '').strip()
    m = re.match(r'^([BW])\+', resultado, flags=re.IGNORECASE)
    if not m:
        raise ValueError(f'Resultado sem vencedor binário: {resultado!r}')
    vencedor = m.group(1).upper()
    rb = primeiro(raiz, 'BR')
    rw = primeiro(raiz, 'WR')
    rank_b = rank_numerico(rb)
    rank_w = rank_numerico(rw)
    if rank_b is None or rank_w is None:
        raise ValueError(f'Rank ausente ou incomum: BR={rb!r}, WR={rw!r}')
    komi_bruto = primeiro(raiz, 'KM')
    try:
        komi = float(komi_bruto) if komi_bruto is not None else None
    except ValueError as exc:
        raise ValueError(f'Komi inválido: {komi_bruto!r}') from exc
    # Alguns SGFs do JGDB registram HA em nós de configuração (ex.: ;AB[dp]HA[2]).
    # Apenas metadados ANTERIORES à primeira jogada podem ser consultados.
    nos_iniciais = []
    for no in nos:
        if 'B' in no or 'W' in no:
            break
        nos_iniciais.append(no)
    handicaps_declarados = [v for no in nos_iniciais for v in no.get('HA', [])]
    if len(set(handicaps_declarados)) > 1:
        raise ValueError(f'Valores de handicap conflitantes: {handicaps_declarados!r}')
    handicap_bruto = handicaps_declarados[0] if handicaps_declarados else None
    tem_ab = any('AB' in no for no in nos_iniciais)
    try:
        # AB sem HA não prova que o handicap seja zero.
        handicap = int(handicap_bruto) if handicap_bruto is not None else (None if tem_ab else 0)
        if handicap is not None and handicap < 0:
            raise ValueError('Handicap negativo')
    except ValueError as exc:
        raise ValueError(f'Handicap inválido: {handicap_bruto!r}') from exc

    meta = {
        'rank_b_original': rb, 'rank_w_original': rw,
        'rank_b': rank_b, 'rank_w': rank_w,
        'komi': komi, 'handicap': handicap,
        'vencedor': vencedor,
        'resultado_sgf': resultado,
        'motivo_derrota': classificar_motivo_derrota(resultado),
    }
    tabuleiro = Tabuleiro(tamanho)
    contagem = {'b': 0, 'w': 0}
    saidas = {}
    n_jogadas = 0
    comecou = False
    maior_lance = max(lances)

    def salvar(lance):
        if lance in lances and lance not in saidas:
            linha = {**meta, 'lance': lance}
            linha.update(tabuleiro.estatisticas())
            linha['pedras_capturadas_por_b'] = contagem['b']
            linha['pedras_capturadas_por_w'] = contagem['w']
            saidas[lance] = linha

    for no in nos:
        if 'B' in no and 'W' in no:
            raise ValueError('Nó com duas jogadas simultâneas')
        if any(chave in no for chave in ('AB', 'AW', 'AE')):
            if comecou:
                raise ValueError('Configuração de tabuleiro após começar a partida')
            tabuleiro.configurar(no)
        movimento = 'B' if 'B' in no else ('W' if 'W' in no else None)
        if movimento is None:
            continue
        if not comecou:
            salvar(0)  # Guarda todas as configurações de handicap anteriores.
            comecou = True
        loc = coordenada_sgf(primeiro(no, movimento), tamanho, jogada=True)
        capturadas = tabuleiro.jogar(movimento.lower(), loc)
        contagem[movimento.lower()] += capturadas
        n_jogadas += 1  # Não conta pedras iniciais; passes contam.
        salvar(n_jogadas)
        if n_jogadas >= maior_lance:
            break
    if not comecou:
        salvar(0)
    return saidas, n_jogadas


def iterar_indices(arquivo_indice):
    with arquivo_indice.open('r', encoding='utf-8-sig') as f:
        for linha in f:
            caminho = linha.strip()
            if caminho and not caminho.startswith('#'):
                yield caminho


def selecionar_indices(arquivo_indice, limite, seed):
    if limite is None:
        yield from iterar_indices(arquivo_indice)
        return
    # Amostra reprodutível de caminhos; evita viés de pegar os primeiros IDs.
    todos = list(iterar_indices(arquivo_indice))
    if limite >= len(todos):
        yield from todos
        return
    rng = random.Random(seed)
    indices = set(rng.sample(range(len(todos)), limite))
    for i, caminho in enumerate(todos):
        if i in indices:
            yield caminho


def localizar_sgf(raiz, split, caminho_indice):
    p = Path(caminho_indice)
    if p.is_absolute():
        raise ValueError('Caminho absoluto no índice')
    relativo = Path(str(p).removeprefix('./'))
    partes = relativo.parts
    if len(partes) < 4 or partes[:2] != ('sgf', split) or relativo.suffix.lower() != '.sgf':
        raise ValueError(f'Caminho inválido para split {split}: {caminho_indice!r}')
    arquivo = (raiz / relativo).resolve()
    if not arquivo.is_relative_to(raiz.resolve()):
        raise ValueError(f'Caminho escapando da raiz: {relativo}')
    return arquivo, relativo.as_posix()


def executar(args):
    raiz = args.data.resolve()
    outdir = args.saida if args.saida is not None else raiz / 'processed'
    outdir.mkdir(parents=True, exist_ok=True)
    lances = sorted(set(args.lances))
    if any(l < 0 for l in lances):
        raise ValueError('Lances não podem ser negativos')

    contadores = {l: Counter() for l in lances}
    auditoria = {l: Counter() for l in lances}
    vistos = {}  # hash SGF -> (split, SGF original), para detectar duplicações exatas

    with ExitStack() as stack:
        escritores = {}
        escritores_audit = {}
        for lance in lances:
            ff = stack.enter_context((outdir / f'lance_{lance:03}.csv').open(
                'w', encoding='utf-8', newline=''))
            fa = stack.enter_context((outdir / f'auditoria_lance_{lance:03}.csv').open(
                'w', encoding='utf-8', newline=''))
            w = csv.DictWriter(ff, fieldnames=COLUNAS, extrasaction='raise')
            wa = csv.DictWriter(fa, fieldnames=AUDITORIA_COLUNAS)
            w.writeheader()
            wa.writeheader()
            escritores[lance], escritores_audit[lance] = w, wa

        for split in ('train', 'val', 'test'):
            indice = raiz / f'{split}.txt'
            if not indice.is_file():
                raise FileNotFoundError(f'Índice ausente: {indice}')
            limite = getattr(args, f'amostra_{split}')
            for pos, entrada in enumerate(selecionar_indices(indice, limite, args.seed)):
                caminho_rel = entrada
                identificador_hash = ''
                processados = 0
                try:
                    arquivo, caminho_rel = localizar_sgf(raiz, split, entrada)
                    conteudo = arquivo.read_bytes()
                    identificador_hash = hashlib.sha256(conteudo).hexdigest()
                    if identificador_hash in vistos:
                        anterior = vistos[identificador_hash]
                        raise RuntimeError(f'duplicado exato de {anterior[0]}/{anterior[1]}')
                    vistos[identificador_hash] = (split, caminho_rel)
                    registros, processados = extrair_sgf(conteudo, lances)
                    status = None
                    detalhe = ''
                except Exception as exc:
                    registros = {}
                    if isinstance(exc, RuntimeError) and str(exc).startswith('duplicado exato'):
                        status = 'duplicado_exato'
                    elif isinstance(exc, ValueError) and str(exc).startswith('Resultado sem vencedor binário:'):
                        status = 'resultado_sem_vencedor'
                    elif isinstance(exc, ValueError) and str(exc).startswith('Rank ausente ou incomum:'):
                        status = 'rank_incomum'
                    else:
                        status = 'erro_sgf'
                    detalhe = str(exc)[:300]

                for lance in lances:
                    if lance in registros:
                        identificador = f'{split}:{Path(caminho_rel).relative_to(Path("sgf") / split).with_suffix("").as_posix()}'
                        linha = {
                            'game_id': identificador,
                            'split': split,
                            'sgf_path': caminho_rel,
                            'hash_sgf': identificador_hash,
                            **registros[lance],
                        }
                        escritores[lance].writerow(linha)
                        contadores[lance][f'{split}_incluidas'] += 1
                        contadores[lance][f'{split}_vitorias_{linha["vencedor"]}'] += 1
                        st = 'ok'
                        det = ''
                    else:
                        st = status or 'partida_curta'
                        det = detalhe if status else f'Não chegou ao lance {lance}'
                    if st != 'ok':
                        auditoria[lance][f'{split}_{st}'] += 1
                    escritores_audit[lance].writerow({
                        'split': split, 'sgf_path': caminho_rel,
                        'status': st, 'detalhe': det,
                        'lances_reconstruidos': processados,
                        'hash_sgf': identificador_hash,
                    })
                if (pos+1) % args.progresso == 0:
                    print(f'[{split}] {pos+1:,} SGFs considerados', flush=True)
            print(f'[{split}] concluído', flush=True)

    for lance in lances:
        resumo = {
            'lance': lance, 'arquivo': f'lance_{lance:03}.csv',
            'atributos': [col for col in COLUNAS if col not in {
                'game_id','split','sgf_path','hash_sgf','lance','vencedor',
                'rank_b_original','rank_w_original','resultado_sgf','motivo_derrota',
            }],
            'target': 'vencedor',
            'campos_excluidos_do_modelo': [
                'game_id','split','sgf_path','hash_sgf','lance','vencedor',
                'rank_b_original','rank_w_original','resultado_sgf','motivo_derrota',
            ],
            'contagens': dict(contadores[lance]),
            'auditoria': dict(auditoria[lance]),
            'amostra_solicitada': {
                sp: getattr(args, f'amostra_{sp}') for sp in ('train','val','test')
            },
            'seed': args.seed,
            'observacoes': [
                'Os splits oficiais são preservados na coluna split.',
                'CSV UTF-8: valores ausentes ficam vazios.',
                'Nenhuma imputação, normalização ou seleção supervisionada foi aplicada.',
                'Grupos empatados como maior grupo: liberdades médias desses grupos.',
                'Distância ao tengen das pedras presentes, não de todas as jogadas.',
                'Ranks: xd=x, yp=y+6, zk=-z; partidas com rank ausente/incomum são excluídas.',
                'Passes: B[], W[], B[tt], W[tt] são jogadas válidas sem colocação de pedra.',
                'Essa escala de rank não é uma equivalência validada de força entre sistemas.',
                'resultado_sgf e motivo_derrota são metadados de resultado e NÃO podem entrar no modelo preditivo.',
                'Suicídio não suportado; arquivos problemáticos são auditados.',
                'HA é lido nos nós anteriores à primeira jogada, inclusive nós AB.',
                'Resultados sem vencedor binário são excluídos e auditados separadamente.',
                'Duplicatas exatas de conteúdo SGF são excluídas após a primeira ocorrência.',
            ],
        }
        (outdir / f'resumo_lance_{lance:03}.json').write_text(
            json.dumps(resumo, indent=2, ensure_ascii=False), encoding='utf-8'
        )
        print(f'Lance {lance}: {sum(v for k,v in contadores[lance].items() if k.endswith("_incluidas")):,} linhas; {outdir / f"lance_{lance:03}.csv"}')
        print('  excluídas:', dict(auditoria[lance]))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--data', type=Path, default=Path('data'), help='Diretório data/ do JGDB')
    parser.add_argument('--saida', type=Path, help='Diretório de saída; padrão data/processed')
    parser.add_argument('--lances', nargs='+', type=int, default=[40], help='Marcos: 0 40 120')
    parser.add_argument('--amostra-train', type=int, help='Sorteio de N SGFs do train.txt')
    parser.add_argument('--amostra-val', type=int, help='Sorteio de N SGFs do val.txt')
    parser.add_argument('--amostra-test', type=int, help='Sorteio de N SGFs do test.txt')
    parser.add_argument('--seed', type=int, default=210906)
    parser.add_argument('--progresso', type=int, default=10000)
    args = parser.parse_args()
    if any(getattr(args, f'amostra_{sp}') is not None and getattr(args, f'amostra_{sp}') < 0 for sp in ('train','val','test')):
        parser.error('O tamanho da amostra não pode ser negativo')
    if args.progresso <= 0:
        parser.error('--progresso deve ser positivo')
    executar(args)


if __name__ == '__main__':
    main()
