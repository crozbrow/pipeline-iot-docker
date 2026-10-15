-- VIEW 1: Temperatura media por ambiente
CREATE OR REPLACE VIEW avg_temp_por_ambiente AS
SELECT
    location_type AS ambiente,
    ROUND(AVG(temperature), 2) AS temperatura_media,
    COUNT(*) AS total_leituras
FROM temperature_readings
GROUP BY location_type;


-- VIEW 2: Quantidade de leituras por hora
CREATE OR REPLACE VIEW leituras_por_hora AS
SELECT
    EXTRACT(HOUR FROM recorded_at)::INTEGER AS hora,
    COUNT(*) AS contagem
FROM temperature_readings
GROUP BY EXTRACT(HOUR FROM recorded_at);


-- VIEW 3: Temperaturas maximas e minimas por dia
CREATE OR REPLACE VIEW temp_max_min_por_dia AS
SELECT
    recorded_at::DATE AS data,
    MAX(temperature) AS temp_max,
    MIN(temperature) AS temp_min,
    ROUND(AVG(temperature), 2) AS temp_media
FROM temperature_readings
GROUP BY recorded_at::DATE;
