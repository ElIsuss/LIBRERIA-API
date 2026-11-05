from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core.paginacion import Page
from app.modules.libros.models import Libro, LibroAutor
from app.modules.libros.schemas import (
    AutorEnLibro,
    EditorialEnLibro,
    GeneroEnLibro,
    LibroCreate,
    LibroDetalle,
    LibroLista,
    LibroUpdate,
    MovimientoStockRead,
    ReponerStockRequest,
)
from app.modules.libros.unit_of_work import LibrosUnitOfWork

MSG_CONFLICTO = "No se pudo guardar el libro: isbn duplicado o id de editorial, genero o autor invalido"


def _a_detalle(libro: Libro) -> LibroDetalle:
    autorias_ordenadas = sorted(libro.autorias, key=lambda a: a.orden)
    return LibroDetalle(
        id=libro.id,
        isbn=libro.isbn,
        titulo=libro.titulo,
        precio=libro.precio,
        stock=libro.stock,
        editorial=EditorialEnLibro.model_validate(libro.editorial),
        genero=GeneroEnLibro.model_validate(libro.genero) if libro.genero else None,
        autores=[
            AutorEnLibro(
                id=a.autor.id,
                nombre=a.autor.nombre,
                nacionalidad=a.autor.nacionalidad,
                rol=a.rol,
                orden=a.orden,
            )
            for a in autorias_ordenadas
        ],
        borrado_en=libro.borrado_en,
    )


def _a_lista(libro: Libro) -> LibroLista:
    return LibroLista(
        id=libro.id,
        isbn=libro.isbn,
        titulo=libro.titulo,
        precio=libro.precio,
        stock=libro.stock,
        editorial=EditorialEnLibro.model_validate(libro.editorial),
        genero=GeneroEnLibro.model_validate(libro.genero) if libro.genero else None,
        borrado_en=libro.borrado_en,
    )


async def obtener_por_id(uow: LibrosUnitOfWork, libro_id: int) -> LibroDetalle:
    libro = await uow.libros.get_detalle(libro_id, include_deleted=False)
    if libro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un libro con ese id",
        )
    return _a_detalle(libro)


async def crear(
    uow: LibrosUnitOfWork,
    datos: LibroCreate,
    admin_id: int,
) -> LibroDetalle:
    isbn_existente = await uow.libros.get_by_isbn(datos.isbn, include_deleted=False)
    if isbn_existente is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=MSG_CONFLICTO,
        )

    payload = datos.model_dump()
    autorias_datos = payload.pop("autores", [])
    stock_inicial = payload.pop("stock_inicial", 0)

    libro = Libro(**payload, stock=0)

    try:
        async with uow:
            libro = await uow.libros.add(libro)
            for a in autorias_datos:
                await uow.libros.add_autoria(
                    LibroAutor(
                        libro_id=libro.id,
                        autor_id=a["autor_id"],
                        rol=a["rol"],
                        orden=a["orden"],
                    )
                )

            if stock_inicial > 0:
                await uow.registrar_movimiento_stock(
                    libro=libro,
                    usuario_id=admin_id,
                    cantidad=stock_inicial,
                    motivo="Stock inicial",
                )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=MSG_CONFLICTO,
        )

    return await obtener_por_id(uow, libro.id)


async def listar_paginado(
    uow: LibrosUnitOfWork,
    page: int = 1,
    size: int = 20,
    titulo: str | None = None,
    genero_id: int | None = None,
) -> Page[LibroLista]:
    items, total = await uow.libros.listar_catalogo(
        titulo=titulo,
        genero_id=genero_id,
        page=page,
        size=size,
    )
    items_dto = [_a_lista(l) for l in items]
    try:
        return Page.create(items=items_dto, total=total, page=page, size=size)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"La página {page} solicitada excede el total de páginas disponibles",
        )


async def actualizar(
    uow: LibrosUnitOfWork,
    libro_id: int,
    datos: LibroUpdate,
) -> LibroDetalle:
    libro = await uow.libros.get_by_id(libro_id, include_deleted=False)
    if libro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un libro con ese id",
        )

    cambios = datos.model_dump(exclude_unset=True)
    if "isbn" in cambios and cambios["isbn"] != libro.isbn:
        isbn_existente = await uow.libros.get_by_isbn(cambios["isbn"], include_deleted=False)
        if isbn_existente is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=MSG_CONFLICTO,
            )

    for campo, valor in cambios.items():
        setattr(libro, campo, valor)

    if not cambios:
        return await obtener_por_id(uow, libro_id)

    try:
        async with uow:
            await uow.libros.update(libro)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=MSG_CONFLICTO,
        )

    return await obtener_por_id(uow, libro_id)


async def reponer_stock(
    uow: LibrosUnitOfWork,
    libro_id: int,
    datos: ReponerStockRequest,
    admin_id: int,
) -> MovimientoStockRead:
    libro = await uow.libros.get_by_id(libro_id, include_deleted=False)
    if libro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un libro activo con ese id",
        )

    async with uow:
        mov = await uow.registrar_movimiento_stock(
            libro=libro,
            usuario_id=admin_id,
            cantidad=datos.cantidad,
            motivo=datos.motivo,
        )

    return MovimientoStockRead.model_validate(mov)


async def eliminar_libro(
    uow: LibrosUnitOfWork,
    libro_id: int,
) -> None:
    libro = await uow.libros.get_by_id(libro_id, include_deleted=False)
    if libro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un libro con ese id",
        )

    async with uow:
        await uow.libros.soft_delete(libro_id)


async def listar_movimientos(
    uow: LibrosUnitOfWork,
    libro_id: int,
) -> list[MovimientoStockRead]:
    libro = await uow.libros.get_by_id_including_deleted(libro_id)
    if libro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un libro con ese id",
        )

    movimientos = await uow.movimientos.get_por_libro(libro_id)
    return [MovimientoStockRead.model_validate(m) for m in movimientos]
