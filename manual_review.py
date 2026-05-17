"""
Becas para La Tribu — carga manual desde LinkedIn / Instagram
Uso: python manual_review.py
  o: python manual_review.py "texto del post"
"""

import os
import sys
import json
import logging
from google import genai
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
GEMINI_KEY   = os.environ["GEMINI_KEY"]

db     = create_client(SUPABASE_URL, SUPABASE_KEY)
gemini = genai.Client(api_key=GEMINI_KEY)

CAMPOS_DB = {
    "titulo", "tipo", "descripcion", "organizacion", "reputacion_org",
    "fecha_limite", "pais_destino", "elegibilidad_latam", "disciplina",
    "nivel", "financiamiento", "cobra_por_aplicar", "alerta", "url", "fuente",
}

PROMPT = """
Sos un asistente especializado en oportunidades internacionales para latinoamericanos.

Analiza este texto y extrae la oportunidad principal.

APROBAR (descartada: false) si:
- La organizacion tiene nombre identificable
- No cobra fee por aplicar
- Beneficios realistas y verificables
- Es para personas individuales

DESCARTAR (descartada: true) si:
- Cobra fee de aplicacion
- Organizacion sin nombre
- Beneficios irreales
- MLM, piramide, concurso de belleza, rifa
- Fecha limite ya vencio
- Es para instituciones, no personas

Responde SOLO con un objeto JSON. Sin markdown, sin texto extra.

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
  "url": "URL si aparece en el texto, sino null",
  "fuente": "{fuente}"
}}

Texto:
{texto}
"""


def procesar(texto, fuente):
    try:
        resp = gemini.models.generate_content(
            model="gemini-2.0-flash",
            contents=PROMPT.format(fuente=fuente, texto=texto),
        )
        raw = resp.text.strip()
        if "```" in raw:
            partes = raw.split("```")
            raw = partes[1] if len(partes) > 1 else raw
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()
        return json.loads(raw)
    except Exception as e:
        log.error(f"Error IA: {e}")
        return None


def guardar(op):
    try:
        es_desc   = op.get("descartada", False)
        tabla     = "becas_descartadas" if es_desc else "becas"
        op_limpia = {k: v for k, v in op.items() if k in CAMPOS_DB}
        if op_limpia.get("url"):
            db.table(tabla).upsert(op_limpia, on_conflict="url").execute()
        else:
            db.table(tabla).insert(op_limpia).execute()
        return True
    except Exception as e:
        log.error(f"Error guardando: {e}")
        return False


def mostrar(op):
    print("\n" + "="*50)
    print(f"TITULO:       {op.get('titulo', '?')}")
    print(f"ORG:          {op.get('organizacion', '?')} ({op.get('reputacion_org', '?')})")
    print(f"FECHA LIMITE: {op.get('fecha_limite', '?')}")
    print(f"PAIS:         {op.get('pais_destino', '?')}")
    print(f"NIVEL:        {op.get('nivel', '?')}")
    print(f"FINANCIAM.:   {op.get('financiamiento', '?')}")
    print(f"COBRA FEE:    {op.get('cobra_por_aplicar', '?')}")
    if op.get("alerta"):
        print(f"ALERTA:       {op['alerta']}")
    estado = "DESCARTADA" if op.get("descartada") else "APROBADA"
    print(f"ESTADO:       {estado}")
    print("="*50)


def main():
    if len(sys.argv) > 1:
        texto  = " ".join(sys.argv[1:])
        fuente = "manual_cli"
    else:
        print("Pega el texto del post. Enter dos veces para terminar.\n")
        lineas = []
        while True:
            linea = input()
            if linea == "" and lineas and lineas[-1] == "":
                break
            lineas.append(linea)
        texto = "\n".join(lineas).strip()
        fuente = input("\nFuente (ej: @canal, linkedin.com/...): ").strip() or "manual"

    if not texto:
        print("Sin texto. Saliendo.")
        return

    print("\nProcesando...")
    op = procesar(texto, fuente)
    if not op:
        print("No se pudo procesar.")
        return

    mostrar(op)

    if input("\nGuardar? (s/n): ").strip().lower() == "s":
        print("Guardado." if guardar(op) else "Error al guardar.")
    else:
        print("Cancelado.")


if __name__ == "__main__":
    main()
