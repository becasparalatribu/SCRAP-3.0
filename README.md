# Becas para La Tribu — Scraper

Scraping diario de becas internacionales para latinoamericanos.

## Stack

| | Herramienta |
|---|---|
| Scraping | Python + BeautifulSoup + lxml |
| IA | Gemini 2.0 Flash |
| Base de datos | Supabase |
| Automatización | GitHub Actions (8am ARG) |

---

## Setup inicial

### 1. Supabase
1. Crear cuenta en https://supabase.com → nuevo proyecto
2. SQL Editor → pegar y ejecutar `setup_supabase.sql`
3. Settings → API → copiar `Project URL` y `anon public key`

### 2. Gemini
1. https://aistudio.google.com → Get API Key → copiar

### 3. GitHub
1. Nuevo repo **privado** → subir todos estos archivos
2. El `scraper.yml` va en `.github/workflows/scraper.yml`
3. Settings → Secrets → Actions → agregar:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `GEMINI_KEY`

---

## Estructura

```
becas-scraper/
├── .github/
│   └── workflows/
│       └── scraper.yml
├── scraper.py
├── manual_review.py
├── fuentes.txt
├── requirements.txt
├── setup_supabase.sql
└── README.md
```

---

## fuentes.txt

Formato por línea: `tipo|valor`

```
rss|https://www.opportunitydesk.org/feed/
web|https://chevening.org/scholarships/
telegram|latam_becas
```

Tipos: `rss` (preferido), `web`, `telegram`. Líneas con `#` se ignoran.

---

## manual_review.py

Para cargar oportunidades desde LinkedIn o Instagram manualmente:

```bash
python manual_review.py
# o directo:
python manual_review.py "texto del post"
```

Requiere las mismas variables de entorno: `SUPABASE_URL`, `SUPABASE_KEY`, `GEMINI_KEY`.

---

## Tablas en Supabase

**`becas`** — oportunidades aprobadas  
**`becas_descartadas`** — descartadas por la IA (auditoría)  
**`becas_vigentes`** — vista: solo vigentes y elegibles LATAM  
**`becas_cs`** — vista: ciencias sociales y humanidades

### Campos

| Campo | Valores |
|---|---|
| tipo | beca, fellowship, internship, conferencia, financiamiento_proyecto, premio, intercambio, residencia, convocatoria, otro |
| elegibilidad_latam | si, no, no_especificado |
| nivel | grado, posgrado, doctorado, postdoctorado, profesional, todos |
| financiamiento | completo, parcial, sin_financiamiento, no_especificado |
| reputacion_org | reconocida, nueva_sin_antecedentes, desconocida, sospechosa |

---

## Notas

- El campo `descartada` que devuelve la IA se usa solo para decidir la tabla destino. No se guarda en la DB.
- Becas sin URL se insertan con `insert()` directo. Pueden generarse duplicados si la misma beca aparece en múltiples fuentes sin URL.
- El modelo es `gemini-2.0-flash`. No cambiar a versiones anteriores.
