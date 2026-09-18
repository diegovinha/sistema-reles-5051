# ⚡ Sistema de Ensaios de Relés de Sobrecorrente ANSI 50/51

Sistema web desenvolvido em **Python** e **Streamlit** para apoio à execução, análise e documentação de ensaios em relés de proteção de sobrecorrente.

A aplicação permite configurar parâmetros de proteção, analisar curvas de atuação, registrar pontos de ensaio e gerar relatórios técnicos em PDF com os resultados obtidos.

## 🛡️ Funções de Proteção

O sistema contempla principalmente:

- **ANSI 50** — Sobrecorrente Instantânea
- **ANSI 51** — Sobrecorrente Temporizada

Permite trabalhar com diferentes características de curvas de atuação utilizadas em sistemas de proteção elétrica.

## 📊 Principais Funcionalidades

- Configuração dos parâmetros do relé
- Curvas de sobrecorrente temporizada
- Proteção instantânea ANSI 50
- Curvas IEC 60255
- Curvas IEEE/ANSI
- Relação de Transformação de Corrente (RTC)
- Registro de correntes primárias e secundárias
- Registro dos tempos reais de atuação
- Cálculo automático dos tempos teóricos
- Cálculo do erro relativo
- Aplicação de tolerância aos resultados
- Classificação automática dos pontos de ensaio
- Visualização gráfica das curvas
- Identificação completa do equipamento ensaiado
- Salvamento e carregamento dos dados do ensaio em JSON
- Geração automática de relatório técnico em PDF
- Identificação do responsável pelo ensaio
- Sistema de autenticação de usuários

## 🧾 Identificação do Ensaio

O sistema permite registrar informações como:

- Modelo do relé
- Fabricante
- Número de série
- ID do equipamento
- Local da instalação
- Ordem de Ajuste (O/A)
- Ordem de Serviço (O/S)
- Solicitante
- Data do ensaio

Essas informações são incorporadas ao relatório técnico gerado pela aplicação.

## 📄 Relatório Técnico

A aplicação gera relatório técnico em PDF contendo informações como:

- Identificação do equipamento
- Dados do ensaio
- Norma e curva utilizadas
- Ajustes ANSI 50/51
- Relação RTC
- Correntes de ensaio
- Tempos teóricos
- Tempos reais medidos
- Erro relativo
- Resultado de cada ponto
- Identificação do responsável pelo ensaio

Os resultados são avaliados automaticamente de acordo com a tolerância definida pelo usuário.

## 🧰 Tecnologias Utilizadas

O projeto utiliza:

- Python
- Streamlit
- NumPy
- Pandas
- Plotly
- Matplotlib
- ReportLab
- SQLite

## 📦 Instalação

Clone o repositório:

```bash
git clone https://github.com/diegovinha/sistema-reles-5051.git

