# Desafio Arquitetural: UPDATE em view com JOIN + agregação

## Resposta curta

O objeto é um **trigger `INSTEAD OF UPDATE`** acoplado à `vw_Clientes_Inadimplentes`.

Ele intercepta o comando antes que o SQL Server tente aplicá-lo à view, o que o motor recusaria com a Msg 4403. No lugar disso, executa um `UPDATE` explícito na tabela física `PEDIDO`.

Script completo e executável: [`vw_clientes_inadimplentes_instead_of.sql`](vw_clientes_inadimplentes_instead_of.sql)

## Por que o motor bloqueia

Uma linha de `vw_Clientes_Inadimplentes` **não existe em disco**. Ela é o resultado de um `GROUP BY` que reúne *N* pedidos pendentes de um cliente em uma linha só. Quando chega `SET Status = 'Cobrado'`, o motor não sabe sozinho quais linhas físicas devem mudar, e as colunas `SUM`/`COUNT` não têm origem física nenhuma. Por isso ele aborta:

```
Msg 4403: Cannot update the view or function 'dbo.vw_Clientes_Inadimplentes'
because it contains aggregates, or a DISTINCT or GROUP BY clause ...
```

## Arquitetura do roteamento

```
 Equipe de Cobrança
        │  UPDATE vw_Clientes_Inadimplentes SET Status = 'Cobrado' WHERE ...
        ▼
 ┌───────────────────────────────┐
 │ vw_Clientes_Inadimplentes     │  (JOIN + GROUP BY: não atualizável)
 │  └─ trg ... INSTEAD OF UPDATE │  ◄── interceptação física
 └──────────────┬────────────────┘
                │  pseudo-tabelas:
                │   deleted  = linhas da view ANTES (Status = 'Pendente')
                │   inserted = linhas da view com os valores do SET
                ▼
     ┌────────── roteamento por coluna ──────────┐
     │ Status            → UPDATE PEDIDO         │  FK_Cli = PK_Cli AND Status = deleted.Status
     │ Nome              → UPDATE CLIENTE        │  PK_Cli = PK_Cli
     │ PK_Cli, Qtd, Total→ THROW 50001           │  chave/agregados: sem dono físico
     └───────────────────────────────────────────┘
```

Pontos de projeto:

1. **Desagregação pela chave do `GROUP BY`.** Cada linha de `inserted`/`deleted` é identificada por `PK_Cli`. O trigger "abre" a linha agregada juntando `PEDIDO.FK_Cli = PK_Cli`.
2. **Mesmo predicado da view.** O join usa `PEDIDO.Status = deleted.Status` (`'Pendente'`). Assim, só os pedidos que de fato compunham a linha são alterados; pedidos `Pago` e `Cancelado` do mesmo cliente ficam intactos.
3. **O `WHERE` do usuário continua valendo**, inclusive sobre coluna agregada (`WHERE TotalDevido > 450`), porque o SQL Server já entrega em `inserted`/`deleted` apenas as linhas da view que atendem ao filtro.
4. **Colunas sem origem física são rejeitadas** com `THROW`, em vez de serem ignoradas em silêncio.
5. **Atomicidade.** O trigger roda na mesma transação do `UPDATE`. Se a gravação física falhar (ex.: `CHECK` de `Status`), tudo é desfeito.
6. **`WITH SCHEMABINDING` na view** impede que alterações em `CLIENTE`/`PEDIDO` quebrem o roteamento sem aviso.

## Resultados (SQL Server 2022, execução real do script)

**Estado inicial da view**

| PK_Cli | Nome | Status | QtdPedidosPendentes | TotalDevido |
|---|---|---|---|---|
| 1 | Ana Souza | Pendente | 2 | 400.00 |
| 2 | Bruno Lima | Pendente | 1 | 500.00 |
| 3 | Carla Mendes | Pendente | 2 | 420.00 |

**Problema: `UPDATE` sem trigger**

```
Msg 4403, Level 16, State 1
Cannot update the view or function 'dbo.vw_Clientes_Inadimplentes' because it contains
aggregates, or a DISTINCT or GROUP BY clause, or PIVOT or UNPIVOT operator.
```

**Teste 1: `SET Status = 'Cobrado' WHERE PK_Cli = 1`** (o mesmo comando, agora com o trigger)

| PK_Ped | FK_Cli | ValorTotal | Status |
|---|---|---|---|
| 101 | 1 | 150.00 | **Cobrado** |
| 102 | 1 | 250.00 | **Cobrado** |
| 103 | 1 | 80.00 | Pago *(intacto)* |

**Teste 2: `SET Status = 'Cobrado' WHERE TotalDevido > 450`** (filtro sobre agregado)

| PK_Ped | FK_Cli | ValorTotal | Status |
|---|---|---|---|
| 104 | 2 | 500.00 | **Cobrado** |
| 105 | 3 | 120.00 | Pendente *(420 < 450)* |
| 106 | 3 | 300.00 | Pendente |
| 107 | 3 | 50.00 | Cancelado |

**Teste 3: `SET TotalDevido = 0`** (rejeitado pelo trigger)

```
Msg 50001, Level 16, State 1, Procedure trg_vw_Clientes_Inadimplentes_IOU
vw_Clientes_Inadimplentes: apenas Status e Nome podem ser alterados; PK_Cli,
QtdPedidosPendentes e TotalDevido sao chave/agregados.
```

**Teste 4: `SET Status = 'Perdoado'`** (o `CHECK` da tabela física barra e a transação é desfeita; os pedidos 105/106 continuam `Pendente`)

```
Msg 547, Level 16, State 1, Procedure trg_vw_Clientes_Inadimplentes_IOU
The UPDATE statement conflicted with the CHECK constraint "CK_PEDIDO_Status".
```

**Teste 5: `SET Nome = 'Carla Mendes Silva' WHERE PK_Cli = 3`**: o nome é roteado para `CLIENTE`.

**Estado final**

| PK_Cli | Nome | Status | QtdPedidosPendentes | TotalDevido |
|---|---|---|---|---|
| 3 | Carla Mendes Silva | Pendente | 2 | 420.00 |

| PK_Ped | FK_Cli | ValorTotal | Status |
|---|---|---|---|
| 101 | 1 | 150.00 | Cobrado |
| 102 | 1 | 250.00 | Cobrado |
| 103 | 1 | 80.00 | Pago |
| 104 | 2 | 500.00 | Cobrado |
| 105 | 3 | 120.00 | Pendente |
| 106 | 3 | 300.00 | Pendente |
| 107 | 3 | 50.00 | Cancelado |
| 108 | 4 | 999.00 | Pago |

Os clientes cobrados saem da view automaticamente: deixaram de ter pedidos `Pendente`, que é exatamente o filtro da view.
