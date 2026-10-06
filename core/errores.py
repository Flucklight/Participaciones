"""Errores del dominio. La interfaz los captura y muestra su mensaje."""


class ErrorDominio(Exception):
    """Se violó una regla de negocio (dato inválido, duplicado, no encontrado)."""


class ErrorImportacion(ErrorDominio):
    """El archivo de lista de inscripción no tiene el formato esperado."""
