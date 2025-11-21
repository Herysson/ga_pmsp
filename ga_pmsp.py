import json
import random
import time
import argparse
from typing import List, Tuple, Dict, Any


# -------------------------------------------------------
# 1. Leitura da instância
# -------------------------------------------------------

def load_instance(path: str):
    """
    Lê o arquivo .json no formato do gerador e retorna:
    - config: dicionário de configuração
    - setup_matrix: matriz de tempos de setup (lista de listas)
    - processing_times: lista de tempos de processamento p[i]
    - ready_times: lista de ready times r[i]
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    config = data["configuracao"]
    setup_matrix = data["matriz_setup"]
    processing_times = data["tempos_processamento"]
    ready_times = data["ready_times"]

    return config, setup_matrix, processing_times, ready_times


# -------------------------------------------------------
# 2. Decodificar um cromossomo em um cronograma e calcular o makespan
# -------------------------------------------------------

def decode_schedule(order: List[int],
                    n_machines: int,
                    processing_times: List[float],
                    ready_times: List[float],
                    setup_matrix: List[List[float]]) -> Tuple[float, List[List[Tuple[int, float, float]]]]:
    """
    Transforma uma permutação de jobs em um cronograma em máquinas.

    Retorna:
    - makespan
    - schedule: lista de máquinas; cada máquina é uma lista de tuplas (job, start, end)
    """
    # Tempo em que cada máquina fica livre
    machine_time = [0.0 for _ in range(n_machines)]
    # Último job executado em cada máquina
    last_job = [None for _ in range(n_machines)]
    # Para guardar quando cada job termina (para calcular o makespan)
    completion_times = [0.0 for _ in range(len(order))]
    # Para guardar o cronograma de fato
    schedule: List[List[Tuple[int, float, float]]] = [[] for _ in range(n_machines)]

    for job in order:
        best_machine = None
        best_completion = float("inf")
        best_start = 0.0

        # Testa colocar este job em cada máquina
        for m in range(n_machines):
            t = machine_time[m]

            # Adiciona tempo de setup se houver job anterior na máquina
            if last_job[m] is not None:
                s = setup_matrix[last_job[m]][job]
                if s is None:  # diagonal vem como null no JSON
                    s = 0.0
                t = t + s

            # Job só pode começar depois do ready time
            start = max(t, ready_times[job])
            completion = start + processing_times[job]

            if completion < best_completion:
                best_completion = completion
                best_machine = m
                best_start = start

        # Atribui o job à melhor máquina encontrada
        machine_time[best_machine] = best_completion
        last_job[best_machine] = job
        completion_times[job] = best_completion
        schedule[best_machine].append((job, best_start, best_completion))

    makespan = max(completion_times)
    return makespan, schedule


# -------------------------------------------------------
# 3. Funções para o Algoritmo Genético
# -------------------------------------------------------

def evaluate(order: List[int],
             n_machines: int,
             processing_times: List[float],
             ready_times: List[float],
             setup_matrix: List[List[float]]) -> float:
    """
    Calcula o custo (makespan) de uma solução.
    """
    makespan, _ = decode_schedule(order, n_machines, processing_times, ready_times, setup_matrix)
    return makespan


def create_individual(n_jobs: int,
                      n_machines: int,
                      processing_times: List[float],
                      ready_times: List[float],
                      setup_matrix: List[List[float]]) -> Dict[str, Any]:
    """
    Cria um indivíduo aleatório:
    - chromosome: permutação de 0..n_jobs-1
    - cost: makespan da solução
    """
    chromosome = list(range(n_jobs))
    random.shuffle(chromosome)
    cost = evaluate(chromosome, n_machines, processing_times, ready_times, setup_matrix)
    return {"chromosome": chromosome, "cost": cost}


def tournament_selection(population: List[Dict[str, Any]], k: int = 3) -> Dict[str, Any]:
    """
    Seleção por torneio:
    - sorteia k indivíduos da população
    - retorna o que tiver menor custo (makespan)
    """
    candidates = random.sample(population, k)
    winner = min(candidates, key=lambda ind: ind["cost"])
    return winner


def order_crossover(parent1: List[int], parent2: List[int]) -> List[int]:
    """
    Crossover do tipo Order Crossover (OX) para permutações.
    Retorna um filho.
    """
    size = len(parent1)
    a, b = sorted(random.sample(range(size), 2))

    # Inicializa filho com None
    child = [None] * size

    # Copia fatia do primeiro pai
    child[a:b] = parent1[a:b]

    # Preenche o resto na ordem do segundo pai
    pos = b
    for gene in parent2[b:] + parent2[:b]:
        if gene not in child:
            if pos >= size:
                pos = 0
            child[pos] = gene
            pos += 1

    return child


def mutate_swap(chromosome: List[int], mutation_rate: float = 0.02):
    """
    Mutação por troca (swap):
    para cada posição, com probabilidade mutation_rate, troca com outra posição aleatória.
    """
    size = len(chromosome)
    for i in range(size):
        if random.random() < mutation_rate:
            j = random.randrange(size)
            chromosome[i], chromosome[j] = chromosome[j], chromosome[i]


def genetic_algorithm(n_jobs: int,
                      n_machines: int,
                      processing_times: List[float],
                      ready_times: List[float],
                      setup_matrix: List[List[float]],
                      pop_size: int = 30,
                      generations: int = 50,
                      crossover_rate: float = 0.9,
                      mutation_rate: float = 0.02,
                      tournament_k: int = 3) -> Dict[str, Any]:
    """
    Implementação simples de um Algoritmo Genético para o PMSP.

    Retorna:
      {
        "best": melhor_individuo,
        "history": lista_com_melhor_makespan_por_geração (inclui geração 0)
      }
    """
    # População inicial
    population = [
        create_individual(n_jobs, n_machines, processing_times, ready_times, setup_matrix)
        for _ in range(pop_size)
    ]

    # Melhor da população inicial
    best = min(population, key=lambda ind: ind["cost"])
    best_history = [best["cost"]]  # geração 0 (solução inicial)

    for gen in range(generations):
        new_population: List[Dict[str, Any]] = []

        # Elitismo
        elite = min(population, key=lambda ind: ind["cost"])
        if elite["cost"] < best["cost"]:
            best = elite
        new_population.append({
            "chromosome": elite["chromosome"][:],
            "cost": elite["cost"]
        })

        # Gera o restante da nova população
        while len(new_population) < pop_size:
            parent1 = tournament_selection(population, tournament_k)["chromosome"]
            parent2 = tournament_selection(population, tournament_k)["chromosome"]

            if random.random() < crossover_rate:
                child1 = order_crossover(parent1, parent2)
                child2 = order_crossover(parent2, parent1)
            else:
                child1 = parent1[:]
                child2 = parent2[:]

            mutate_swap(child1, mutation_rate)
            mutate_swap(child2, mutation_rate)

            cost1 = evaluate(child1, n_machines, processing_times, ready_times, setup_matrix)
            new_population.append({"chromosome": child1, "cost": cost1})

            if len(new_population) < pop_size:
                cost2 = evaluate(child2, n_machines, processing_times, ready_times, setup_matrix)
                new_population.append({"chromosome": child2, "cost": cost2})

        population = new_population

        # Melhor desta geração (para o histórico)
        best_gen = min(population, key=lambda ind: ind["cost"])
        best_history.append(best_gen["cost"])

        if (gen + 1) % 10 == 0:
            print(f"Geração {gen + 1}: melhor makespan = {best['cost']:.2f}")

    return {"best": best, "history": best_history}


# -------------------------------------------------------
# 4. Calcular Limite Inferior
# -------------------------------------------------------

def calcular_ddlb(config, processing_times, setup_matrix, ready_times):
    """
    Calcula o Data Dependent Lower Bound (DDLB) corrigido.

    Ideia:
    - Para cada job i, δ_i = menor setup saindo de i para qualquer j != i.
    - Em qualquer agenda com m máquinas, n_jobs - m jobs pagarão setup de saída.
    - O setup total mínimo é: sum(δ_i) - soma dos m maiores δ_i.
    - Limite de carga = (sum p_i + setup_total_min) / m
    - Limite de caminho crítico = max_i (r_i + p_i + δ_i)
    - DDLB = max(limite_carga_trabalho, limite_caminho_critico)
    """
    n_jobs = config['n_jobs']
    n_machines = config['n_maquinas']

    # 1) Calcula δ_i = menor setup saindo de i
    deltas = []
    for i in range(n_jobs):
        min_setup_i = min(
            setup_matrix[i][j]
            for j in range(n_jobs)
            if j != i and setup_matrix[i][j] is not None
        )
        deltas.append(min_setup_i)

    # 2) Soma dos tempos de processamento e dos δ_i
    soma_p = sum(processing_times)
    soma_deltas = sum(deltas)

    # 3) Setup total mínimo: tira os m maiores δ_i
    deltas_ordenados = sorted(deltas, reverse=True)
    soma_maiores = sum(deltas_ordenados[:n_machines])
    setup_total_minimo = soma_deltas - soma_maiores

    limite_carga_trabalho = (soma_p + setup_total_minimo) / n_machines

    # 4) Limite de caminho crítico
    limite_caminho_critico = 0.0
    for i in range(n_jobs):
        caminho_i = ready_times[i] + processing_times[i] + deltas[i]
        if caminho_i > limite_caminho_critico:
            limite_caminho_critico = caminho_i

    ddlb = max(limite_carga_trabalho, limite_caminho_critico)
    return ddlb


# -------------------------------------------------------
# 5. Exemplo de uso
# -------------------------------------------------------
# -------------------------------------------------------
# 5. Orquestração e Execução Principal (estilo ls_pmsp)
# -------------------------------------------------------

def run_scenario_from_file(file_path: str):
    """
    Orquestra o processo: carregar instância, rodar GA e exibir resultados
    em um formato parecido com o ls_pmsp.py.
    """
    print("=" * 50)
    print(f"EXECUTANDO CENÁRIO DO ARQUIVO: {file_path}")
    print("=" * 50)

    # --- Carregar instância ---
    try:
        config, setup_matrix, processing_times, ready_times = load_instance(file_path)
    except FileNotFoundError:
        print(f"ERRO: O arquivo '{file_path}' não foi encontrado.")
        return
    except Exception as e:
        print(f"ERRO ao carregar ou processar o arquivo: {e}")
        return

    n_machines = config["n_maquinas"]
    n_jobs = config["n_jobs"]
    scenario_code = config.get("codigo_cenario", "Cenário Desconhecido")

    # --- Rodar GA ---
    print("\n[FASE 1: APLICANDO ALGORITMO GENÉTICO]")

    start_time = time.time()
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
    end_time = time.time()
    tempo_ga = end_time - start_time

    best_individual = result["best"]
    history = result["history"]

    # Melhor makespan final
    ms_final = best_individual["cost"]

    # Makespan inicial (melhor da população inicial, geração 0)
    ms_inicial = history[0]
    melhoria_ms = ms_inicial - ms_final

    # Quantidade de iterações (gerações efetivas)
    q_iteracoes = len(history) - 1  # history inclui geração 0

    # --- Decodifica o melhor cromossomo em cronograma ---
    best_makespan, best_schedule = decode_schedule(
        best_individual["chromosome"],
        n_machines,
        processing_times,
        ready_times,
        setup_matrix,
    )

    # --- Calcula o DDLB ---
    ddlb = calcular_ddlb(config, processing_times, setup_matrix, ready_times)
    razao_ms_ddlb = ms_final / ddlb if ddlb > 0 else float("inf")

    # --- Exibir resultados finais (estilo ls_pmsp) ---
    print("\n" + "=" * 50)
    print(f"RESULTADO FINAL PARA {scenario_code}")
    print("=" * 50)

    print("--- Solução do Algoritmo Genético ---")
    for m, jobs_on_machine in enumerate(best_schedule, start=1):
        seq = [job for (job, start, end) in jobs_on_machine]
        tempo_m = jobs_on_machine[-1][2] if jobs_on_machine else 0.0
        print(f"Máquina {m}: Seq={seq}, Tempo={tempo_m:.0f}")

    print("\n--- Métricas de Avaliação ---")
    print(f"Makespan Final (MS): {ms_final:.2f}")
    print(f"Limite Inferior (DDLB): {ddlb:.2f}")
    print(f"Razão MS/DDLB: {razao_ms_ddlb:.4f}")
    print(f"Melhoria de Makespan sobre a solução inicial: {melhoria_ms:.2f}")
    print(f"Quantidade de iterações (gerações) realizadas: {q_iteracoes}")
    print(f"Tempo de execução do GA: {tempo_ga*1000:.2f} ms")
    print("\n")


if __name__ == "__main__":
    random.seed(42)

    parser = argparse.ArgumentParser(
        description="Resolve o PMSP com Algoritmo Genético a partir de um arquivo de instância JSON."
    )
    parser.add_argument(
        "caminho_arquivo",
        type=str,
        help="Caminho para o arquivo .json da instância do problema."
    )

    args = parser.parse_args()
    run_scenario_from_file(args.caminho_arquivo)
