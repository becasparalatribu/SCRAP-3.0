"""
Becas para La Tribu — scraper automatico
"""

import os
import json
import time
import logging
import requests
from bs4 import BeautifulSoup
from google import genai
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# Credenciales desde variables de entorno
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
GEMINI_KEY   = os.environ["GEMINI_KEY"]

# Clientes
db     = create_client(SUPABASE_URL, SUPABASE_KEY)
gemini = genai.Client(api_key=GEMINI_KEY)

FUENTES_FILE = os.path.join(os.path.dirname(__file__), "fuentes.txt")

HEADERS_WEB = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
}

HEADERS_RSS = {
    "User-Agent": "Mozilla/5.0 (compatible; FeedFetcher/1.0)",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

# Campos que existen en la DB — filtra todo lo demas antes del insert
CAMPOS_DB = {
    "titulo", "tipo", "descripcion", "organizacion", "reputacion_org",
    "fecha_limite", "pais_destino", "elegibilidad_latam", "disciplina",
    "nivel", "financiamiento", "cobra_por_aplicar", "alerta", "url", "fuente",
}

PROMPT = """
Sos un asistente especializado en oportunidades internacionales para latinoamericanos.

Analizá el texto y extraé TODAS las oportunidades mencionadas.
Tipos validos: beca | fellowship | internship | conferencia | financiamiento_proyecto | premio | intercambio | residencia | convocatoria | otro

APROBAR (descartada: false) si:
- La organizacion tiene nombre identificable
- No cobra fee por aplicar
- Beneficios realistas y verificables
- Es para personas individuales

DESCARTAR (descartada: true) si:
- Cobra fee de aplicacion
- Organizacion sin nombre
- Beneficios irreales o promesas vagas
- MLM, piramide, concurso de belleza, rifa
- Fecha limite ya vencio
- Es para instituciones, no personas

Responde UNICAMENTE con un array JSON valido. Sin texto extra, sin markdown. Si no hay oportunidades: []

[
  {{
    "titulo": "Nombre oficial",
    "tipo": "beca | fellowship | internship | conferencia | financiamiento_proyecto | premio | intercambio | residencia | convocatoria | otro",
    "descripcion": "Que es y que cubre. Maximo 2 oraciones.",
    "organizacion": "Entidad que la emite",
    "reputacion_org": "reconocida | nueva_sin_antecedentes | desconocida | sospechosa",
    "fecha_limite": "DD/MM/AAAA o No especificada",
    "pais_destino": "Pais o paises donde se realiza",
    "elegibilidad_latam": "si | no | no_especificado",
    "disciplina": "Area principal. Si aplica a todas: Todas. Si incluye cs sociales: Ciencias Sociales",
    "nivel": "grado | posgrado | doctorado | postdoctorado | profesional | todos",
    "financiamiento": "completo | parcial | sin_financiamiento | no_especificado",
    "cobra_por_aplicar": "si | no | no_especificado",
    "alerta": null,
    "descartada": false,
    "url": "URL directa si aparece, sino null",
    "fuente": "{fuente}"
  }}
]

Fuente: {fuente}
Texto:
{texto}
"""


def leer_fuentes():
    rss, web, telegram = [], [], []
    with open(FUENTES_FILE, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            partes = linea.split("|", 1)
            if len(partes) != 2:
                continue
            tipo, valor = partes[0].strip().lower(), partes[1].strip()
            if tipo == "rss":
                rss.append(valor)
            elif tipo == "web":
                web.append(valor)
            elif tipo == "telegram":
                telegram.append(valor)
    log.info(f"Fuentes: {len(rss)} RSS, {len(web)} web, {len(telegram)} Telegram")
    return rss, web, telegram


def obtener_rss(url):
    try:
        r = requests.get(url, headers=HEADERS_RSS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "xml")
        items = soup.find_all("item") or soup.find_all("entry")
        if not items:
            return None
        partes = []
        for item in items[:20]:
            titulo = item.find("title")
            desc   = item.find("description") or item.find("summary")
            link   = item.find("link")
            linea  = []
            if titulo:
                linea.append(f"TITULO: {titulo.get_text(strip=True)}")
            if desc:
                texto_desc = BeautifulSoup(desc.get_text(strip=True), "html.parser").get_text(separator=" ", strip=True)
                linea.append(f"DESC: {texto_desc[:300]}")
            if link:
                href = link.get("href") or link.get_text(strip=True)
                if href:
                    linea.append(f"URL: {href}")
            if linea:
                partes.append(" | ".join(linea))
        return "\n\n".join(partes)[:8000] if partes else None
    except Exception as e:
        log.warning(f"Error RSS {url}: {e}")
        return None


def obtener_web(url):
    try:
        r = requests.get(url, headers=HEADERS_WEB, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)[:8000]
    except Exception as e:
        log.warning(f"Error web {url}: {e}")
        return None


def obtener_telegram(canal):
    try:
        r = requests.get(f"https://t.me/s/{canal}", headers=HEADERS_WEB, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        mensajes = soup.find_all("div", class_="tgme_widget_message_text")
        if mensajes:
            return " || ".join(m.get_text(separator=" ", strip=True) for m in mensajes[-30:])[:8000]
        for tag in soup(["script", "style", "nav", "header"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)[:8000]
    except Exception as e:
        log.warning(f"Error Telegram @{canal}: {e}")
        return None


def clasificar(texto, fuente):
    prompt = PROMPT.format(fuente=fuente, texto=texto)
    try:
        resp = gemini.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        raw = resp.text.strip()
        if "```" in raw:
            partes = raw.split("```")
            raw = partes[1] if len(partes) > 1 else raw
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()
        inicio = raw.find("[")
        fin    = raw.rfind("]")
        if inicio != -1 and fin != -1:
            raw = raw[inicio:fin+1]
        resultado = json.loads(raw)
        return resultado if isinstance(resultado, list) else []
    except Exception as e:
        log.warning(f"Error IA {fuente}: {e}")
        return []


def guardar(oportunidades):
    ok = desc = 0
    for op in oportunidades:
        try:
            es_desc   = op.get("descartada", False)
            tabla     = "becas_descartadas" if es_desc else "becas"
            op_limpia = {k: v for k, v in op.items() if k in CAMPOS_DB}
            if op_limpia.get("url"):
                db.table(tabla).upsert(op_limpia, on_conflict="url").execute()
            else:
                db.table(tabla).insert(op_limpia).execute()
            if es_desc:
                desc += 1
            else:
                ok += 1
        except Exception as e:
            log.warning(f"Error guardando '{op.get('titulo', '?')}': {e}")
    return ok, desc


def procesar(texto, fuente):
    ops = clasificar(texto, fuente)
    log.info(f"  IA detecto {len(ops)} oportunidades.")
    g, d = guardar(ops)
    log.info(f"  OK: {g} guardadas | DESCARTADAS: {d}")
    return g, d


def main():
    rss, web, telegram = leer_fuentes()
    total_ok = total_desc = 0

    for url in rss:
        log.info(f"[RSS] {url}")
        texto = obtener_rss(url)
        if texto:
            g, d = procesar(texto, url)
            total_ok += g; total_desc += d
        time.sleep(2)

    for url in web:
        log.info(f"[WEB] {url}")
        texto = obtener_web(url)
        if texto:
            g, d = procesar(texto, url)
            total_ok += g; total_desc += d
        time.sleep(3)

    for canal in telegram:
        log.info(f"[TELEGRAM] @{canal}")
        texto = obtener_telegram(canal)
        if texto:
            g, d = procesar(texto, f"https://t.me/{canal}")
            total_ok += g; total_desc += d
        time.sleep(3)

    log.info(f"Finalizado. Guardadas: {total_ok} | Descartadas: {total_desc}")


if __name__ == "__main__":
    main()
