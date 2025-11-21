# Algoritmo Genético para o Problema de Máquinas Paralelas (PMSP)

Este repositório contém uma implementação em Python de um **Algoritmo Genético (GA)** para resolver o problema de **Agendamento em Máquinas Paralelas com tempos de setup dependentes da sequência e tempos de liberação (ready times)**.

As instâncias do problema usadas nos testes podem ser obtidas no repositório:

> [https://github.com/Herysson/pmsp-instance-generator](https://github.com/Herysson/pmsp-instance-generator)
> (arquivo `instancias.zip`)

O formato dessas instâncias é JSON e já é suportado diretamente pelo código `ga_pmsp.py`.

---

## 1. Visão geral do problema

De forma simples, o problema é:

* Temos **vários jobs** (tarefas) para processar.
* Temos **várias máquinas paralelas** que podem processar esses jobs.
* Cada job:

  * tem um **tempo de processamento**;
  * só pode começar após um certo **tempo de liberação** (*ready time*);
  * ao trocar de um job para outro, existe um **tempo de setup** que depende da sequência (quem vem antes de quem).
* Queremos **distribuir e ordenar** os jobs nas máquinas para **minimizar o makespan**, isto é, o tempo em que o último job termina.

O algoritmo genético procura, de forma heurística, uma boa solução (não necessariamente ótima) para esse problema.

---

## 2. Visão geral do Algoritmo Genético

O Algoritmo Genético implementado em `ga_pmsp.py` segue a estrutura clássica:

1. **Representação da solução** como uma permutação dos jobs.
2. **Avaliação** dessa permutação, transformando-a em um cronograma em máquinas (decodificação).
3. **Evolução de uma população** de soluções ao longo de várias gerações, usando:

   * seleção por torneio,
   * crossover (recombinação),
   * mutação por troca (swap),
   * elitismo (preservar o melhor indivíduo).

A seguir, as principais funções do GA são explicadas em uma linguagem acessível, com pseudo-código quando necessário.

---

## 3. Representação da solução

Cada solução (indivíduo) é representada como:

```python
{
    "chromosome": [lista_com_jobs],
    "cost": makespan_da_solução
}
```

* `chromosome`: é uma **permutação** dos índices dos jobs, por exemplo `[3, 0, 2, 1]`.
  Essa lista indica a ordem em que os jobs serão considerados para alocação nas máquinas.
* `cost`: é o **makespan** resultante dessa solução (quanto menor, melhor).

---

## 4. Funções principais do GA

### 4.1. Leitura da instância (`load_instance`)

Função responsável por:

* Ler um arquivo `.json` de instância.
* Retornar:

  * `config`: dicionário com dados gerais da instância (ex.: número de máquinas, número de jobs).
  * `setup_matrix`: matriz de tempos de setup entre jobs.
  * `processing_times`: lista com os tempos de processamento de cada job.
  * `ready_times`: lista com os tempos de liberação de cada job.

Você não precisa alterar essa função para usar o GA, pois ela já está preparada para as instâncias geradas pelo `pmsp-instance-generator`.

---

### 4.2. Decodificação da permutação (`decode_schedule`)

**Objetivo:** transformar um cromossomo (permutação de jobs) em um cronograma em máquinas e calcular o **makespan**.

**Ideia geral:**

1. Temos `M` máquinas.

2. Para cada job na ordem definida pelo cromossomo:

   * testamos colocá-lo em cada máquina;
   * calculamos em qual máquina ele terminaria mais cedo, considerando:

     * quando a máquina estará livre,
     * o setup em relação ao último job daquela máquina,
     * o *ready time* do job.
   * escolhemos a máquina que termina esse job mais cedo.

3. No final, o **makespan** é o maior tempo de término entre todas as máquinas.

**Pseudo-código simplificado:**

```text
para cada máquina m:
    tempo_livre[m] = 0
    ultimo_job[m] = nenhum

para cada job em order (cromossomo):
    melhor_máquina = nenhum
    melhor_tempo_conclusão = infinito

    para cada máquina m:
        t = tempo_livre[m]
        se existe ultimo_job[m]:
            t = t + setup(ultimo_job[m], job)

        inicio = max(t, ready_time[job])
        conclusao = inicio + processing_time[job]

        se conclusao < melhor_tempo_conclusão:
            melhor_máquina = m
            melhor_tempo_conclusão = conclusao

    alocar job na melhor_máquina
    tempo_livre[melhor_máquina] = melhor_tempo_conclusão
    ultimo_job[melhor_máquina] = job

makespan = máximo dos tempos_livres[m] entre todas as máquinas
```

Essa função retorna:

* o **makespan**, e
* uma estrutura com a lista de jobs alocados em cada máquina, com seus tempos de início e fim.

---

### 4.3. Avaliação da solução (`evaluate`)

Função: `evaluate(order, n_machines, processing_times, ready_times, setup_matrix)`

* Recebe um cromossomo (permutação de jobs).
* Chama `decode_schedule` para construir o cronograma.
* Retorna apenas o **makespan** (custo da solução).

Em código:

```python
makespan, _ = decode_schedule(...)
return makespan
```

---

### 4.4. Criação de um indivíduo (`create_individual`)

Função: `create_individual(...)`

**O que faz:**

1. Cria uma permutação aleatória de todos os jobs:

   ```python
   chromosome = list(range(n_jobs))
   random.shuffle(chromosome)
   ```

2. Calcula o custo (makespan) usando `evaluate`.

3. Retorna um dicionário com o cromossomo e o custo.

Essa função é usada para gerar a **população inicial** do GA.

---

### 4.5. Seleção por torneio (`tournament_selection`)

Função: `tournament_selection(population, k=3)`

**Ideia**: escolher bons pais para a reprodução.

Passos:

1. Sorteia **k indivíduos** da população.
2. Compara o custo (makespan) desses k indivíduos.
3. Retorna o melhor (menor makespan) como “pai”.

Pseudo-código:

```text
selecionar k indivíduos aleatórios da população
retornar o indivíduo com menor custo entre eles
```

O parâmetro `k` controla a **pressão seletiva**:

* `k` pequeno → mais diversidade.
* `k` grande → maior chance de sempre escolher os melhores (menos diversidade).

---

### 4.6. Crossover de ordem (`order_crossover`)

Função: `order_crossover(parent1, parent2)`

Essa função combina dois cromossomos (pais) para gerar um novo cromossomo (filho), preservando a ideia de **permutação** (sem jobs repetidos).

**Passos principais:**

1. Sorteia duas posições `a` e `b` dentro da lista.
2. Copia o segmento `parent1[a:b]` para o filho.
3. Percorre `parent2` na ordem original e vai preenchendo os espaços vazios do filho com jobs que **ainda não apareceram**.

Pseudo-código:

```text
criar filho com todas as posições vazias
copiar o segmento parent1[a:b] no filho

pos = b
para cada gene g em parent2 na ordem:
    se g não está no filho:
        colocar g na próxima posição vazia (ciclamente nas posições do filho)
```

Isso gera um cromossomo que mistura informações dos dois pais, mantendo a estrutura de permutação.

---

### 4.7. Mutação por troca (`mutate_swap`)

Função: `mutate_swap(chromosome, mutation_rate=0.02)`

**O que faz:**

* Percorre o cromossomo posição a posição.
* Para cada posição, com probabilidade `mutation_rate`, troca o gene atual com outro gene em uma posição aleatória.

Pseudo-código:

```text
para cada índice i no cromossomo:
    se random() < mutation_rate:
        escolher índice j aleatório
        trocar chromosome[i] com chromosome[j]
```

Isso introduz pequenas variações na solução, ajudando a explorar novas regiões do espaço de busca.

---

### 4.8. Algoritmo Genético principal (`genetic_algorithm`)

Assinatura:

```python
genetic_algorithm(
    n_jobs,
    n_machines,
    processing_times,
    ready_times,
    setup_matrix,
    pop_size=50,
    generations=200,
    crossover_rate=0.9,
    mutation_rate=0.02,
    tournament_k=3,
)
```

**Passos:**

1. **Inicialização da população**

   * Cria `pop_size` indivíduos aleatórios com `create_individual`.
   * Acha o melhor indivíduo inicial.
   * Guarda o melhor custo em `history` (geração 0).

2. **Laço de gerações**
   Para cada geração:

   * **Elitismo**:

     * Encontra o melhor indivíduo da população atual (elite).
     * Garante que ele entre na nova população.

   * **Criação dos novos indivíduos**:

     * Enquanto a nova população não tiver `pop_size` indivíduos:

       1. Seleciona `parent1` e `parent2` usando `tournament_selection`.
       2. Com probabilidade `crossover_rate`, aplica `order_crossover` para gerar dois filhos.
          Caso contrário, apenas copia os cromossomos dos pais.
       3. Aplica `mutate_swap` em cada filho.
       4. Avalia o custo (makespan) de cada filho com `evaluate` e adiciona à nova população.

   * Substitui a população antiga pela nova.

   * Atualiza o melhor indivíduo global (se algum filho for melhor).

   * Guarda o melhor custo da geração na lista `history`.

   * A cada 10 gerações, imprime o melhor makespan atual.

3. **Retorno**

   * A função retorna um dicionário com:

     ```python
     {
       "best": melhor_individuo,        # cromossomo e custo
       "history": lista_de_melhores_custos_por_geração
     }
     ```

---

## 5. Parâmetros ajustáveis do GA

Dentro da função `run_scenario_from_file`, o GA é chamado assim:

```python
result = genetic_algorithm(
    n_jobs=n_jobs,
    n_machines=n_machines,
    processing_times=processing_times,
    ready_times=ready_times,
    setup_matrix=setup_matrix,
    pop_size=50,
    generations=200,
    crossover_rate=0.9,
    mutation_rate=0.02,
    tournament_k=3,
)
```

Você pode alterar esses valores para controlar o comportamento do algoritmo:

| Parâmetro        | Significado                                                               | Efeito prático                                                               |
| ---------------- | ------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `pop_size`       | Tamanho da população (quantos indivíduos por geração).                    | Populações maiores aumentam diversidade, mas deixam a execução mais lenta.   |
| `generations`    | Número de gerações (iterações do GA).                                     | Mais gerações aumentam o tempo e a chance de encontrar soluções melhores.    |
| `crossover_rate` | Probabilidade de aplicar o crossover em um par de pais.                   | Valores altos (ex.: 0.8–0.9) geram mais recombinação entre soluções.         |
| `mutation_rate`  | Probabilidade de mutar cada posição do cromossomo (swap).                 | Controla a exploração local; se muito alto, o cromossomo pode ficar caótico. |
| `tournament_k`   | Tamanho do torneio na seleção (quantos indivíduos competem para ser pai). | Quanto maior, mais “forte” a seleção (tende a escolher sempre os melhores).  |

Os valores fornecidos no exemplo (`pop_size=50`, `generations=200`, etc.) funcionam como um bom ponto de partida.

---

## 6. Cálculo do Limite Inferior (DDLB)

O código também implementa um **limite inferior** baseado no conceito de *Data Dependent Lower Bound (DDLB)*:

```python
ddlb = calcular_ddlb(config, processing_times, setup_matrix, ready_times)
```

A ideia é, de forma resumida:

1. Para cada job `i`, encontrar o menor setup de saída `δᵢ` (mínimo de `setup[i][j]` para todos os `j ≠ i`).
2. Somar os tempos de processamento e esses `δᵢ`, ajustando para o fato de que algumas máquinas terminam sem setup no final.
3. Calcular:

   * um limite de **carga de trabalho** (distribuição de processamento + setup pelas máquinas),
   * e um limite de **caminho crítico** usando `ready_time`, tempo de processamento e `δᵢ`.
4. O DDLB é o **máximo** entre esses dois limites.

Na saída, o programa mostra a **razão**:

```text
Razão MS/DDLB: X.XXXX
```

Quanto mais próximo de 1, melhor a qualidade relativa do makespan encontrado.

---

## 7. Como usar o código

### 7.1. Pré-requisitos

* **Python 3.8+** (recomendado 3.10 ou superior).
* Sistema operacional:

  * qualquer (Windows, Linux, macOS) para rodar o `.py`;
  * o `.bat` é específico para **Windows**.

O código usa apenas bibliotecas da **biblioteca padrão** do Python:

* `json`, `random`, `time`, `argparse`, `typing`.

Não é necessário instalar pacotes adicionais via `pip`.

---

### 7.2. Estrutura sugerida de pastas

Exemplo de organização:

```text
.
├── ga_pmsp.py           # Implementação do Algoritmo Genético
├── run_solver_GA.bat    # Script em lote (Windows) para rodar múltiplos cenários
├── resultados_GA.txt    # Exemplo de arquivo com resultados obtidos
└── instancias/          # Pasta com instâncias extraídas de instancias.zip
    ├── HHHHHHH/
    │   ├── HHHHHHH_1.json
    │   ├── HHHHHHH_2.json
    │   └── ...
    ├── HHHHHHL/
    │   ├── HHHHHHL_1.json
    │   └── ...
    └── ...
```

---

### 7.3. Obtendo e organizando as instâncias

1. Acesse o repositório:
   [https://github.com/Herysson/pmsp-instance-generator](https://github.com/Herysson/pmsp-instance-generator)
2. Baixe o arquivo `instancias.zip`.
3. Extraia o conteúdo para a pasta `instancias/` (ou outra de sua preferência).
4. Verifique que os arquivos `.json` seguem o formato esperado pelo `ga_pmsp.py`.

---

### 7.4. Executando o solver para uma única instância

No terminal (cmd / PowerShell / bash), na pasta onde está o `ga_pmsp.py`, execute:

```bash
python ga_pmsp.py caminho/para/instancia/HHHHHHH_1.json
```

Exemplo em Windows:

```bash
python ga_pmsp.py instancias\HHHHHHH\HHHHHHH_1.json
```

A saída mostrará:

* Cabeçalho com o nome do arquivo.
* Progresso do GA (melhor makespan em algumas gerações).
* Solução final:

  * sequência de jobs em cada máquina,
  * tempo final de cada máquina.
* Métricas de avaliação:

  * Makespan final,
  * Limite inferior (DDLB),
  * Razão MS/DDLB,
  * Melhoria de makespan em relação à solução inicial,
  * Tempo de execução do GA.

---

### 7.5. Executando múltiplos cenários com o `.bat`

O arquivo `run_solver_GA.bat` (para Windows) pode ser usado para:

* Rodar o solver para **várias instâncias em sequência**.
* Salvar toda a saída em um arquivo de log, como `resultados_GA.txt`.

Passos:

1. Abra o arquivo `run_solver_GA.bat` em um editor de texto.
2. Ajuste:

   * o caminho do Python (se necessário),
   * a pasta das instâncias,
   * o nome do arquivo de saída (log), se quiser personalizar.
3. Execute o `.bat` com duplo clique ou no terminal:

   ```bash
   run_solver_GA.bat
   ```

Ao final, o arquivo `resultados_GA.txt` conterá os resultados de todas as instâncias processadas (makespan, DDLB, tempo, etc.).

---

## 8. Reprodutibilidade

No final de `ga_pmsp.py`, a semente do gerador de números aleatórios é fixada:

```python
if __name__ == "__main__":
    random.seed(42)
    ...
```

Isso significa que:

* Executando o código com a mesma instância e mesmos parâmetros, os resultados serão **reprodutíveis** (iguais em execuções diferentes).
* Se você quiser variar os resultados, pode comentar ou alterar essa linha.

---

## 9. Resultados de exemplo

O arquivo `resultados_GA.txt` contém um conjunto de resultados gerados pelo solver, incluindo:

* nome de cada instância,
* evolução do melhor makespan ao longo das gerações,
* solução final (jobs por máquina),
* métricas de avaliação e tempo de execução.

Isso pode ser usado como **referência** para:

* comparar novas configurações de parâmetros,
* validar mudanças no código,
* ou como base para análise em trabalhos acadêmicos.

