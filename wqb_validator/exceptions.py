"""
WQB Expression Validator 异常定义
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ValidationError:
    """验证错误信息"""

    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    code: str = ""
    suggestion: Optional[str] = None

    def __str__(self):
        """字符串表示"""
        if self.line and self.column:
            return f"第{self.line}行第{self.column}列: {self.message}"
        return self.message

    def to_dict(self):
        """转换为字典格式"""
        return {
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "code": self.code,
            "suggestion": self.suggestion,
        }


@dataclass
class ValidationResult:
    """验证结果"""

    is_valid: bool
    errors: List[ValidationError]
    warnings: List[str] = None
    metadata: dict = None

    def __post_init__(self):
        """初始化后处理"""
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}

    def add_error(self, error: ValidationError):
        """添加错误"""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str):
        """添加警告"""
        self.warnings.append(warning)

    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """是否有警告"""
        return len(self.warnings) > 0

    def error_count(self) -> int:
        """错误数量"""
        return len(self.errors)

    def warning_count(self) -> int:
        """警告数量"""
        return len(self.warnings)

    def to_dict(self):
        """转换为字典格式"""
        return {
            "is_valid": self.is_valid,
            "errors": [error.to_dict() for error in self.errors],
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


class ValidationException(Exception):
    """验证异常基类"""

    def __init__(self, message: str, errors: List[ValidationError] = None):
        super().__init__(message)
        self.message = message
        self.errors = errors or []

    def __str__(self):
        return f"{self.message} (错误数量: {len(self.errors)})"


class ConfigurationError(ValidationException):
    """配置错误"""

    pass


class DataLoadError(ValidationException):
    """数据加载错误"""

    pass


class GrammarError(ValidationException):
    """语法错误"""

    pass
