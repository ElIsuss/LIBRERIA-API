# Evidencia Caso C-15: Ausencia de N+1 y Cantidad Fija de Consultas SQL

## 1. Contexto y Regla de Negocio Evaluada
- **Regla RN-13 / Requerimiento C-15**: Al consultar una venta con sus renglones y libros vinculados, el sistema no debe ejecutar una consulta SQL adicional por cada renglón (antipatrón N+1).
- **Mecanismo**: Estrategia de precargas eager con SQLAlchemy en el repositorio de ventas:
  - `joinedload(Venta.cliente)`
  - `selectinload(Venta.renglones).joinedload(RenglonVenta.libro)`

## 2. Petición HTTP Realizada
- **Endpoint**: `GET http://localhost:8000/ventas/1`
- **Autenticación**: Cookie `HttpOnly` (`access_token`) con usuario de rol `VENDEDOR`.

### Respuesta JSON Obtenida (`200 OK`)
```json
{
  "id": 1,
  "fecha": "2026-11-07T16:59:16.837764Z",
  "total": "69000.00",
  "cliente": {
    "id": 1,
    "nombre": "Lucía Fernández",
    "email": "lucia@example.com"
  },
  "renglones": [
    {
      "libro_id": 1,
      "titulo": "Rayuela",
      "cantidad": 1,
      "precio_unitario": "25000.00",
      "subtotal": "25000.00"
    },
    {
      "libro_id": 3,
      "titulo": "Ficciones",
      "cantidad": 2,
      "precio_unitario": "22000.00",
      "subtotal": "44000.00"
    }
  ]
}
```

## 3. Salida de Consola con Logs SQL (`SQL_ECHO=true`)
```text
2026-11-07 15:09:41,914 INFO sqlalchemy.engine.Engine BEGIN (implicit)

-- Verificación de usuario autenticado en la sesión:
2026-11-07 15:09:41,935 INFO sqlalchemy.engine.Engine SELECT usuario.id, usuario.email, usuario.nombre, usuario.password_hash, usuario.activo, usuario.debe_cambiar_password 
FROM usuario 
WHERE usuario.id = $1::INTEGER
2026-11-07 15:09:41,935 INFO sqlalchemy.engine.Engine [generated in 0.00040s] (3,)

-- CONSULTA 1: Lectura de la Venta con JOIN a Cliente (joinedload)
2026-11-07 15:09:41,944 INFO sqlalchemy.engine.Engine SELECT venta.id, venta.fecha, venta.total, venta.cliente_id, cliente_1.id AS id_1, cliente_1.nombre, cliente_1.email, cliente_1.usuario_id 
FROM venta LEFT OUTER JOIN cliente AS cliente_1 ON cliente_1.id = venta.cliente_id 
WHERE venta.id = $1::INTEGER
2026-11-07 15:09:41,944 INFO sqlalchemy.engine.Engine [generated in 0.00030s] (1,)

-- CONSULTA 2: Lectura de los Renglones con JOIN a Libro (selectinload con IN)
2026-11-07 15:09:41,952 INFO sqlalchemy.engine.Engine SELECT renglon_venta.venta_id, renglon_venta.id, renglon_venta.libro_id, renglon_venta.cantidad, renglon_venta.precio_unitario, libro_1.id, libro_1.isbn, libro_1.titulo, libro_1.precio, libro_1.stock, libro_1.editorial_id, libro_1.genero_id, libro_1.borrado_en 
FROM renglon_venta LEFT OUTER JOIN libro AS libro_1 ON libro_1.id = renglon_venta.libro_id 
WHERE renglon_venta.venta_id IN ($1::INTEGER)
2026-11-07 15:09:41,952 INFO sqlalchemy.engine.Engine [generated in 0.00035s] (1,)

-- Verificación de roles vigentes en tiempo real:
2026-11-07 15:09:41,960 INFO sqlalchemy.engine.Engine SELECT DISTINCT asignacion_rol.rol 
FROM asignacion_rol 
WHERE asignacion_rol.usuario_id = $1::INTEGER AND asignacion_rol.revocada_en IS NULL AND (asignacion_rol.vence_en IS NULL OR asignacion_rol.vence_en > $2::TIMESTAMP WITH TIME ZONE)
2026-11-07 15:09:41,960 INFO sqlalchemy.engine.Engine [generated in 0.00034s] (3, datetime.datetime(2026, 11, 7, 18, 9, 41, 958811, tzinfo=datetime.timezone.utc))

INFO:     127.0.0.1:53963 - "GET /ventas/1 HTTP/1.1" 200 OK
2026-11-07 15:09:41,965 INFO sqlalchemy.engine.Engine ROLLBACK
```

## 4. Conclusión Técnica
- Para obtener la venta completa con su cliente, sus múltiples renglones (*Rayuela* y *Ficciones*) y la información de los libros, SQLAlchemy ejecutó exactamente **2 consultas SQL fijas**:
  1. `SELECT ... FROM venta LEFT OUTER JOIN cliente`
  2. `SELECT ... FROM renglon_venta LEFT OUTER JOIN libro WHERE renglon_venta.venta_id IN (1)`
- No se produce el problema N+1: independientemente de que la venta tenga 2, 4 o 50 renglones, el número de consultas para recuperar la entidad y sus dependencias permanece estrictamente fijo e independiente de la cantidad de renglones.
