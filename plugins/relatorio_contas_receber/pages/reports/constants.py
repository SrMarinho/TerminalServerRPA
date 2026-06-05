from enum import Enum


class FormatoArquivo(str, Enum):
    PADRAO = "Padrão"
    BITMAP = "Bitmap"
    JPEG = "JPEG"
    ARQUIVO_TEXTO_WINDOWS = "Arquivo Texto Windows"
    EXPORTACAO_WINDOWS = "Arquivo Exportação Windows"
    ARQUIVO_TEXTO_DOS = "Arquivo Texto DOS"
    EXPORTACAO_DOS = "Arquivo Exportação DOS"
    HTML = "HTML"
    EXPORTACAO_SAGA = "Exportação Layout Saga"
    EXPORTACAO_EXCEL = "Exportação Layout Excel"
    EXCEL = "Arquivo para Excel"
    EXCEL_OPENXML = "Arquivo para Excel (Open XML)"
    WORD_OPENXML = "Documento do Word (Open XML)"
    PDF = "Arquivo Formato PDF"
    CSV = "Arquivo Formato CSV"
    PDF_A = "Arquivo Formato PDF/A"

    def __str__(self) -> str:
        return self.value


class OpcaoRelatorio(str, Enum):
    VALIDAR = "V"
    BAIXAR = "B"

    def __str__(self) -> str:
        return self.value


class AnaliticoSintetico(str, Enum):
    ANALITICO = "A"
    SINTETICO = "S"

    def __str__(self) -> str:
        return self.value


class CsvRemoverEspacos(str, Enum):
    NAO = "nao"
    SIM = "sim"

    def __str__(self) -> str:
        return self.value
