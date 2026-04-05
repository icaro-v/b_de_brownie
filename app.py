import sys
from datetime import date
from pathlib import Path
from PyQt5 import QtWidgets, uic, QtGui, QtCore
from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QMessageBox

from database import (
    obter_sessao,
    Ingrediente,
    Produto,
    Venda,
    Despesa,
    TipoDespesa,
    DivisaoLucro,
    DB_PATH,
)

BASE_DIR = Path(__file__).resolve().parent
CAMINHO_LOGO = BASE_DIR / 'logo.png'
PARTE_IGUAL = 100 / 3


def formatar_moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class JanelaPrincipal(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(str(BASE_DIR / 'ui_mainwindow.ui'), self)

        self.sessao = obter_sessao()
        self.id_produto_edicao = None
        self.id_ingrediente_edicao = None
        self.id_despesa_edicao = None
        self.id_venda_edicao = None
        self.id_tipo_despesa_edicao = None

        self._garantir_divisao_fixa()
        self._semear_produtos()

        self._conectar_sinais()
        self._inicializar_campos()
        self._carregar_logo()
        self.recarregar_tudo()

    # region inicialização
    def _conectar_sinais(self):
        self.botaoAdicionarIngrediente.clicked.connect(self.adicionar_ingrediente)
        self.botaoRegistrarVenda.clicked.connect(self.registrar_venda)
        self.botaoAdicionarDespesa.clicked.connect(self.adicionar_despesa)
        self.botaoSalvarProduto.clicked.connect(self.adicionar_produto)
        self.botaoSalvarTipoDespesa.clicked.connect(self.adicionar_tipo_despesa)
        self.botaoSalvarDivisao.clicked.connect(self.mostrar_divisao_fixa)

        self.comboProdutoVenda.currentIndexChanged.connect(self.ao_selecionar_produto)
        self.comboProdutoVenda.editTextChanged.connect(self.ao_digitar_produto)

        # duplo clique nas tabelas para carregar no formulário
        self.tabelaProdutos.cellDoubleClicked.connect(self.carregar_produto_para_edicao)
        self.tabelaIngredientes.cellDoubleClicked.connect(self.carregar_ingrediente_para_edicao)
        self.tabelaDespesas.cellDoubleClicked.connect(self.carregar_despesa_para_edicao)
        self.tabelaVendas.cellDoubleClicked.connect(self.carregar_venda_para_edicao)
        self.tabelaTiposDespesa.cellDoubleClicked.connect(self.carregar_tipo_despesa_para_edicao)

        # despesas dependentes de categoria
        self.comboCategoriaDespesa.currentTextChanged.connect(self.atualizar_itens_despesa_por_categoria)
        self.comboItemDespesa.currentIndexChanged.connect(self.ao_selecionar_item_despesa)

        # menus de contexto e tecla Delete para exclusão
        self._tabelas_excluir = (
            self.tabelaProdutos,
            self.tabelaIngredientes,
            self.tabelaDespesas,
            self.tabelaVendas,
            self.tabelaTiposDespesa,
        )
        self._mapa_tipo_tabela = {
            self.tabelaProdutos: 'produto',
            self.tabelaIngredientes: 'ingrediente',
            self.tabelaDespesas: 'despesa',
            self.tabelaVendas: 'venda',
            self.tabelaTiposDespesa: 'tipo_despesa',
        }
        for tabela in self._tabelas_excluir:
            tabela.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            tabela.customContextMenuRequested.connect(lambda pos, t=tabela: self._mostrar_menu_excluir(t, pos))
            tabela.installEventFilter(self)

    def _inicializar_campos(self):
        hoje = QDate.currentDate()
        self.dataVendaInput.setDate(hoje)
        self.dataDespesaInput.setDate(hoje)

        for spin in (self.spinMinhaParte, self.spinNamoradaParte, self.spinNegocioParte):
            spin.setValue(PARTE_IGUAL)
            spin.setReadOnly(True)
            spin.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.botaoSalvarDivisao.setEnabled(False)
        self.botaoSalvarDivisao.setVisible(False)
        self.labelSomaDivisao.setText("Divisão fixa: 33,3% para cada")

        # tabelas somente leitura
        for tabela in (self.tabelaProdutos, self.tabelaIngredientes, self.tabelaDespesas, self.tabelaVendas, self.tabelaRecentes):
            tabela.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        # iniciar dependências de despesas
        self.atualizar_itens_despesa_por_categoria(self.comboCategoriaDespesa.currentText())

    def eventFilter(self, obj, event):
        if obj in getattr(self, "_tabelas_excluir", []) and event.type() == QtCore.QEvent.KeyPress:
            if event.key() == QtCore.Qt.Key_Delete:
                self._excluir_registro_tabela(obj)
                return True
        return super().eventFilter(obj, event)

    def _carregar_logo(self):
        if CAMINHO_LOGO.exists():
            pix = QtGui.QPixmap(str(CAMINHO_LOGO)).scaledToWidth(160, QtCore.Qt.SmoothTransformation)
            self.labelLogo.setPixmap(pix)
            self.labelLogo.setText('')

    def _garantir_divisao_fixa(self):
        divisao = self.sessao.query(DivisaoLucro).first()
        if not divisao:
            divisao = DivisaoLucro(parte_voce=PARTE_IGUAL, parte_namorada=PARTE_IGUAL, parte_negocio=PARTE_IGUAL)
            self.sessao.add(divisao)
        else:
            divisao.parte_voce = divisao.parte_namorada = divisao.parte_negocio = PARTE_IGUAL
        self.sessao.commit()

    def _semear_produtos(self):
        if self.sessao.query(Produto).count() == 0:
            iniciais = [
                ('Brownie Tradicional', 'Tradicional'),
                ('Recheado Leite Ninho', 'Recheado'),
                ('Recheado Ovomaltine', 'Recheado'),
                ('Recheado Nutella', 'Recheado'),
                ('Recheado Doce de Leite', 'Recheado'),
            ]
            for nome, categoria in iniciais:
                self.sessao.add(Produto(nome=nome, categoria=categoria, preco_base=0.0))
            self.sessao.commit()
    # endregion

    # region ações
    def adicionar_ingrediente(self):
        nome = self.campoNomeIngrediente.text().strip()
        unidade = self.comboUnidadeIngrediente.currentText()
        custo = float(self.spinCustoIngrediente.value())
        observacao = self.campoObsIngrediente.text().strip()
        if not nome:
            QMessageBox.warning(self, 'Campo obrigatório', 'Preencha o nome do ingrediente.')
            return
        if self.id_ingrediente_edicao:
            ingrediente = self.sessao.query(Ingrediente).get(self.id_ingrediente_edicao)
            if not ingrediente:
                QMessageBox.warning(self, 'Não encontrado', 'Ingrediente não existe mais.')
                return
            ingrediente.nome = nome
            ingrediente.unidade = unidade
            ingrediente.custo_por_unidade = custo
            ingrediente.observacao = observacao
        else:
            existente = self.sessao.query(Ingrediente).filter_by(nome=nome).first()
            if existente:
                QMessageBox.information(self, 'Duplicado', 'Já existe um ingrediente com esse nome.')
                return
            ingrediente = Ingrediente(nome=nome, unidade=unidade, custo_por_unidade=custo, observacao=observacao)
            self.sessao.add(ingrediente)
        self.sessao.commit()
        self.campoNomeIngrediente.clear()
        self.campoObsIngrediente.clear()
        self.spinCustoIngrediente.setValue(0)
        self.id_ingrediente_edicao = None
        self.botaoAdicionarIngrediente.setText("Adicionar ingrediente")
        self.recarregar_ingredientes()

    def registrar_venda(self):
        produto_nome = self.comboProdutoVenda.currentText().strip() or 'Brownie'
        quantidade = int(self.spinQtdVenda.value())
        preco_unit = float(self.spinPrecoVenda.value())
        if preco_unit <= 0:
            QMessageBox.warning(self, 'Preço', 'Defina o preço unitário.')
            return
        total = quantidade * preco_unit
        qdate = self.dataVendaInput.date()
        dt = date(qdate.year(), qdate.month(), qdate.day())
        if self.id_venda_edicao:
            venda = self.sessao.query(Venda).get(self.id_venda_edicao)
            if not venda:
                QMessageBox.warning(self, 'Não encontrado', 'Venda não existe mais.')
                return
            venda.data = dt
            venda.produto = produto_nome
            venda.quantidade = quantidade
            venda.preco_unitario = preco_unit
            venda.total = total
        else:
            venda = Venda(data=dt, produto=produto_nome, quantidade=quantidade, preco_unitario=preco_unit, total=total)
            self.sessao.add(venda)

        produto = self.sessao.query(Produto).filter_by(nome=produto_nome).first()
        if not produto:
            produto = Produto(nome=produto_nome, categoria='Outro', preco_base=preco_unit)
            self.sessao.add(produto)
        elif preco_unit > 0 and abs(produto.preco_base - preco_unit) > 0.001:
            produto.preco_base = preco_unit

        self.sessao.commit()
        self.comboProdutoVenda.setCurrentIndex(-1)
        self.spinQtdVenda.setValue(1)
        self.spinPrecoVenda.setValue(0)
        self.id_venda_edicao = None
        self.botaoRegistrarVenda.setText("Registrar venda")
        self.recarregar_vendas()
        self.recarregar_produtos()
        self.recarregar_resumo()

    def adicionar_despesa(self):
        categoria = self.comboCategoriaDespesa.currentText()
        observacao = self.campoObservacaoDespesa.text().strip()
        descricao = ''
        valor = float(self.spinValorDespesa.value())
        if valor <= 0:
            QMessageBox.warning(self, 'Valor', 'Informe um valor maior que zero.')
            return
        item_sel = self.comboItemDespesa.currentText().strip() if self.comboItemDespesa.isEnabled() else ''
        if categoria == 'Ingredientes':
            if item_sel:
                descricao = item_sel
            else:
                QMessageBox.warning(self, 'Selecione um ingrediente', 'Escolha um ingrediente para registrar a despesa.')
                return
        else:
            # se houver tipos cadastrados na categoria e nenhum selecionado, pede seleção
            if self.comboItemDespesa.count() > 0 and not item_sel:
                QMessageBox.warning(self, 'Selecione um tipo', 'Escolha um tipo de despesa para registrar.')
                return
            if item_sel:
                descricao = item_sel
        if not descricao:
            descricao = categoria
        qdate = self.dataDespesaInput.date()
        dt = date(qdate.year(), qdate.month(), qdate.day())
        if self.id_despesa_edicao:
            despesa = self.sessao.query(Despesa).get(self.id_despesa_edicao)
            if not despesa:
                QMessageBox.warning(self, 'Não encontrado', 'Despesa não existe mais.')
                return
            despesa.data = dt
            despesa.categoria = categoria
            despesa.descricao = descricao
            despesa.valor = valor
            despesa.observacao = observacao
        else:
            despesa = Despesa(data=dt, categoria=categoria, descricao=descricao, valor=valor, observacao=observacao)
            self.sessao.add(despesa)
        self.sessao.commit()
        self.campoObservacaoDespesa.clear()
        self.spinValorDespesa.setValue(0)
        self.id_despesa_edicao = None
        self.botaoAdicionarDespesa.setText("Adicionar despesa")
        self.recarregar_despesas()
        self.recarregar_resumo()

    def adicionar_produto(self):
        nome = self.campoNomeProduto.text().strip()
        categoria = self.comboCategoriaProduto.currentText()
        preco = float(self.spinPrecoProduto.value())
        if not nome:
            QMessageBox.warning(self, 'Campo obrigatório', 'Preencha o nome do produto.')
            return
        if self.id_produto_edicao:
            produto = self.sessao.query(Produto).get(self.id_produto_edicao)
            if not produto:
                QMessageBox.warning(self, 'Não encontrado', 'Produto não existe mais.')
                return
            produto.nome = nome
            produto.categoria = categoria
            produto.preco_base = preco
        else:
            existente = self.sessao.query(Produto).filter_by(nome=nome).first()
            if existente:
                QMessageBox.information(self, 'Duplicado', 'Já existe um produto com esse nome.')
                return
            produto = Produto(nome=nome, categoria=categoria, preco_base=preco)
            self.sessao.add(produto)
        self.sessao.commit()
        self.campoNomeProduto.clear()
        self.spinPrecoProduto.setValue(0)
        self.id_produto_edicao = None
        self.botaoSalvarProduto.setText("Salvar produto")
        self.recarregar_produtos()

    def adicionar_tipo_despesa(self):
        nome = self.campoNomeTipoDespesa.text().strip()
        categoria = self.comboCategoriaTipoDespesa.currentText()
        valor_padrao = float(self.spinValorTipoDespesa.value())
        if not nome:
            QMessageBox.warning(self, 'Campo obrigatório', 'Preencha o nome do tipo de despesa.')
            return
        if self.id_tipo_despesa_edicao:
            td = self.sessao.query(TipoDespesa).get(self.id_tipo_despesa_edicao)
            if not td:
                QMessageBox.warning(self, 'Não encontrado', 'Tipo de despesa não existe mais.')
                return
            td.nome = nome
            td.categoria = categoria
            td.valor_padrao = valor_padrao
        else:
            existente = self.sessao.query(TipoDespesa).filter_by(nome=nome).first()
            if existente:
                QMessageBox.information(self, 'Duplicado', 'Já existe um tipo de despesa com esse nome.')
                return
            td = TipoDespesa(nome=nome, categoria=categoria, valor_padrao=valor_padrao)
            self.sessao.add(td)
        self.sessao.commit()
        self.campoNomeTipoDespesa.clear()
        self.spinValorTipoDespesa.setValue(0)
        self.id_tipo_despesa_edicao = None
        self.botaoSalvarTipoDespesa.setText("Salvar tipo")
        self.recarregar_tipos_despesa()

    def mostrar_divisao_fixa(self):
        QMessageBox.information(self, 'Divisão fixa', 'A divisão é fixa: 3 partes iguais (33,3% cada).')
    # endregion

    # region recarregar
    def recarregar_tudo(self):
        self.recarregar_ingredientes()
        self.recarregar_tipos_despesa()
        self.recarregar_produtos()
        self.recarregar_vendas()
        self.recarregar_despesas()
        self.recarregar_resumo()

    def recarregar_ingredientes(self):
        dados = self.sessao.query(Ingrediente).order_by(Ingrediente.nome).all()
        tabela = self.tabelaIngredientes
        tabela.setRowCount(len(dados))
        tabela.setColumnCount(4)
        tabela.setHorizontalHeaderLabels(['Nome', 'Unidade', 'Custo/un', 'Obs'])
        for linha, ing in enumerate(dados):
            item_nome = QtWidgets.QTableWidgetItem(ing.nome)
            item_nome.setData(QtCore.Qt.UserRole, ing.id)
            tabela.setItem(linha, 0, item_nome)
            tabela.setItem(linha, 1, QtWidgets.QTableWidgetItem(ing.unidade))
            tabela.setItem(linha, 2, QtWidgets.QTableWidgetItem(formatar_moeda(ing.custo_por_unidade)))
            tabela.setItem(linha, 3, QtWidgets.QTableWidgetItem(ing.observacao or ''))
        tabela.resizeColumnsToContents()
        # atualizar combo de itens de despesa se categoria for ingredientes
        if self.comboCategoriaDespesa.currentText() == 'Ingredientes':
            self.atualizar_itens_despesa_por_categoria('Ingredientes')

    def recarregar_tipos_despesa(self):
        dados = self.sessao.query(TipoDespesa).order_by(TipoDespesa.categoria, TipoDespesa.nome).all()
        tabela = self.tabelaTiposDespesa
        tabela.setRowCount(len(dados))
        tabela.setColumnCount(3)
        tabela.setHorizontalHeaderLabels(['Nome', 'Categoria', 'Valor padrão'])
        for linha, td in enumerate(dados):
            item_nome = QtWidgets.QTableWidgetItem(td.nome)
            item_nome.setData(QtCore.Qt.UserRole, td.id)
            tabela.setItem(linha, 0, item_nome)
            tabela.setItem(linha, 1, QtWidgets.QTableWidgetItem(td.categoria))
            tabela.setItem(linha, 2, QtWidgets.QTableWidgetItem(formatar_moeda(td.valor_padrao)))
        tabela.resizeColumnsToContents()
        if self.comboCategoriaDespesa.currentText() != 'Ingredientes':
            self.atualizar_itens_despesa_por_categoria(self.comboCategoriaDespesa.currentText())

    def recarregar_produtos(self):
        dados = self.sessao.query(Produto).order_by(Produto.categoria, Produto.nome).all()
        tabela = self.tabelaProdutos
        tabela.setRowCount(len(dados))
        tabela.setColumnCount(3)
        tabela.setHorizontalHeaderLabels(['Nome', 'Categoria', 'Preço padrão'])
        self.comboProdutoVenda.blockSignals(True)
        self.comboProdutoVenda.clear()
        for linha, prod in enumerate(dados):
            item_nome = QtWidgets.QTableWidgetItem(prod.nome)
            item_nome.setData(QtCore.Qt.UserRole, prod.id)
            tabela.setItem(linha, 0, item_nome)
            tabela.setItem(linha, 1, QtWidgets.QTableWidgetItem(prod.categoria))
            tabela.setItem(linha, 2, QtWidgets.QTableWidgetItem(formatar_moeda(prod.preco_base)))
            self.comboProdutoVenda.addItem(prod.nome, prod.preco_base)
        self.comboProdutoVenda.setEditable(True)
        self.comboProdutoVenda.setCurrentIndex(-1)
        self.comboProdutoVenda.blockSignals(False)
        tabela.resizeColumnsToContents()

    def recarregar_vendas(self):
        dados = self.sessao.query(Venda).order_by(Venda.data.desc()).all()
        tabela = self.tabelaVendas
        tabela.setRowCount(len(dados))
        tabela.setColumnCount(5)
        tabela.setHorizontalHeaderLabels(['Data', 'Produto', 'Qtd', 'Preço unit', 'Total'])
        for linha, venda in enumerate(dados):
            item_data = QtWidgets.QTableWidgetItem(venda.data.strftime('%d/%m/%Y'))
            item_data.setData(QtCore.Qt.UserRole, venda.id)
            tabela.setItem(linha, 0, item_data)
            tabela.setItem(linha, 1, QtWidgets.QTableWidgetItem(venda.produto))
            tabela.setItem(linha, 2, QtWidgets.QTableWidgetItem(str(venda.quantidade)))
            tabela.setItem(linha, 3, QtWidgets.QTableWidgetItem(formatar_moeda(venda.preco_unitario)))
            tabela.setItem(linha, 4, QtWidgets.QTableWidgetItem(formatar_moeda(venda.total)))
        tabela.resizeColumnsToContents()

    def recarregar_despesas(self):
        dados = self.sessao.query(Despesa).order_by(Despesa.data.desc()).all()
        tabela = self.tabelaDespesas
        tabela.setRowCount(len(dados))
        tabela.setColumnCount(5)
        tabela.setHorizontalHeaderLabels(['Data', 'Categoria', 'Item', 'Observação', 'Valor'])
        for linha, desp in enumerate(dados):
            item_data = QtWidgets.QTableWidgetItem(desp.data.strftime('%d/%m/%Y'))
            item_data.setData(QtCore.Qt.UserRole, desp.id)
            tabela.setItem(linha, 0, item_data)
            tabela.setItem(linha, 1, QtWidgets.QTableWidgetItem(desp.categoria))
            tabela.setItem(linha, 2, QtWidgets.QTableWidgetItem(desp.descricao))
            tabela.setItem(linha, 3, QtWidgets.QTableWidgetItem(desp.observacao or ''))
            tabela.setItem(linha, 4, QtWidgets.QTableWidgetItem(formatar_moeda(desp.valor)))
        tabela.resizeColumnsToContents()

    def recarregar_resumo(self):
        total_vendas = sum(v.total for v in self.sessao.query(Venda).all())
        total_despesas = sum(d.valor for d in self.sessao.query(Despesa).all())
        lucro = total_vendas - total_despesas
        self.labelReceitaTotal.setText(formatar_moeda(total_vendas))
        self.labelDespesasTotais.setText(formatar_moeda(total_despesas))
        self.labelLucroLiquido.setText(formatar_moeda(lucro))
        self.labelResumoReceitaValor.setText(formatar_moeda(total_vendas))
        self.labelResumoDespesasValor.setText(formatar_moeda(total_despesas))
        self.labelResumoLucroValor.setText(formatar_moeda(lucro))
        self.atualizar_divisao_lucro(lucro)
        self.preencher_tabela_recentes()
    # endregion

    # region auxiliares
    def preencher_tabela_recentes(self):
        vendas = [(v.data, 'Venda', f"{v.produto} (x{v.quantidade})", v.total) for v in self.sessao.query(Venda).all()]
        despesas = [(d.data, 'Despesa', d.descricao, -d.valor) for d in self.sessao.query(Despesa).all()]
        linhas = sorted(vendas + despesas, key=lambda x: x[0], reverse=True)[:10]
        tabela = self.tabelaRecentes
        tabela.setRowCount(len(linhas))
        tabela.setColumnCount(4)
        tabela.setHorizontalHeaderLabels(['Data', 'Tipo', 'Descrição', 'Valor'])
        for i, (dt, tipo, desc, val) in enumerate(linhas):
            tabela.setItem(i, 0, QtWidgets.QTableWidgetItem(dt.strftime('%d/%m/%Y')))
            tabela.setItem(i, 1, QtWidgets.QTableWidgetItem(tipo))
            tabela.setItem(i, 2, QtWidgets.QTableWidgetItem(desc))
            tabela.setItem(i, 3, QtWidgets.QTableWidgetItem(formatar_moeda(val)))
        tabela.resizeColumnsToContents()

    def atualizar_divisao_lucro(self, lucro):
        parte = lucro / 3
        self.labelValorMinhaParte.setText(formatar_moeda(parte))
        self.labelValorNamorada.setText(formatar_moeda(parte))
        self.labelValorNegocio.setText(formatar_moeda(parte))

    def ao_selecionar_produto(self, indice: int):
        if indice < 0:
            return
        preco = self.comboProdutoVenda.itemData(indice)
        if preco is not None and preco > 0:
            self.spinPrecoVenda.setValue(float(preco))

    def ao_digitar_produto(self, texto: str):
        if not texto:
            self.spinPrecoVenda.setValue(0)

    def atualizar_itens_despesa_por_categoria(self, categoria: str):
        if categoria == 'Ingredientes':
            itens = [ing.nome for ing in self.sessao.query(Ingrediente).order_by(Ingrediente.nome).all()]
            self.comboItemDespesa.blockSignals(True)
            self.comboItemDespesa.clear()
            for nome in itens:
                self.comboItemDespesa.addItem(nome, None)
            self.comboItemDespesa.setEnabled(True)
            if itens:
                self.comboItemDespesa.setCurrentIndex(0)
                self.campoObservacaoDespesa.setPlaceholderText('Observação opcional')
            else:
                self.campoObservacaoDespesa.setPlaceholderText('')
            self.comboItemDespesa.blockSignals(False)
            if itens:
                self.ao_selecionar_item_despesa(self.comboItemDespesa.currentIndex())
        else:
            itens_td = self.sessao.query(TipoDespesa).filter_by(categoria=categoria).order_by(TipoDespesa.nome).all()
            self.comboItemDespesa.blockSignals(True)
            self.comboItemDespesa.clear()
            if itens_td:
                for td in itens_td:
                    self.comboItemDespesa.addItem(td.nome, td.valor_padrao)
                self.comboItemDespesa.setEnabled(True)
                self.comboItemDespesa.setCurrentIndex(0)
                self.campoObservacaoDespesa.setPlaceholderText('Observação opcional')
            else:
                self.comboItemDespesa.setEnabled(False)
                self.campoObservacaoDespesa.setPlaceholderText('')
            self.comboItemDespesa.blockSignals(False)
            if itens_td:
                self.ao_selecionar_item_despesa(self.comboItemDespesa.currentIndex())

    def ao_selecionar_item_despesa(self, indice: int):
        if not self.comboItemDespesa.isEnabled() or indice < 0:
            return
        item = self.comboItemDespesa.itemText(indice)
        valor_padrao = self.comboItemDespesa.itemData(indice)
        if valor_padrao is not None and valor_padrao > 0:
            self.spinValorDespesa.setValue(float(valor_padrao))
        # Preenche descrição automaticamente com o item escolhido
        self.campoObservacaoDespesa.setPlaceholderText('Observação opcional')

    # menus de contexto e exclusão
    def _mostrar_menu_excluir(self, tabela: QtWidgets.QTableWidget, pos):
        if not tabela.selectedIndexes():
            return
        menu = QtWidgets.QMenu(self)
        ac_excluir = menu.addAction("Excluir")
        acao = menu.exec_(tabela.viewport().mapToGlobal(pos))
        if acao == ac_excluir:
            self._excluir_registro_tabela(tabela)

    def _excluir_registro_tabela(self, tabela: QtWidgets.QTableWidget):
        tipo = self._mapa_tipo_tabela.get(tabela)
        if not tipo:
            return
        linha = tabela.currentRow()
        if linha < 0:
            return
        item_id = tabela.item(linha, 0)
        if not item_id:
            return
        registro_id = item_id.data(QtCore.Qt.UserRole)
        if registro_id is None:
            return
        if QMessageBox.question(self, "Confirmar exclusão", "Deseja excluir este registro?") != QMessageBox.Yes:
            return

        if tipo == 'produto':
            obj = self.sessao.query(Produto).get(registro_id)
        elif tipo == 'ingrediente':
            obj = self.sessao.query(Ingrediente).get(registro_id)
        elif tipo == 'despesa':
            obj = self.sessao.query(Despesa).get(registro_id)
        elif tipo == 'venda':
            obj = self.sessao.query(Venda).get(registro_id)
        elif tipo == 'tipo_despesa':
            obj = self.sessao.query(TipoDespesa).get(registro_id)
        else:
            obj = None
        if obj:
            self.sessao.delete(obj)
            self.sessao.commit()

        # limpar estados de edição se necessário
        if tipo == 'produto' and self.id_produto_edicao == registro_id:
            self.id_produto_edicao = None
            self.campoNomeProduto.clear()
            self.spinPrecoProduto.setValue(0)
            self.botaoSalvarProduto.setText("Salvar produto")
        if tipo == 'ingrediente' and self.id_ingrediente_edicao == registro_id:
            self.id_ingrediente_edicao = None
            self.campoNomeIngrediente.clear()
            self.spinCustoIngrediente.setValue(0)
            self.campoObsIngrediente.clear()
            self.botaoAdicionarIngrediente.setText("Adicionar ingrediente")
        if tipo == 'despesa' and self.id_despesa_edicao == registro_id:
            self.id_despesa_edicao = None
            self.campoObservacaoDespesa.clear()
            self.spinValorDespesa.setValue(0)
            self.botaoAdicionarDespesa.setText("Adicionar despesa")
        if tipo == 'venda' and self.id_venda_edicao == registro_id:
            self.id_venda_edicao = None
            self.comboProdutoVenda.setCurrentIndex(-1)
            self.spinQtdVenda.setValue(1)
            self.spinPrecoVenda.setValue(0)
            self.botaoRegistrarVenda.setText("Registrar venda")
        if tipo == 'tipo_despesa' and self.id_tipo_despesa_edicao == registro_id:
            self.id_tipo_despesa_edicao = None
            self.campoNomeTipoDespesa.clear()
            self.botaoSalvarTipoDespesa.setText("Salvar tipo")

        # recarregar visões
        if tipo in ('produto',):
            self.recarregar_produtos()
        if tipo in ('ingrediente',):
            self.recarregar_ingredientes()
        if tipo in ('despesa',):
            self.recarregar_despesas()
        if tipo in ('venda',):
            self.recarregar_vendas()
        if tipo in ('tipo_despesa',):
            self.recarregar_tipos_despesa()
        # resumo depende de vendas e despesas
        if tipo in ('despesa', 'venda'):
            self.recarregar_resumo()

    # region carregar para edição via duplo clique
    def carregar_produto_para_edicao(self, linha: int, coluna: int):
        item = self.tabelaProdutos.item(linha, 0)
        if not item:
            return
        prod_id = item.data(QtCore.Qt.UserRole)
        prod = self.sessao.query(Produto).get(prod_id)
        if not prod:
            return
        self.id_produto_edicao = prod.id
        self.campoNomeProduto.setText(prod.nome)
        index_cat = self.comboCategoriaProduto.findText(prod.categoria)
        self.comboCategoriaProduto.setCurrentIndex(index_cat if index_cat >= 0 else 0)
        self.spinPrecoProduto.setValue(prod.preco_base)
        self.botaoSalvarProduto.setText("Atualizar produto")

    def carregar_ingrediente_para_edicao(self, linha: int, coluna: int):
        item = self.tabelaIngredientes.item(linha, 0)
        if not item:
            return
        ing_id = item.data(QtCore.Qt.UserRole)
        ing = self.sessao.query(Ingrediente).get(ing_id)
        if not ing:
            return
        self.id_ingrediente_edicao = ing.id
        self.campoNomeIngrediente.setText(ing.nome)
        idx_un = self.comboUnidadeIngrediente.findText(ing.unidade)
        self.comboUnidadeIngrediente.setCurrentIndex(idx_un if idx_un >= 0 else 0)
        self.spinCustoIngrediente.setValue(ing.custo_por_unidade)
        self.campoObsIngrediente.setText(ing.observacao or '')
        self.botaoAdicionarIngrediente.setText("Atualizar ingrediente")

    def carregar_despesa_para_edicao(self, linha: int, coluna: int):
        item = self.tabelaDespesas.item(linha, 0)
        if not item:
            return
        desp_id = item.data(QtCore.Qt.UserRole)
        desp = self.sessao.query(Despesa).get(desp_id)
        if not desp:
            return
        self.id_despesa_edicao = desp.id
        self.dataDespesaInput.setDate(QDate(desp.data.year, desp.data.month, desp.data.day))
        idx_cat = self.comboCategoriaDespesa.findText(desp.categoria)
        self.comboCategoriaDespesa.setCurrentIndex(idx_cat if idx_cat >= 0 else 0)
        # atualizar itens e selecionar se for ingrediente
        if desp.categoria == 'Ingredientes':
            self.atualizar_itens_despesa_por_categoria('Ingredientes')
            idx_item = self.comboItemDespesa.findText(desp.descricao)
            if idx_item >= 0:
                self.comboItemDespesa.setCurrentIndex(idx_item)
        else:
            self.atualizar_itens_despesa_por_categoria(desp.categoria)
        self.campoObservacaoDespesa.setText(desp.observacao or '')
        self.spinValorDespesa.setValue(desp.valor)
        self.botaoAdicionarDespesa.setText("Atualizar despesa")

    def carregar_venda_para_edicao(self, linha: int, coluna: int):
        item = self.tabelaVendas.item(linha, 0)
        if not item:
            return
        venda_id = item.data(QtCore.Qt.UserRole)
        venda = self.sessao.query(Venda).get(venda_id)
        if not venda:
            return
        self.id_venda_edicao = venda.id
        self.dataVendaInput.setDate(QDate(venda.data.year, venda.data.month, venda.data.day))
        self.comboProdutoVenda.setEditText(venda.produto)
        self.spinQtdVenda.setValue(venda.quantidade)
        self.spinPrecoVenda.setValue(venda.preco_unitario)
        self.botaoRegistrarVenda.setText("Atualizar venda")
    # endregion

    def carregar_tipo_despesa_para_edicao(self, linha: int, coluna: int):
        item = self.tabelaTiposDespesa.item(linha, 0)
        if not item:
            return
        tipo_id = item.data(QtCore.Qt.UserRole)
        td = self.sessao.query(TipoDespesa).get(tipo_id)
        if not td:
            return
        self.id_tipo_despesa_edicao = td.id
        self.campoNomeTipoDespesa.setText(td.nome)
        idx_cat = self.comboCategoriaTipoDespesa.findText(td.categoria)
        self.comboCategoriaTipoDespesa.setCurrentIndex(idx_cat if idx_cat >= 0 else 0)
        self.spinValorTipoDespesa.setValue(td.valor_padrao)
        self.botaoSalvarTipoDespesa.setText("Atualizar tipo")
    # endregion


def main():
    app = QtWidgets.QApplication(sys.argv)
    with open(BASE_DIR / 'tema.qss', 'r', encoding='utf-8') as f:
        app.setStyleSheet(f.read())
    janela = JanelaPrincipal()
    janela.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
