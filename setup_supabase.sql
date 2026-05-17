-- Becas para La Tribu — setup Supabase
-- Ejecutar UNA SOLA VEZ en el SQL Editor de Supabase

CREATE TABLE IF NOT EXISTS becas (
    id                 UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    titulo             TEXT        NOT NULL,
    tipo               TEXT,
    descripcion        TEXT,
    organizacion       TEXT,
    reputacion_org     TEXT,
    fecha_limite       TEXT,
    pais_destino       TEXT,
    elegibilidad_latam TEXT,
    disciplina         TEXT,
    nivel              TEXT,
    financiamiento     TEXT,
    cobra_por_aplicar  TEXT,
    alerta             TEXT,
    url                TEXT UNIQUE,
    fuente             TEXT,
    creado_en          TIMESTAMPTZ DEFAULT now(),
    actualizado_en     TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS becas_descartadas (
    id                 UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    titulo             TEXT,
    tipo               TEXT,
    descripcion        TEXT,
    organizacion       TEXT,
    reputacion_org     TEXT,
    fecha_limite       TEXT,
    pais_destino       TEXT,
    elegibilidad_latam TEXT,
    disciplina         TEXT,
    nivel              TEXT,
    financiamiento     TEXT,
    cobra_por_aplicar  TEXT,
    alerta             TEXT,
    url                TEXT UNIQUE,
    fuente             TEXT,
    creado_en          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_becas_tipo           ON becas (tipo);
CREATE INDEX IF NOT EXISTS idx_becas_nivel          ON becas (nivel);
CREATE INDEX IF NOT EXISTS idx_becas_pais           ON becas (pais_destino);
CREATE INDEX IF NOT EXISTS idx_becas_disciplina     ON becas (disciplina);
CREATE INDEX IF NOT EXISTS idx_becas_financiamiento ON becas (financiamiento);
CREATE INDEX IF NOT EXISTS idx_becas_latam          ON becas (elegibilidad_latam);
CREATE INDEX IF NOT EXISTS idx_becas_creado_en      ON becas (creado_en DESC);

CREATE OR REPLACE FUNCTION actualizar_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.actualizado_en = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trigger_actualizar_timestamp
    BEFORE UPDATE ON becas
    FOR EACH ROW
    EXECUTE FUNCTION actualizar_timestamp();

-- Vista: becas vigentes para LATAM
CREATE OR REPLACE VIEW becas_vigentes AS
SELECT * FROM becas
WHERE (
    fecha_limite IS NULL
    OR fecha_limite = 'No especificada'
    OR (
        fecha_limite ~ '^\d{2}/\d{2}/\d{4}$'
        AND TO_DATE(fecha_limite, 'DD/MM/YYYY') >= CURRENT_DATE
    )
)
AND elegibilidad_latam IN ('si', 'no_especificado')
ORDER BY creado_en DESC;

-- Vista: solo ciencias sociales y humanidades
CREATE OR REPLACE VIEW becas_cs AS
SELECT * FROM becas_vigentes
WHERE disciplina ILIKE '%Ciencias Sociales%'
   OR disciplina ILIKE '%Social Sciences%'
   OR disciplina ILIKE '%Humanidades%'
   OR disciplina ILIKE '%Humanities%'
   OR disciplina ILIKE '%Todas%'
ORDER BY creado_en DESC;
