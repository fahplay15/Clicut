# Gerador de Cortes IA

Este projeto é uma base inicial para um aplicativo que recebe um vídeo ou áudio e sugere trechos curtos para publicação.

## Estrutura

- backend/: servidor FastAPI
- frontend/: interface simples em HTML/CSS/JavaScript

## Como executar

1. Entre na pasta backend
2. Crie um ambiente virtual
3. Instale as dependências:

```bash
pip install -r requirements.txt
```

4. Inicie o servidor:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

5. Abra o arquivo frontend/index.html em um navegador ou sirva a pasta frontend com um servidor estático.

## Próximo passo

Integrar com Whisper para transcrição e Groq para análise de momentos mais relevantes.
