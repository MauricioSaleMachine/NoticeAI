# Import das bibliotecas
import os
import sys
import google.generativeai as genai
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QSlider, QComboBox, 
                             QTextEdit, QScrollArea, QGroupBox, QSizePolicy, QMessageBox,
                             QInputDialog, QProgressBar)
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal
from PyQt5.QtGui import QDesktopServices, QFont
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json

#Iniciando a apresentação das classes

class NewsWorker(QThread): 
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, query, num_news, period):
        super().__init__()
        self.query = query
        self.num_news = num_news
        self.period = period

    def run(self):
        try:
            news = []
            for i in range(self.num_news):
                self.progress.emit(int((i+1)/self.num_news * 100))
                
                # Simulação de busca de notícias (substitua por uma API real)
                news_item = {
                    'title': f"Notícia {i+1} sobre {self.query}",
                    'url': f"https://exemplo.com/noticia-{i+1}",
                    'summary': f"Resumo gerado sobre os últimos desenvolvimentos em {self.query}.",
                    'date': (datetime.now() - timedelta(days=i)).strftime('%d/%m/%Y'),
                    'content': f"Conteúdo detalhado da notícia {i+1} sobre {self.query}..."
                }
                news.append(news_item)
            
            self.finished.emit(news)
        except Exception as e:
            self.error.emit(f"Erro ao buscar notícias: {str(e)}")

class GeminiWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, model, prompt):
        super().__init__()
        self.model = model
        self.prompt = prompt

    def run(self):
        try:
            response = self.model.generate_content(self.prompt)
            self.finished.emit(response.text)
        except Exception as e:
            self.error.emit(f"Erro ao gerar resumo: {str(e)}")

class NewsApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pesquisador de Notícias com Gemini AI")
        self.setGeometry(100, 100, 1000, 800)
        
        # Configuração inicial do Gemini
        self.gemini_available = False
        self.configure_gemini()
        
        # Widget central
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Layout principal
        self.main_layout = QHBoxLayout()
        self.central_widget.setLayout(self.main_layout)
        
        # Configura a interface
        self.setup_ui()
    
    def configure_gemini(self):
        # Tenta obter a API key
        api_key = os.environ.get('GEMINI_API_KEY')
        
        if not api_key:
            api_key, ok = QInputDialog.getText(
                self, 
                "Configuração da API",
                "Digite sua chave da API Gemini:",
                QLineEdit.Normal
            )
            if not ok or not api_key:
                QMessageBox.warning(self, "Aviso", 
                                  "A funcionalidade Gemini não estará disponível sem uma chave válida.")
                return
        
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
            self.gemini_available = True
        except Exception as e:
            QMessageBox.critical(self, "Erro", 
                                f"Falha ao configurar Gemini: {str(e)}")
    
    def setup_ui(self):
        # Sidebar
        self.setup_sidebar()
        
        # Área principal
        self.setup_main_area()
    
    def setup_sidebar(self):
        sidebar = QGroupBox("Configurações de Pesquisa")
        sidebar.setFixedWidth(300)
        layout = QVBoxLayout()
        
        # Campo de pesquisa
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Digite o tema da pesquisa...")
        
        # Número de notícias
        self.num_news_slider = QSlider(Qt.Horizontal)
        self.num_news_slider.setRange(1, 10)
        self.num_news_slider.setValue(3)
        self.num_news_label = QLabel("3 notícias")
        
        # Período
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Últimos 7 dias", "Último mês", "Último ano", "Qualquer período"])
        
        # Botão de pesquisa
        self.search_btn = QPushButton("Pesquisar Notícias")
        self.search_btn.clicked.connect(self.start_news_search)
        self.search_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        
        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        # Adiciona widgets ao layout
        layout.addWidget(QLabel("Tema da Pesquisa:"))
        layout.addWidget(self.query_input)
        layout.addWidget(QLabel("Número de Notícias:"))
        layout.addWidget(self.num_news_slider)
        layout.addWidget(self.num_news_label)
        layout.addWidget(QLabel("Período:"))
        layout.addWidget(self.period_combo)
        layout.addWidget(self.search_btn)
        layout.addWidget(self.progress_bar)
        layout.addStretch()
        
        sidebar.setLayout(layout)
        self.main_layout.addWidget(sidebar)
        
        # Conecta o slider ao label
        self.num_news_slider.valueChanged.connect(
            lambda: self.num_news_label.setText(f"{self.num_news_slider.value()} notícias"))
    
    def setup_main_area(self):
        main_area = QWidget()
        layout = QVBoxLayout()
        
        # Título
        title = QLabel("📰 Resumo de Notícias com Gemini AI")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        
        # Área de notícias
        self.news_scroll = QScrollArea()
        self.news_scroll.setWidgetResizable(True)
        self.news_container = QWidget()
        self.news_layout = QVBoxLayout()
        self.news_container.setLayout(self.news_layout)
        self.news_scroll.setWidget(self.news_container)
        
        # Área de resumo
        self.summary_label = QLabel("🔍 Resumo Analítico")
        self.summary_label.setFont(QFont("Arial", 14, QFont.Bold))
        
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        
        # Botão para gerar resumo
        self.summary_btn = QPushButton("Gerar Resumo com Gemini")
        self.summary_btn.clicked.connect(self.generate_summary)
        self.summary_btn.setStyleSheet("background-color: #2196F3; color: white;")
        self.summary_btn.setEnabled(False)
        
        # Adiciona widgets ao layout
        layout.addWidget(title)
        layout.addWidget(QLabel("Notícias Encontradas:"))
        layout.addWidget(self.news_scroll)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.summary_text)
        layout.addWidget(self.summary_btn)
        
        main_area.setLayout(layout)
        self.main_layout.addWidget(main_area)
    
    def start_news_search(self):
        if not self.query_input.text().strip():
            QMessageBox.warning(self, "Aviso", "Por favor, digite um tema para pesquisa.")
            return
        
        # Limpa resultados anteriores
        self.clear_news()
        
        # Prepara a pesquisa
        query = self.query_input.text()
        num_news = self.num_news_slider.value()
        period = self.period_combo.currentText()
        
        # Mostra barra de progresso
        self.progress_bar.setVisible(True)
        self.search_btn.setEnabled(False)
        
        # Inicia thread de busca
        self.news_worker = NewsWorker(query, num_news, period)
        self.news_worker.finished.connect(self.display_news)
        self.news_worker.error.connect(self.show_error)
        self.news_worker.progress.connect(self.progress_bar.setValue)
        self.news_worker.start()
    
    def clear_news(self):
        # Remove notícias anteriores
        while self.news_layout.count():
            child = self.news_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.summary_text.clear()
        self.summary_btn.setEnabled(False)
        self.news_data = []
    
    def display_news(self, news):
        self.progress_bar.setVisible(False)
        self.search_btn.setEnabled(True)
        self.news_data = news
        
        if not news:
            QMessageBox.information(self, "Informação", "Nenhuma notícia encontrada.")
            return
        
        for item in news:
            self.add_news_item(item)
        
        self.summary_btn.setEnabled(self.gemini_available and len(news) > 0)
    
    def add_news_item(self, news_item):
        group = QGroupBox(f"{news_item['title']} - {news_item['date']}")
        layout = QVBoxLayout()
        
        # Resumo
        summary = QLabel(news_item['summary'])
        summary.setWordWrap(True)
        
        # Botão para abrir notícia
        btn = QPushButton("🔗 Ver notícia completa")
        btn.setStyleSheet("text-align: left; color: blue;")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(news_item['url'])))
        
        layout.addWidget(summary)
        layout.addWidget(btn)
        group.setLayout(layout)
        self.news_layout.addWidget(group)
    
    def generate_summary(self):
        if not self.news_data:
            return
        
        # Prepara o prompt para o Gemini
        prompt = f"""
        Você é um especialista em análise de notícias. 
        Analise as seguintes notícias e forneça um resumo conciso e útil:
        
        Tema principal: {self.query_input.text()}
        
        Notícias: {json.dumps(self.news_data, indent=2)}
        
        Seu resumo deve incluir:
        1. Principais pontos em comum entre as notícias
        2. Destaques importantes
        3. Possíveis implicações ou tendências
        4. Contexto relevante
        
        Use linguagem clara e objetiva.
        """
        
        # Mostra mensagem de processamento
        processing_msg = QMessageBox(self)
        processing_msg.setWindowTitle("Processando")
        processing_msg.setText("Gerando resumo com Gemini...")
        processing_msg.setStandardButtons(QMessageBox.NoButton)
        processing_msg.hide()
        
        # Inicia thread do Gemini
        self.gemini_worker = GeminiWorker(self.model, prompt)
        self.gemini_worker.finished.connect(
            lambda text: (processing_msg.close(), self.summary_text.setPlainText(text)))
        self.gemini_worker.error.connect(
            lambda err: (processing_msg.close(), self.show_error(err)))
        self.gemini_worker.start()
    
    def show_error(self, message):
        QMessageBox.critical(self, "Erro", message)
        self.progress_bar.setVisible(False)
        self.search_btn.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NewsApp()
    window.show()
    sys.exit(app.exec_())

    # Interface gráfica capaz de buscar notícias com ate 6/periodo mensal
    # Mauricio De Jesus Cerqueira - 2025
    # Interface feita usando o sistema PyQt5 (pode ser moldado para usar uma interface gráfica SIGMA desde
    # que a configuração seja refeita a partir do código fonte do programa).
    # Tem uso apenas de bibliotecas python e recursos gratuitos de IA (Gemini API)
    # Key de uso individual e intransferivel (A chave da API só pode ser utilizada em um projeto python,
    # Se necessário crie outra chave API para um projeto diferente, para que não haja conflito de respostas
    # e/ou conflito de armazenamento da chave, causando sobrecarga de sistema e por consequencia um "Crash"
    # e/ou falha do sistema).
    # Caso tenha duvidas, entre em contato via LinkedIn, ou leia as instruções listadas dentro do meu Readme.md.