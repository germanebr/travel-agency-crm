from __future__ import annotations

from enum import StrEnum


class TripStatus(StrEnum):
    PROXIMO = "Próximo"
    VIAJANDO = "Viajando"
    FINALIZADO = "Finalizado"
    CANCELADO = "Cancelado"


class SaleStatus(StrEnum):
    RESERVADA = "Reservada"
    LIQUIDADA = "Liquidada"
    COMPLETA = "Completa"
    CANCELADA = "Cancelada"
    NO_APLICA = "No aplica"


class ProviderName(StrEnum):
    AEROMEXICO = "Aeromexico"
    AGENT_CARS = "Agent Cars"
    BEDSONLINE = "Bedsonline"
    CIVITATIS = "Civitatis"
    CREATUR = "Creatur"
    DISNEY = "Disney"
    EXPEDIA_MX = "Expedia MX"
    EXPEDIA_USA = "Expedia USA"
    GRUPO_LOMAS = "GRUPO LOMAS"
    ROOM_RES = "Room res"
    TERRAWIND = "Terrawind"
    VAX = "VAX"
    VACATION_EXPRESS = "Vacation Express"
    VIATOR = "Viator"
    VIRGIN = "Virgin"
    XCARET_SALES = "Xcaret Sales"
