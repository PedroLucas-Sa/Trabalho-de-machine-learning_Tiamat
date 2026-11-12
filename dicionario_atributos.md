# Dicionário dos atributos

Definições conferidas no script `tiamat_go_gerar_tabelas.py` do projeto e no resumo da extração final. Todas as estatísticas posicionais representam o estado após 40 jogadas. `b` significa pretas e `w`, brancas.

Um grupo reúne pedras da mesma cor conectadas ortogonalmente. Suas liberdades são as interseções vazias ortogonalmente adjacentes ao grupo, contadas sem repetição dentro de cada grupo. Um grupo em atari tem exatamente uma liberdade.

| Atributo | Definição | Unidade |
|---|---|---|
| `rank_b` | Graduação das pretas convertida pela escala do projeto | Escala de rank |
| `rank_w` | Graduação das brancas convertida pela escala do projeto | Escala de rank |
| `komi` | Valor da compensação informado nas condições da partida | Pontos |
| `handicap` | Número de pedras de handicap declarado antes da primeira jogada; pode estar ausente quando não há informação suficiente | Pedras |
| `maior_grupo_b` | Número de pedras no maior grupo preto presente | Pedras |
| `maior_grupo_w` | Número de pedras no maior grupo branco presente | Pedras |
| `liberdades_maior_grupo_b` | Liberdades do maior grupo preto; média quando há empate de tamanho entre maiores grupos | Liberdades |
| `liberdades_maior_grupo_w` | Liberdades do maior grupo branco; média quando há empate de tamanho entre maiores grupos | Liberdades |
| `pedras_em_jogo_b` | Pedras pretas presentes no tabuleiro | Pedras |
| `pedras_em_jogo_w` | Pedras brancas presentes no tabuleiro | Pedras |
| `pedras_capturadas_por_b` | Total acumulado de pedras brancas removidas por capturas das pretas até o lance 40 | Pedras |
| `pedras_capturadas_por_w` | Total acumulado de pedras pretas removidas por capturas das brancas até o lance 40 | Pedras |
| `distancia_media_tengen_b` | Média das distâncias euclidianas das pedras pretas presentes até o centro do tabuleiro | Espaçamentos entre interseções |
| `distancia_media_tengen_w` | Média das distâncias euclidianas das pedras brancas presentes até o centro do tabuleiro | Espaçamentos entre interseções |
| `quantidade_grupos_b` | Número de grupos pretos presentes | Grupos |
| `quantidade_grupos_w` | Número de grupos brancos presentes | Grupos |
| `tamanho_medio_grupos_b` | Total de pedras pretas presentes dividido pelo número de grupos pretos | Pedras por grupo |
| `tamanho_medio_grupos_w` | Total de pedras brancas presentes dividido pelo número de grupos brancos | Pedras por grupo |
| `liberdades_medias_grupos_b` | Média das contagens de liberdades dos grupos pretos, sem ponderar pelo tamanho dos grupos | Liberdades por grupo |
| `liberdades_medias_grupos_w` | Média das contagens de liberdades dos grupos brancos, sem ponderar pelo tamanho dos grupos | Liberdades por grupo |
| `grupos_em_atari_b` | Número de grupos pretos com uma única liberdade | Grupos |
| `grupos_em_atari_w` | Número de grupos brancos com uma única liberdade | Grupos |
| `pedras_em_atari_b` | Soma das pedras pertencentes a grupos pretos em atari | Pedras |
| `pedras_em_atari_w` | Soma das pedras pertencentes a grupos brancos em atari | Pedras |

## Target e metadados

`vencedor` é o target: `B` vira 0 e `W` vira 1. `resultado_sgf` e `motivo_derrota` descrevem o encerramento e não entram nos modelos. `game_id`, `hash_sgf`, `sgf_path`, `split`, `lance` e ranks originais são metadados, não preditores.

Passes contam como jogadas sem colocar pedras. Pedras de configuração inicial não contam como jogadas nem como capturas. A ausência de pedras de uma cor pode tornar médias posicionais indefinidas; o pipeline preserva a dimensão e trata ausências.

A escala `zk → −z`, `xd → x`, `yp → y+6` é uma convenção adotada neste projeto e não uma equivalência validada de força entre sistemas de graduação.
