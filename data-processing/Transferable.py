import pandas as pd
from pathlib import Path

import networkx as nx

import matplotlib.pyplot as plt
from networkx.drawing.nx_pydot import graphviz_layout


def transferable_check(GROUP_NUMBER, df):
    values = []
    for i in range(len(df)):
        values.append(df.iloc[i].tolist())

    flagsToBinary = []
    groupNumber = [str(i) for i in range(GROUP_NUMBER)]

    # flag bit를 & 연산하여 동일한 cpu flag를 가진 그룹을 추출.
    for value in values:
        binary_string = ''.join(str(i) for i in value)
        binary_number = int(binary_string, 2)
        flagsToBinary.append(binary_number)

    matrix = []
    for binary in flagsToBinary:
        row = []
        for i in range(len(flagsToBinary)):
            if (binary & flagsToBinary[i] == binary):
                row.append(True)
            else:
                row.append(False)
        matrix.append(row)

    transferable = pd.DataFrame(matrix, columns=groupNumber)
    transferable.index = range(2, len(transferable)+2)
    transferable = transferable.groupby(groupNumber).size()

    for i in range(len(matrix)):
        print(f'Transferable group{i+2} to ', end='')
        for j in range(len(matrix[i])):
            if (matrix[i][j]):
                print(j + 2, end=', ')
        print()

    return matrix


def Digraph(GROUP_NUMBER, df):
    matrix = transferable_check(GROUP_NUMBER, df)

    # 방향성 그래프 생성
    G = nx.DiGraph()

    # 노드 추가
    for i in range(GROUP_NUMBER):
        G.add_node(i + 2)
        for j in range(len(matrix[i])):
            # 집합 관계 성립
            if (matrix[i][j]):
                # 본인을 가리키지 않도록 함.
                if (i == j):
                    continue
                # 엣지 추가
                G.add_edge(i + 2, j + 2)

    # Transitive reduction 적용
    G = nx.transitive_reduction(G)

    pos = graphviz_layout(G, prog='dot')
    nx.draw(G, pos, with_labels=True, node_color='lightblue', edge_color='gray',
            node_size=2000, font_size=20, font_weight='bold', arrowsize=30)
    plt.show()
