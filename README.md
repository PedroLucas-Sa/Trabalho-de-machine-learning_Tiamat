<!-- @format -->

<h1 align="center">
Tiamat — Previsão do vencedor de partidas de Go
</h1>

<p align="center">
  <i>Aprendizado de Máquina</i><br/>
  Ilum - Escola de Ciência | Campinas, 2026
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue" alt="Python 3.11 ou superior">
  <img src="https://img.shields.io/badge/Content-Machine%20Learning-purple" alt="Machine Learning">
</p>

---

# Sobre o Projeto

O projeto investiga a previsão do vencedor de partidas de Go após as primeiras 40 jogadas, utilizando algoritmos de aprendizado de máquina.

A análise utiliza uma amostra filtrada do [Joe's Go Database](https://www.pjreddie.com/projects/jgdb/), com 5.156 partidas e 24 atributos preditivos. Os atributos descrevem condições iniciais, como ranks, komi e handicap, e características da posição, como pedras presentes, capturas, grupos e liberdades.

O estudo compara cinco algoritmos de classificação: **Regressão Logística, Random Forest, Gradient Boosting, XGBoost e SVM**, tendo um **DummyClassifier** como baseline.

---

# Objetivo

- Investigar a capacidade de prever a cor vencedora a partir dos atributos do lance 40.
- Comparar diferentes algoritmos de classificação com um modelo baseline.
- Otimizar hiperparâmetros com Optuna, buscando pelo menos 100 configurações distintas completas por algoritmo.
- Utilizar validação cruzada e seleção de atributos dentro dos pipelines.
- Analisar o desempenho, os atributos utilizados e os erros dos modelos.
- Apresentar e discutir os resultados em um relatório científico.

---

# Conteúdo do Repositório

A sequência de análises está organizada nos seguintes notebooks:

| Arquivo | Conteúdo |
|---|---|
| [01_analise_exploratoria_tiamat.ipynb](01_analise_exploratoria_tiamat.ipynb) | Exploração dos dados, distribuições e correlações |
| [02_baselines_preprocessamento_tiamat.ipynb](02_baselines_preprocessamento_tiamat.ipynb) | Baselines, pré-processamento e validação cruzada |
| [03_treinamento_otimizacao_tiamat.ipynb](03_treinamento_otimizacao_tiamat.ipynb) | Treinamento e otimização dos cinco algoritmos com Optuna |
| [04_comparacao_validacao_tiamat.ipynb](04_comparacao_validacao_tiamat.ipynb) | Comparação e seleção do modelo na validação |
| [05_explicabilidade_erros_tiamat.ipynb](05_explicabilidade_erros_tiamat.ipynb) | Explicabilidade e análise dos erros |
| [06_avaliacao_final_teste_tiamat.ipynb](06_avaliacao_final_teste_tiamat.ipynb) | Avaliação final no conjunto de teste reservado |
| [07_relatorio_conclusoes_tiamat.ipynb](07_relatorio_conclusoes_tiamat.ipynb) | Relatório, discussão e conclusões |

A pasta `data/piloto_final/` reúne a base tabular e a auditoria da extração. O arquivo [dicionario_atributos.md](dicionario_atributos.md) descreve os atributos, e [requirements.txt](requirements.txt) registra as dependências necessárias.

---

# Como utilizar

Para começar, mantenha os notebooks e os arquivos de dados na estrutura do projeto. Abra um terminal na pasta dos notebooks e instale as dependências:

```bash
python -m pip install -r requirements.txt
python -m jupyter notebook
```

Em seguida:

1. Abra o notebook `01_analise_exploratoria_tiamat.ipynb` e execute as células em ordem.
2. Continue com o notebook 02 para analisar os baselines.
3. No notebook 03, execute o teste rápido e altere `EXECUTAR_OTIMIZACAO = True` para iniciar ou retomar as buscas oficiais.
4. Após concluir pelo menos 100 configurações distintas completas para cada um dos cinco algoritmos, execute os notebooks 04 e 05.
5. No notebook 06, habilite `EXECUTAR_TESTE_FINAL = True` depois de concluir a seleção e a análise de erros.
6. Complete as interpretações e o relatório no notebook 07 com os resultados observados.

---

# Observação

O projeto foi desenvolvido como parte das atividades da disciplina de Aprendizado de Máquina, no Bacharelado em Ciência e Tecnologia da Ilum Escola de Ciência, seguindo a proposta da atividade Tiamat.

A semente aleatória utilizada é **`210906`**. A amostra possui **4.612 partidas de treinamento, 270 de validação e 274 de teste**. A EDA e a otimização utilizam o treino; a validação auxilia na escolha do modelo; o teste é reservado para a avaliação final. O pré-processamento permanece dentro dos pipelines para prevenir [vazamento de dados](https://scikit-learn.org/stable/common_pitfalls.html).

As interpretações e a descrição do uso de ferramentas de IA devem acompanhar os notebooks e o relatório.

---

# Referências

- Cassar, D. R. *Criaturas Lendárias do Reino de Lumi e onde encontrá-las*. ATP-203, seção Tiamat. Material da disciplina.
- [Joe's Go Database](https://www.pjreddie.com/projects/jgdb/).
- [scikit-learn — validação cruzada](https://scikit-learn.org/stable/modules/cross_validation.html).
- [Optuna — salvamento e retomada dos estudos](https://optuna.readthedocs.io/en/stable/tutorial/20_recipes/001_rdb.html).

---

# Professor orientador

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/drcassar">
        <img src="https://avatars.githubusercontent.com/u/9871905?v=4" width="100px;" alt="Foto do Daniel no GitHub" style="border-radius:100%;"/><br>
        <b>Prof. Dr. Daniel R. Cassar</b>
      </a>
    </td>
  </tr>
</table>

---

# Autor

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/PedroLucas-Sa">
        <img
          src="https://avatars.githubusercontent.com/u/282565085?v=4&size=64"
          width="120px"
          alt="Foto do Pedro Lucas no GitHub"
          style="border-radius:50%; border:2px solid #ccc;"
        /><br>
        <b>Pedro Lucas M. S. Sá</b>
      </a>
    </td>
  </tr>
</table>
