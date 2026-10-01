/* =====================================================================
   Desafio Arquitetural: UPDATE em view com JOIN + agregacao (SQL Server)

   Solucao: trigger INSTEAD OF UPDATE acoplado a view. Ele intercepta o
   UPDATE antes do motor tentar aplica-lo na view (o que seria bloqueado
   com a Msg 4403) e roteia a gravacao para a tabela fisica correta:
       Status          -> PEDIDO   (todos os pedidos pendentes do cliente)
       Nome            -> CLIENTE
       PK / agregados  -> rejeitados (nao existem fisicamente)

   Executar no SSMS/Azure Data Studio ou: sqlcmd -S <srv> -i este_arquivo.sql
   ===================================================================== */

SET NOCOUNT ON;
GO

IF DB_ID('DesafioArquitetural') IS NOT NULL
BEGIN
    ALTER DATABASE DesafioArquitetural SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE DesafioArquitetural;
END
GO
CREATE DATABASE DesafioArquitetural;
GO
USE DesafioArquitetural;
GO

/* ---------------------------------------------------------------------
   1. Tabelas fisicas
   --------------------------------------------------------------------- */
CREATE TABLE dbo.CLIENTE (
    PK_Cli INT           NOT NULL CONSTRAINT PK_CLIENTE PRIMARY KEY,
    Nome   NVARCHAR(100) NOT NULL
);

CREATE TABLE dbo.PEDIDO (
    PK_Ped     INT           NOT NULL CONSTRAINT PK_PEDIDO PRIMARY KEY,
    FK_Cli     INT           NOT NULL CONSTRAINT FK_PEDIDO_CLIENTE REFERENCES dbo.CLIENTE (PK_Cli),
    ValorTotal DECIMAL(12,2) NOT NULL,
    Status     VARCHAR(20)   NOT NULL
        CONSTRAINT CK_PEDIDO_Status CHECK (Status IN ('Pendente', 'Cobrado', 'Pago', 'Cancelado'))
);
GO

INSERT INTO dbo.CLIENTE (PK_Cli, Nome) VALUES
    (1, N'Ana Souza'),
    (2, N'Bruno Lima'),
    (3, N'Carla Mendes'),
    (4, N'Daniel Rocha');

INSERT INTO dbo.PEDIDO (PK_Ped, FK_Cli, ValorTotal, Status) VALUES
    (101, 1, 150.00, 'Pendente'),
    (102, 1, 250.00, 'Pendente'),
    (103, 1,  80.00, 'Pago'),
    (104, 2, 500.00, 'Pendente'),
    (105, 3, 120.00, 'Pendente'),
    (106, 3, 300.00, 'Pendente'),
    (107, 3,  50.00, 'Cancelado'),
    (108, 4, 999.00, 'Pago');
GO

/* ---------------------------------------------------------------------
   2. View exigida pela diretoria (JOIN + agregacao, filtro 'Pendente')
      SCHEMABINDING impede que alguem altere PEDIDO/CLIENTE e quebre
      silenciosamente o roteamento do trigger.
   --------------------------------------------------------------------- */
CREATE VIEW dbo.vw_Clientes_Inadimplentes
WITH SCHEMABINDING
AS
SELECT  c.PK_Cli,
        c.Nome,
        p.Status,
        COUNT_BIG(*)      AS QtdPedidosPendentes,
        SUM(p.ValorTotal) AS TotalDevido
FROM    dbo.CLIENTE AS c
JOIN    dbo.PEDIDO  AS p ON p.FK_Cli = c.PK_Cli
WHERE   p.Status = 'Pendente'
GROUP BY c.PK_Cli, c.Nome, p.Status;
GO

PRINT '=== ESTADO INICIAL: vw_Clientes_Inadimplentes ===';
SELECT * FROM dbo.vw_Clientes_Inadimplentes ORDER BY PK_Cli;
GO

/* ---------------------------------------------------------------------
   3. O PROBLEMA: sem o trigger, o motor recusa o UPDATE (Msg 4403)
   --------------------------------------------------------------------- */
PRINT '=== PROBLEMA: UPDATE direto na view (ainda sem trigger) ===';
GO
UPDATE dbo.vw_Clientes_Inadimplentes SET Status = 'Cobrado' WHERE PK_Cli = 1;
GO

/* ---------------------------------------------------------------------
   4. A SOLUCAO: trigger INSTEAD OF UPDATE (interceptacao fisica)

      A linha da view nao existe em disco. Ela e uma "projecao" de N
      pedidos pendentes de um cliente. O trigger recebe:
        deleted  = linhas da view ANTES (Status = 'Pendente')
        inserted = linhas da view com os valores do SET
      e traduz cada linha agregada de volta para as linhas fisicas que a
      compoem (PEDIDO.FK_Cli = PK_Cli AND PEDIDO.Status = deleted.Status).
   --------------------------------------------------------------------- */
CREATE TRIGGER dbo.trg_vw_Clientes_Inadimplentes_IOU
ON dbo.vw_Clientes_Inadimplentes
INSTEAD OF UPDATE
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM inserted)
        RETURN;

    -- Chave e colunas agregadas nao tem linha fisica de origem.
    IF UPDATE(PK_Cli) OR UPDATE(QtdPedidosPendentes) OR UPDATE(TotalDevido)
    BEGIN
        THROW 50001, N'vw_Clientes_Inadimplentes: apenas Status e Nome podem ser alterados; PK_Cli, QtdPedidosPendentes e TotalDevido sao chave/agregados.', 1;
    END

    -- Rota 1: Status -> PEDIDO (somente os pedidos que formavam a linha da view).
    IF UPDATE(Status)
    BEGIN
        UPDATE p
           SET p.Status = i.Status
          FROM dbo.PEDIDO AS p
          JOIN deleted    AS d ON d.PK_Cli = p.FK_Cli
                              AND d.Status = p.Status
          JOIN inserted   AS i ON i.PK_Cli = d.PK_Cli;
    END

    -- Rota 2: Nome -> CLIENTE.
    IF UPDATE(Nome)
    BEGIN
        UPDATE c
           SET c.Nome = i.Nome
          FROM dbo.CLIENTE AS c
          JOIN inserted    AS i ON i.PK_Cli = c.PK_Cli;
    END
END
GO

/* ---------------------------------------------------------------------
   5. Testes
   --------------------------------------------------------------------- */
PRINT '=== TESTE 1: cobrar o cliente 1 (mesmo comando que falhou antes) ===';
UPDATE dbo.vw_Clientes_Inadimplentes SET Status = 'Cobrado' WHERE PK_Cli = 1;
SELECT PK_Ped, FK_Cli, ValorTotal, Status FROM dbo.PEDIDO WHERE FK_Cli = 1 ORDER BY PK_Ped;
GO

PRINT '=== TESTE 2: cobrar quem deve mais de 450 (filtro sobre coluna agregada) ===';
UPDATE dbo.vw_Clientes_Inadimplentes SET Status = 'Cobrado' WHERE TotalDevido > 450;
SELECT PK_Ped, FK_Cli, ValorTotal, Status FROM dbo.PEDIDO WHERE FK_Cli IN (2, 3) ORDER BY PK_Ped;
GO

PRINT '=== TESTE 3 (negativo): tentar alterar coluna agregada ===';
GO
UPDATE dbo.vw_Clientes_Inadimplentes SET TotalDevido = 0 WHERE PK_Cli = 3;
GO

PRINT '=== TESTE 4 (negativo): status invalido -> CHECK da tabela PEDIDO barra e desfaz tudo ===';
GO
UPDATE dbo.vw_Clientes_Inadimplentes SET Status = 'Perdoado' WHERE PK_Cli = 3;
GO
SELECT PK_Ped, FK_Cli, Status FROM dbo.PEDIDO WHERE FK_Cli = 3 ORDER BY PK_Ped;
GO

PRINT '=== TESTE 5: Nome e roteado para CLIENTE ===';
UPDATE dbo.vw_Clientes_Inadimplentes SET Nome = N'Carla Mendes Silva' WHERE PK_Cli = 3;
SELECT PK_Cli, Nome FROM dbo.CLIENTE WHERE PK_Cli = 3;
GO

PRINT '=== ESTADO FINAL: vw_Clientes_Inadimplentes ===';
SELECT * FROM dbo.vw_Clientes_Inadimplentes ORDER BY PK_Cli;

PRINT '=== ESTADO FINAL: PEDIDO ===';
SELECT * FROM dbo.PEDIDO ORDER BY PK_Ped;
GO
