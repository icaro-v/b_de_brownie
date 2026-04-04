# B de Brownie 🍫

Aplicativo desktop em **PyQt5 + SQLite** para controlar ingredientes, produtos, vendas e despesas de uma pequena produção de brownies. Tudo roda localmente, sem servidores.

## O que dá pra fazer
- Cadastrar produtos e ingredientes com preço base e custo por unidade.
- Registrar vendas e despesas (com categorias e observações) e ver o resumo automático de receita, despesas e lucro.
- Manter tipos de despesa com valores padrão para preenchimento rápido.
- Divisão fixa do lucro em 3 partes iguais já calculada na tela.
- Editar com duplo clique nas tabelas e excluir via menu de contexto ou tecla Delete.

## Requisitos
- Python 3.10+ (testado em Windows).
- Dependências: `SQLAlchemy>=1.4`, `PyQt5>=5.15` (lista em `dependencias.txt`).

## Instalação rápida
```bash
python -m venv .venv
.venv\Scripts\activate    # no Windows (ou source .venv/bin/activate no Linux/macOS)
pip install -r dependencias.txt
```

## Banco de dados
- Usa SQLite em `b_de_brownie.db` (ignorado no Git).
- Para criar do zero (ou recriar):  
  - `python init_db.py` — cria se não existir.  
  - `python init_db.py --force` — apaga o arquivo atual e recria (perde dados).
- O app também cria as tabelas automaticamente ao iniciar, caso o arquivo não exista.

## Executar
```bash
python app.py
```
A interface é carregada a partir de `ui_mainwindow.ui` e estilizada por `tema.qss`.

## Estrutura rápida
- `app.py`: janela principal e lógica da UI.
- `database.py`: engine SQLite, modelos SQLAlchemy e `Base.metadata.create_all`.
- `init_db.py`: utilitário para criar/recriar o banco.
- `ui_mainwindow.ui`: layout Qt Designer.
- `tema.qss`: estilos da interface.
- `dependencias.txt`: lista mínima de pacotes.

## Licença
MIT — veja `LICENSE`.
