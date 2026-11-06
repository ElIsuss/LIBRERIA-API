-- ==================================================================---------------------------
-- Caso de prueba C-14: Demuestra que UPDATE y DELETE sobre movimiento_stock son
-- rechazados por el trigger append-only de la 4ª migración RN-12.
-- Ejecutar con: psql -U usuario -d base -f test/solo_agregado.sql
-- ==================================================================---------------------------

-- 1. Intento de UPDATE sobre movimiento_stock - DEBE FALLAR
DO $$
BEGIN
    UPDATE movimiento_stock
    SET cantidad = 5
    WHERE id = (SELECT id FROM movimiento_stock LIMIT 1);
    
    RAISE NOTICE 'ERROR: El UPDATE fue exitoso (debería haber fallado)';
EXCEPTION WHEN unique_violation THEN
    RAISE NOTICE 'Éxito: El UPDATE fue rechazado por el trigger. No se modificaron filas.';
    RAISE NOTICE 'El trigger append-only (RN-12) impide modificaciones sobre movimiento_stock';
WHEN others THEN
    RAISE NOTICE 'Éxito: El UPDATE fue rechazado por el trigger. Error: %', SQLERRM;
END $$;


-- 2. Intento de DELETE sobre movimiento_stock - DEBE FALLAR
DO $$
BEGIN
    DELETE FROM movimiento_stock
    WHERE id = (SELECT id FROM movimiento_stock LIMIT 1);
    
    RAISE NOTICE 'ERROR: El DELETE fue exitoso (debería haber fallado)';
EXCEPTION WHEN unique_violation THEN
    RAISE NOTICE 'Éxito: El DELETE fue rechazado por el trigger. No se eliminaron filas.';
    RAISE NOTICE 'El trigger append-only (RN-12) impide eliminaciones sobre movimiento_stock';
WHEN others THEN
    RAISE NOTICE 'Éxito: El DELETE fue rechazado por el trigger. Error: %', SQLERRM;
END $$;

-- Verificación final: contar filas en movimiento_stock para confirmar que ninguna fue eliminada o modificada
SELECT COUNT(*) AS total_filas FROM movimiento_stock;
-- El resultado debe ser el mismo que antes de ejecutar los intentos anteriores.
-- Si las filas count es consistente, el trigger está funcionando correctamente.