# 🏓 Sistema de Gerenciamento de Tênis de Mesa

Sistema web para gerenciamento de atletas, clubes, campeonatos e upload de vídeos de tênis de mesa.

## 📋 Índice

- [Sobre o Projeto](#sobre-o-projeto)
- [Tecnologias](#tecnologias)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Executando o Projeto](#executando-o-projeto)
- [Comandos Úteis](#comandos-úteis)
- [Backup e Restore](#backup-e-restore)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Contribuição](#contribuição)
- [Licença](#licença)

## 🎯 Sobre o Projeto

Sistema desenvolvido para gerenciar:

- **Atletas**: Cadastro, foto, estatísticas e histórico
- **Clubes**: Gestão de clubes e associações
- **Campeonatos**: Organização de torneios e competições
- **Vídeos**: Upload e gerenciamento de vídeos de partidas

### Funcionalidades Principais

- ✅ Cadastro completo de atletas com foto
- ✅ Gerenciamento de clubes e associações
- ✅ Organização de campeonatos e torneios
- ✅ Upload de vídeos de partidas
- ✅ Sistema de autenticação JWT
- ✅ API REST com documentação automática
- ✅ Backup automatizado do banco de dados
- ✅ Containerização com Docker

## 🛠️ Tecnologias

### Backend
- **Django 5.0** - Framework web
- **Django REST Framework** - API REST
- **PostgreSQL** - Banco de dados (produção)
- **SQLite** - Banco de dados (desenvolvimento)
- **JWT** - Autenticação
- **Docker** - Containerização

### Ferramentas
- **Docker Compose** - Orquestração de containers
- **PostgreSQL Client** - Backup e restore
- **Python 3.11** - Linguagem

## 📋 Pré-requisitos

Antes de começar, certifique-se de ter instalado:

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [Git](https://git-scm.com/)
- [PostgreSQL Client](https://www.postgresql.org/download/) (para scripts de backup)

## 🚀 Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/sistema-tenis-mesa.git
cd sistema-tenis-mesa