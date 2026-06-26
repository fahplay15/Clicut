import json
import os
import shutil
from pathlib import Path

import ffmpeg
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

try:
    import whisper
except ImportError:  # pragma: no cover - optional dependency for environments without it
    whisper = None

try:
    from groq import Groq
except ImportError:  # pragma: no cover - optional dependency for environments without it
    Groq = None

app = FastAPI(title="Gerador de Cortes IA", redirect_slashes=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "temp_"
UPLOAD_DIR.mkdir(exist_ok=True)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
cliente_groq = Groq(api_key=GROQ_API_KEY) if Groq is not None and GROQ_API_KEY else None

if whisper is not None:
    print("Carregando modelo Whisper... (isso pode demorar alguns segundos)")
    modelo_whisper = whisper.load_model("base")
else:
    modelo_whisper = None


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "gerador-de-cortes-ia"}


@app.post("/processar-video")
@app.post("/processar-video/")
async def processar_video(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith((".mp4", ".m4v")):
        raise HTTPException(status_code=400, detail="Formato não suportado. Envie um MP4.")

    caminho_video = UPLOAD_DIR / f"temp_{Path(file.filename or 'video').name}"
    caminho_saida = UPLOAD_DIR / f"corte_{Path(file.filename or 'video').name}"

    try:
        with caminho_video.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if modelo_whisper is None or cliente_groq is None:
            raise HTTPException(status_code=500, detail="As dependências de IA ainda não foram instaladas no ambiente. Instale whisper e groq para ativar a transcrição e a análise automática.")

        print("Vídeo recebido. Iniciando transcrição...")
        resultado_transcricao = modelo_whisper.transcribe(str(caminho_video))
        transcricao_texto = resultado_transcricao.get("text", "")
        segmentos = resultado_transcricao.get("segments", [])

        print("Analisando melhores momentos com o Groq...")
        prompt = f"""
        Você é um editor de vídeos virais. Leia esta transcrição e encontre o ÚNICO trecho mais
        impactante, polêmico ou que prenda muito a atenção (com cerca de 15 a 30 segundos de duração).
        Retorne APENAS um JSON válido no seguinte formato exato, sem explicações adicionais:
        {{"frase_inicial": "primeiras palavras do trecho escolhido", "frase_final": "últimas palavras do trecho"}}

        Transcrição:
        {transcricao_texto}
        """

        resposta_groq = cliente_groq.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="mixtral-8x7b-32768",
            response_format={"type": "json_object"},
        )

        escolha_ia = json.loads(resposta_groq.choices[0].message.content)

        tempo_inicio = 0
        tempo_fim = 15

        for seg in segmentos:
            texto_seg = seg.get("text", "")
            if escolha_ia.get("frase_inicial", "").lower() in texto_seg.lower():
                tempo_inicio = seg.get("start", 0)
            if escolha_ia.get("frase_final", "").lower() in texto_seg.lower():
                tempo_fim = seg.get("end", 15)
                break

        print(f"Cortando o vídeo de {tempo_inicio}s até {tempo_fim}s...")
        (
            ffmpeg.input(str(caminho_video), ss=tempo_inicio, to=tempo_fim)
            .output(str(caminho_saida))
            .run(overwrite_output=True, quiet=True)
        )

        return {"mensagem": "Sucesso", "arquivo": caminho_saida.name, "inicio": tempo_inicio, "fim": tempo_fim}

    except Exception as e:
        print(f"Erro no processo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if caminho_video.exists():
            caminho_video.unlink(missing_ok=True)
