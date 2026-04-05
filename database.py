from datetime import date
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, Float, Date
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = Path(__file__).resolve().parent
CAMINHO_DB = BASE_DIR / 'b_de_brownie.db'
URL_DB = f'sqlite:///{CAMINHO_DB}'
engine = create_engine(URL_DB, echo=False)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

class Ingrediente(Base):
    __tablename__ = 'ingredientes'

    id = Column(Integer, primary_key=True)
    nome = Column(String, unique=True, nullable=False)
    unidade = Column(String, default='g')
    custo_por_unidade = Column(Float, default=0.0)
    observacao = Column(String, default='')


class Produto(Base):
    __tablename__ = 'produtos'

    id = Column(Integer, primary_key=True)
    nome = Column(String, unique=True, nullable=False)
    categoria = Column(String, default='Tradicional')
    preco_base = Column(Float, default=0.0)


class Venda(Base):
    __tablename__ = 'vendas'

    id = Column(Integer, primary_key=True)
    data = Column(Date, default=date.today)
    produto = Column(String, nullable=False)
    quantidade = Column(Integer, default=1)
    preco_unitario = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    observacao = Column(String, default='')


class Despesa(Base):
    __tablename__ = 'despesas'

    id = Column(Integer, primary_key=True)
    data = Column(Date, default=date.today)
    categoria = Column(String, default='Outros')
    descricao = Column(String, default='')
    valor = Column(Float, default=0.0)
    observacao = Column(String, default='')


class TipoDespesa(Base):
    __tablename__ = 'tipos_despesa'

    id = Column(Integer, primary_key=True)
    nome = Column(String, unique=True, nullable=False)
    categoria = Column(String, default='Outros')
    valor_padrao = Column(Float, default=0.0)


class DivisaoLucro(Base):
    __tablename__ = 'divisao_lucro'

    id = Column(Integer, primary_key=True)
    parte_voce = Column(Float, default=33.3)
    parte_namorada = Column(Float, default=33.3)
    parte_negocio = Column(Float, default=33.3)


Base.metadata.create_all(engine)


def obter_sessao():
    return SessionLocal()

# compatibilidade antiga
get_session = obter_sessao
DB_PATH = CAMINHO_DB


if __name__ == '__main__':
    Base.metadata.create_all(engine)
    print(f'Tabelas garantidas em {CAMINHO_DB}')
