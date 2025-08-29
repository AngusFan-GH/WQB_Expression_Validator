import json
import pandas as pd
from lark import Lark, Transformer, exceptions
import re
import os
from typing import List, Tuple, Dict, Any, Optional, Set
from dataclasses import dataclass

from .utils.fetch_data import DATA_DIR

# ====== 类型定义 ======


@dataclass
class ValidationError:
    """验证错误信息"""

    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    code: str = ""
    suggestion: Optional[str] = None


# ====== 2. 加载权限数据 ======
# 获取包目录
package_dir = os.path.dirname(os.path.abspath(__file__))

# 全局变量，将在首次使用时初始化
operators_df = None
valid_operator_names = None
data_fields_dict = None
OP_PARAM_TYPES = None
valid_ops = None

# ====== 1. 加载 grammar 文件 ======
grammar_path = os.path.join(package_dir, "grammar.lark")
with open(grammar_path, "r") as f:
    grammar = f.read()

parser = Lark(grammar, start="start", parser="lalr")


def _load_data():
    """加载必要的数据文件"""
    global operators_df, valid_operator_names, data_fields_dict, valid_ops

    # 强制从用户配置目录加载数据，不使用包内置数据
    user_data_dir = os.path.expanduser("~/.wqb_validator/data")

    if not os.path.exists(user_data_dir):
        raise FileNotFoundError(
            f"数据目录不存在: {user_data_dir}\n"
            "请先运行 'wqb-data setup <email> <password>' 配置认证信息，\n"
            "然后运行 'wqb-data fetch' 下载数据。"
        )

    if operators_df is None:
        operators_file = os.path.join(user_data_dir, "operators.csv")
        if not os.path.exists(operators_file):
            raise FileNotFoundError(
                f"操作符文件不存在: {operators_file}\n"
                "请运行 'wqb-data fetch' 下载数据。"
            )
        operators_df = pd.read_csv(operators_file)
        valid_operator_names = set(operators_df["name"].dropna().unique())

    if data_fields_dict is None:
        data_fields_file = os.path.join(user_data_dir, "data_fields.json")
        if not os.path.exists(data_fields_file):
            raise FileNotFoundError(
                f"数据字段文件不存在: {data_fields_file}\n"
                "请运行 'wqb-data fetch' 下载数据。"
            )
        with open(data_fields_file, "r") as f:
            data_fields_dict = json.load(f)

    if valid_ops is None:
        valid_ops_file = os.path.join(user_data_dir, "valid_ops.json")
        if not os.path.exists(valid_ops_file):
            raise FileNotFoundError(
                f"操作符定义文件不存在: {valid_ops_file}\n"
                "请运行 'wqb-data fetch' 下载数据。"
            )
        with open(valid_ops_file, "r") as f:
            valid_ops = json.load(f)


# ====== 参数类型推断辅助 ======
def parse_param_type(param):
    param = param.strip()
    # 形如 x, y, z, input, group, field, alpha 等，视为 field/number
    if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", param):
        return "field_or_number"
    # 形如 "abc" 或 'abc'，视为 string
    if re.match(r'^".*"$|^\'.*\'$', param):
        return "string"
    # 形如 true/false
    if param in ["true", "false", "True", "False"]:
        return "bool"
    # 形如 1, 1.0, 0.5
    if re.match(r"^-?\d+(\.\d+)?$", param):
        return "number"
    # 形如 x=1, y="abc", filter=false
    if "=" in param:
        key, value = param.split("=", 1)
        return parse_param_type(value.strip())
    return "unknown"


def parse_operator_param_types(definition):
    """
    返回位置参数类型列表和命名参数类型dict
    """
    # 只取第一个括号内的参数
    m = re.search(r"\w+\(([^)]*)\)", definition)
    if not m:
        return [], {}
    params = m.group(1)
    param_list = [p.strip() for p in params.split(",") if p.strip()]
    pos_types = []
    kw_types = {}
    for p in param_list:
        if "=" in p:
            key, value = p.split("=", 1)
            kw_types[key.strip()] = parse_param_type(value.strip())
        else:
            pos_types.append(parse_param_type(p))
    return pos_types, kw_types


# 构建操作符参数类型映射
def operator_param_types_map():
    _load_data()  # 确保数据已加载
    mapping = {}
    for _, row in operators_df.iterrows():
        name = row["name"]
        definition = str(row["definition"])
        pos_types, kw_types = parse_operator_param_types(definition)
        mapping[name] = {"pos": pos_types, "kw": kw_types}
    return mapping


def get_op_param_types():
    """获取操作符参数类型映射，延迟初始化"""
    global OP_PARAM_TYPES
    if OP_PARAM_TYPES is None:
        OP_PARAM_TYPES = operator_param_types_map()
    return OP_PARAM_TYPES


# ====== 基础验证器类 ======


class BaseValidator:
    """基础验证器类"""

    def __init__(self):
        self.errors: List[ValidationError] = []
        self.warnings: List[str] = []

    def add_error(
        self,
        message: str,
        line: Optional[int] = None,
        column: Optional[int] = None,
        code: str = "",
        suggestion: Optional[str] = None,
    ):
        """添加验证错误"""
        self.errors.append(
            ValidationError(
                message=message,
                line=line,
                column=column,
                code=code,
                suggestion=suggestion,
            )
        )

    def add_warning(self, message: str):
        """添加警告信息"""
        self.warnings.append(message)

    def clear(self):
        """清除所有错误和警告"""
        self.errors.clear()
        self.warnings.clear()


# ====== 字符和格式验证器 ======


class CharacterValidator(BaseValidator):
    """字符和格式验证器"""

    def __init__(self):
        super().__init__()
        # 允许的字符模式
        self.allowed_pattern = re.compile(r'[a-zA-Z0-9_\s=+\-*/()><=!;.,"\'#]')
        # 标识符模式
        self.identifier_pattern = re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b")
        # 数字模式
        self.number_pattern = re.compile(r"\b\d+\.\d+\.\d+\b")
        # 连续操作符模式
        self.op_pattern = re.compile(r"[+\-*/]{2,}")

    def validate(self, expr: str) -> List[ValidationError]:
        """验证字符和格式"""
        self.clear()

        # 去除多行注释
        expr = re.sub(r"/\*.*?\*/", "", expr, flags=re.DOTALL)

        lines = expr.splitlines()
        for line_idx, line in enumerate(lines):
            line = line.rstrip()
            if line == "":
                continue

            # 跳过注释行
            stripped_line = line.strip()
            if stripped_line.startswith("#"):
                continue

            # 检查行内注释
            comment_pos = line.find("#")
            code_part = line[:comment_pos] if comment_pos != -1 else line

            # 验证字符
            self._validate_characters(code_part, line_idx + 1)

            # 验证标识符
            self._validate_identifiers(code_part, line_idx + 1)

            # 验证数字格式
            self._validate_numbers(code_part, line_idx + 1)

            # 验证操作符
            self._validate_operators(code_part, line_idx + 1)

            # 验证字符串
            self._validate_strings(code_part, line_idx + 1)

            # 验证括号匹配
            self._validate_brackets(code_part, line_idx + 1)

        return self.errors

    def _validate_characters(self, code_part: str, line_num: int):
        """验证非法字符"""
        for i, char in enumerate(code_part):
            if not self.allowed_pattern.match(char):
                self.add_error(
                    f"不支持字符 '{char}'",
                    line=line_num,
                    column=i + 1,
                    code=code_part,
                    suggestion="请使用标准ASCII字符",
                )

    def _validate_identifiers(self, code_part: str, line_num: int):
        """验证标识符格式"""
        # 检查以数字开头的标识符
        digit_start_pattern = re.compile(r"\b\d+[a-zA-Z_][a-zA-Z0-9_]*\b")
        for match in digit_start_pattern.finditer(code_part):
            identifier = match.group()
            self.add_error(
                f"标识符 '{identifier}' 不能以数字开头",
                line=line_num,
                column=match.start() + 1,
                code=code_part,
                suggestion="标识符应以字母或下划线开头",
            )

        # 检查连续下划线
        for match in self.identifier_pattern.finditer(code_part):
            identifier = match.group()
            if "__" in identifier:
                self.add_error(
                    f"标识符 '{identifier}' 不能包含连续下划线",
                    line=line_num,
                    column=match.start() + 1,
                    code=code_part,
                    suggestion="避免使用连续下划线",
                )

        return self.errors

    def _validate_numbers(self, code_part: str, line_num: int):
        """验证数字格式"""
        for match in self.number_pattern.finditer(code_part):
            number = match.group()
            self.add_error(
                f"数字 '{number}' 格式错误，不能有多个小数点",
                line=line_num,
                column=match.start() + 1,
                code=code_part,
                suggestion="数字只能有一个小数点",
            )

    def _validate_operators(self, code_part: str, line_num: int):
        """验证操作符使用"""
        for match in self.op_pattern.finditer(code_part):
            op = match.group()
            self.add_error(
                f"连续操作符 '{op}' 不合法",
                line=line_num,
                column=match.start() + 1,
                code=code_part,
                suggestion="请检查操作符使用是否正确",
            )

    def _validate_strings(self, code_part: str, line_num: int):
        """验证字符串格式"""
        quote_count = code_part.count('"') + code_part.count("'")
        if quote_count % 2 != 0:
            last_quote_pos = max(code_part.rfind('"'), code_part.rfind("'"))
            if last_quote_pos != -1:
                self.add_error(
                    f"字符串未闭合",
                    line=line_num,
                    column=last_quote_pos + 1,
                    code=code_part,
                    suggestion="请检查引号是否配对",
                )

    def _validate_brackets(self, code_part: str, line_num: int):
        """验证括号匹配"""
        stack = []

        for i, char in enumerate(code_part):
            if char == "(":
                stack.append(("(", i))
            elif char == ")":
                if stack and stack[-1][0] == "(":
                    stack.pop()
                else:
                    self.add_error(
                        "括号不匹配，多余的右括号",
                        line=line_num,
                        column=i + 1,
                        code=code_part,
                        suggestion="请检查括号数量",
                    )
                    break

        # 检查未闭合的左括号
        if stack:
            last_open_pos = stack[-1][1]
            self.add_error(
                "括号不匹配，缺少右括号",
                line=line_num,
                column=last_open_pos + 1,
                code=code_part,
                suggestion="请添加缺失的右括号",
            )


# ====== 语法验证器 ======


class SyntaxValidator(BaseValidator):
    """语法验证器"""

    def __init__(self, grammar_file: str = None):
        super().__init__()
        if grammar_file is None:
            # 获取包目录
            package_dir = os.path.dirname(os.path.abspath(__file__))
            grammar_file = os.path.join(package_dir, "grammar.lark")

        with open(grammar_file, "r") as f:
            grammar = f.read()
        self.parser = Lark(grammar, start="start", parser="lalr")

    def validate(self, expr: str) -> List[ValidationError]:
        """验证语法"""
        self.clear()

        try:
            tree = self.parser.parse(expr)
            return self.errors
        except exceptions.LarkError as e:
            msg = str(e)
            line_no, col_no = self._extract_error_position(msg)

            if line_no and col_no:
                error_lines = expr.splitlines()
                if line_no <= len(error_lines):
                    error_line = error_lines[line_no - 1]
                    error_msg = self._get_error_message(msg)

                    self.add_error(
                        error_msg,
                        line=line_no,
                        column=col_no,
                        code=error_line,
                        suggestion=self._get_suggestion(msg),
                    )
            else:
                self.add_error(f"语法错误: {msg}", suggestion="请检查表达式语法")

        return self.errors

    def _extract_error_position(
        self, error_msg: str
    ) -> Tuple[Optional[int], Optional[int]]:
        """提取错误位置"""
        m = re.search(r"at line (\d+), column (\d+)", error_msg)
        if m:
            return int(m.group(1)), int(m.group(2))
        return None, None

    def _get_error_message(self, error_msg: str) -> str:
        """获取错误消息"""
        if "Expected one of:" in error_msg and "* SEMICOLON" in error_msg:
            return "缺少分号"
        elif (
            "Expected one of:" in error_msg
            and "CNAME" in error_msg
            and "(" in error_msg
        ):
            return "函数调用语法错误"
        elif "Expected one of:" in error_msg and "RPAR" in error_msg:
            return "括号不匹配"
        elif "Expected one of:" in error_msg and "EQUAL" in error_msg:
            return "赋值语句语法错误"
        else:
            return "语法错误"

    def _get_suggestion(self, error_msg: str) -> str:
        """获取修复建议"""
        if "SEMICOLON" in error_msg:
            return "请在语句末尾添加分号"
        elif "RPAR" in error_msg:
            return "请检查括号是否配对"
        elif "EQUAL" in error_msg:
            return "请检查赋值语句格式"
        else:
            return "请检查表达式语法"


# ====== 业务规则验证器 ======


class BusinessRuleValidator(BaseValidator):
    """业务规则验证器"""

    def __init__(self):
        super().__init__()

    def validate(self, expr: str) -> List[ValidationError]:
        """验证业务规则"""
        self.clear()

        # 检查赋值语句规则
        self._check_assignment_rules(expr)

        # 检查表达式结构规则
        self._check_expression_structure(expr)

        return self.errors

    def _check_assignment_rules(self, expr: str):
        """检查赋值语句规则"""
        lines = expr.splitlines()
        for line_idx, line in enumerate(lines):
            line = line.strip()
            if line == "" or line.startswith("#"):
                continue

            # 按分号分割语句
            statements = [s.strip() for s in line.split(";") if s.strip()]
            if len(statements) > 1:
                # 检查非最后一条语句
                for stmt in statements[:-1]:
                    if "=" in stmt:
                        # 非最后一条语句可以是赋值语句
                        pass

                # 检查最后一条语句
                last_stmt = statements[-1]
                if "=" in last_stmt:
                    # 检查是否是函数调用中的命名参数
                    equal_pos = last_stmt.find("=")
                    if equal_pos > 0:
                        before_equal = last_stmt[:equal_pos].strip()
                        if "(" in before_equal:
                            # 这是函数调用中的命名参数，不是赋值语句
                            pass
                        else:
                            # 检查等号左边是否是有效的变量名
                            if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", before_equal):
                                self.add_error(
                                    f"'{last_stmt}' 不能是赋值语句",
                                    line=line_idx + 1,
                                    code=line,
                                    suggestion="最后一行应该是表达式，不能是赋值语句",
                                )

    def _check_expression_structure(self, expr: str):
        """检查表达式结构规则"""
        # 检查是否为空表达式
        if not expr.strip():
            self.add_error("表达式不能为空", suggestion="请提供有效的表达式")

        # 检查是否包含必要的表达式
        lines = [
            line.strip()
            for line in expr.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]

        if not lines:
            self.add_error(
                "没有找到有效的表达式行", suggestion="请提供至少一行有效的表达式"
            )


# ====== 注释过滤处理 ======


def filter_comments(expr: str) -> str:
    """过滤注释，只保留代码部分"""
    # 1. 去除多行注释 /* ... */
    expr = re.sub(r"/\*.*?\*/", "", expr, flags=re.DOTALL)

    # 2. 去除单行注释 # ...
    lines = expr.splitlines()
    filtered_lines = []
    for line in lines:
        comment_pos = line.find("#")
        if comment_pos != -1:
            # 只保留注释前的代码部分
            filtered_lines.append(line[:comment_pos])
        else:
            filtered_lines.append(line)

    return "\n".join(filtered_lines)


# ====== 数据字段验证器 ======


class DataFieldValidator(BaseValidator):
    """数据字段验证器"""

    def __init__(self, valid_fields: Set[str]):
        super().__init__()
        self.valid_fields = valid_fields

    def validate(self, expr: str) -> List[ValidationError]:
        """验证数据字段是否有效"""
        self.clear()

        # 提取表达式中的所有字段引用
        field_references = self._extract_field_references(expr)

        # 验证每个字段
        for field_ref in field_references:
            if field_ref not in self.valid_fields:
                self.add_error(
                    f"无效数据字段: {field_ref}",
                    suggestion="请检查字段名拼写，或查看可用字段列表",
                )

        return self.errors

    def _extract_field_references(self, expr: str) -> Set[str]:
        """提取表达式中的所有字段引用"""
        # 简单的字段名提取（可以后续优化为AST解析）
        # 匹配形如 field_name 的标识符，排除函数名、变量名和操作符
        field_pattern = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b")
        matches = field_pattern.findall(expr)

        # 过滤掉函数名（带括号的）、已知的操作符和变量名
        fields = set()
        for match in matches:
            # 检查是否是函数调用
            if not self._is_function_call(match, expr):
                # 检查是否是操作符
                if not self._is_operator(match):
                    # 检查是否是变量名（在赋值语句左边或函数参数中）
                    if not self._is_variable_name(match, expr):
                        fields.add(match)

        return fields

    def _is_variable_name(self, name: str, expr: str) -> bool:
        """检查是否是变量名"""
        # 检查是否在赋值语句左边
        assignment_pattern = re.compile(rf"\b{re.escape(name)}\s*=")
        if assignment_pattern.search(expr):
            return True

        # 检查是否在函数参数中作为命名参数
        named_param_pattern = re.compile(rf"{re.escape(name)}\s*=")
        if named_param_pattern.search(expr):
            return True

        # 检查是否是布尔值
        if name.lower() in ["true", "false"]:
            return True

        return False

    def _is_function_call(self, name: str, expr: str) -> bool:
        """检查是否是函数调用"""
        # 简单的检查：名字后面是否有左括号
        pattern = re.compile(rf"\b{re.escape(name)}\s*\(")
        return pattern.search(expr) is not None

    def _is_operator(self, name: str) -> bool:
        """检查是否是操作符"""
        # 从全局的valid_ops中检查是否是操作符
        return name in valid_ops


# ====== 操作符验证器 ======


class OperatorValidator(BaseValidator):
    """操作符验证器"""

    def __init__(self, operators_data: Dict[str, Any]):
        super().__init__()
        self.operators_data = operators_data

    def validate(self, expr: str) -> List[ValidationError]:
        """验证操作符使用是否正确"""
        self.clear()

        # 提取表达式中的所有函数调用
        function_calls = self._extract_function_calls(expr)

        # 验证每个函数调用
        for func_call in function_calls:
            self._validate_function_call(func_call)

        return self.errors

    def _extract_function_calls(self, expr: str) -> List[Dict[str, Any]]:
        """提取表达式中的所有函数调用"""
        # 简单的函数调用提取（可以后续优化为AST解析）
        function_calls = []

        # 匹配形如 function_name(arg1, arg2, ...) 的模式
        pattern = re.compile(r"(\w+)\s*\(([^)]*)\)")
        matches = pattern.finditer(expr)

        for match in matches:
            func_name = match.group(1)
            args_str = match.group(2)

            # 解析参数
            args = self._parse_arguments(args_str)

            function_calls.append(
                {
                    "name": func_name,
                    "args": args,
                    "position": match.start(),
                    "full_match": match.group(0),
                }
            )

        return function_calls

    def _parse_arguments(self, args_str: str) -> List[Dict[str, Any]]:
        """解析函数参数"""
        if not args_str.strip():
            return []

        args = []
        # 简单的参数分割（可以后续优化）
        arg_parts = [part.strip() for part in args_str.split(",")]

        for i, part in enumerate(arg_parts):
            if "=" in part:
                # 命名参数
                key, value = part.split("=", 1)
                args.append(
                    {
                        "type": "keyword",
                        "name": key.strip(),
                        "value": value.strip(),
                        "position": i,
                    }
                )
            else:
                # 位置参数
                args.append(
                    {"type": "positional", "value": part.strip(), "position": i}
                )

        return args

    def _validate_function_call(self, func_call: Dict[str, Any]):
        """验证单个函数调用"""
        op_name = func_call["name"]
        args = func_call["args"]

        # 1. 检查操作符是否存在
        if op_name not in self.operators_data:
            self.add_error(
                f"未知操作符: {op_name}", suggestion="请检查操作符名称是否正确"
            )
            return

        op_info = self.operators_data[op_name]

        # 2. 检查参数数量
        min_args = op_info.get("min_args", 0)
        max_args = op_info.get("max_args")

        positional_args = [arg for arg in args if arg["type"] == "positional"]

        if len(positional_args) < min_args:
            self.add_error(
                f"{op_name} 参数不足: 至少需要 {min_args} 个，实际为 {len(positional_args)}",
                suggestion=f"请提供至少 {min_args} 个参数",
            )

        if max_args and len(positional_args) > max_args:
            self.add_error(
                f"{op_name} 参数过多: 最多允许 {max_args} 个，实际为 {len(positional_args)}",
                suggestion=f"请减少参数数量到 {max_args} 个以内",
            )

        # 3. 检查命名参数
        if "kwarg_types" in op_info:
            for arg in args:
                if arg["type"] == "keyword":
                    if arg["name"] not in op_info["kwarg_types"]:
                        self.add_error(
                            f"{op_name} 不支持命名参数: {arg['name']}",
                            suggestion=f"支持的命名参数: {list(op_info['kwarg_types'].keys())}",
                        )


# ====== 3. 验证器类（用于 AST 遍历） ======
class ExprValidator(Transformer):
    def __init__(self, valid_field_names):
        super().__init__()
        self.errors = []
        self.valid_field_names = valid_field_names
        self.debug_mode = False  # 调试模式开关
        self.variables = {}  # 变量作用域
        self.variable_exprs = {}  # 变量表达式链路

    def _resolve_variable_type(self, var_name, visited=None):
        """递归查找变量真实类型，防止类型链断裂，递归表达式所有子节点"""
        if visited is None:
            visited = set()
        if var_name in visited:
            return "unknown"  # 防止循环引用
        visited.add(var_name)
        t = self.variables.get(var_name, "unknown")
        if t != "unknown":
            return t
        # 如果有表达式链，递归查找
        expr = self.variable_exprs.get(var_name)
        if expr is not None:
            expr_type = self._get_node_type(expr, visited)
            if expr_type != "unknown":
                return expr_type
            # 如果表达式是 dict 或 lark tree，递归所有子节点
            if isinstance(expr, dict):
                for v in expr.values():
                    sub_type = None
                    if isinstance(v, str) and v in self.variables:
                        sub_type = self._resolve_variable_type(v, visited)
                    else:
                        sub_type = self._get_node_type(v, visited)
                    if sub_type != "unknown":
                        return sub_type
            elif hasattr(expr, "children"):
                for child in expr.children:
                    sub_type = self._get_node_type(child, visited)
                    if sub_type != "unknown":
                        return sub_type
        return "unknown"

    def assignment_stmt(self, args):
        """处理赋值语句"""
        assignment_tuple = args[0]
        var_name = assignment_tuple[0]
        value = assignment_tuple[1]

        # 检查变量名是否包含中文字符
        import re

        chinese_pattern = re.compile(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]")
        if chinese_pattern.search(var_name):
            self.errors.append(f"变量名 '{var_name}' 包含中文字符，不支持")

        # 检查变量名是否与操作符冲突
        if var_name in valid_ops:
            self.errors.append(f"变量名 '{var_name}' 与操作符名冲突")
            return None

        # 检查变量名是否为数据字段
        if var_name in self.valid_field_names:
            self.errors.append(f"字段名 '{var_name}' 不能作为变量名")
            return None

        # 递归推断右侧表达式类型
        inferred_type = self._get_node_type(value)
        self.variables[var_name] = inferred_type
        self.variable_exprs[var_name] = value  # 记录表达式链
        if self.debug_mode:
            print(f"变量 {var_name} 被推断为类型: {inferred_type}")

        return None  # 赋值语句不返回值

    def expr_stmt(self, args):
        """处理表达式语句（带分号）"""
        return None  # 带分号的表达式不返回值

    def final_expr(self, args):
        """处理最终表达式（最后一行，无分号）"""
        return args[0]

    def assignment(self, args):
        """处理赋值语法"""
        var_name = str(args[0])
        value = args[1]
        return (var_name, value)

    def function(self, args):
        name = str(args[0])

        # 检查操作符名是否包含中文字符
        import re

        chinese_pattern = re.compile(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]")
        if chinese_pattern.search(name):
            self.errors.append(f"操作符名 '{name}' 包含中文字符，不支持")

        if len(args) == 1:
            num_args = 0
            arg_nodes = []
        else:
            args_node = args[1]
            if hasattr(args_node, "children"):
                arg_nodes = args_node.children
                num_args = len(arg_nodes)
            else:
                arg_nodes = args[1:]
                num_args = len(arg_nodes)

        if name not in valid_ops:
            # 简洁错误信息，无建议
            error_msg = f"未知操作符: {name}"
            self.errors.append(error_msg)
            return {"type": "function_call", "name": name, "return_type": "unknown"}

        op = valid_ops[name]
        min_args = op["min_args"]
        max_args = op.get("max_args")

        pos_types = op.get("arg_types", [])
        kw_types = op.get("kwarg_types", {})
        var_args_type = op.get("var_args_type")  # 可变参数类型

        # 分别计算位置参数和命名参数
        pos_args = []
        kw_args = []

        for node in arg_nodes:
            if hasattr(node, "data") and node.data == "kwarg":
                kw_args.append(node)
            else:
                pos_args.append(node)

        # 检查位置参数数量
        if len(pos_args) < min_args:
            self.errors.append(
                f"{name} 位置参数不足: 至少需要 {min_args} 个，实际为 {len(pos_args)}"
            )
        if max_args is not None and len(pos_args) > max_args:
            self.errors.append(
                f"{name} 位置参数过多: 最多允许 {max_args} 个，实际为 {len(pos_args)}"
            )

        # 检查位置参数类型
        for i, node in enumerate(pos_args):
            if i < len(pos_types):
                # 固定位置参数
                expect_type = pos_types[i]
                actual_type = self._get_node_type(node)
                if not self._is_type_compatible(expect_type, actual_type):
                    self.errors.append(
                        f"{name} 的第{i+1}个位置参数类型应为 {expect_type}，实际为 {actual_type}"
                    )
            elif var_args_type:
                # 可变参数，使用 var_args_type
                expect_type = var_args_type
                actual_type = self._get_node_type(node)
                if not self._is_type_compatible(expect_type, actual_type):
                    self.errors.append(
                        f"{name} 的第{i+1}个可变参数类型应为 {expect_type}，实际为 {actual_type}"
                    )
            elif len(pos_types) > 0:
                # 对于可变参数，使用最后一个类型定义
                expect_type = pos_types[-1]
                actual_type = self._get_node_type(node)
                if not self._is_type_compatible(expect_type, actual_type):
                    self.errors.append(
                        f"{name} 的第{i+1}个位置参数类型应为 {expect_type}，实际为 {actual_type}"
                    )

        # 检查命名参数
        for node in kw_args:
            key = str(node.children[0])
            value_node = node.children[1]
            expect_type = kw_types.get(key)
            # 检查参数名是否合法
            if key not in kw_types:
                self.errors.append(f"{name} 的参数 `{key}` 不是有效参数名")
                continue
            actual_type = self._get_node_type(value_node)
            if expect_type and not self._is_type_compatible(expect_type, actual_type):
                self.errors.append(
                    f"{name} 的参数 `{key}` 类型应为 {expect_type}，实际为 {actual_type}"
                )

        # 检查参数值选择
        choices = op.get("choices", {})
        if choices and len(args) > 1:
            args_node = args[1]
            if hasattr(args_node, "children"):
                for child in args_node.children:
                    if (
                        hasattr(child, "data")
                        and child.data == "kwarg"
                        and len(child.children) == 2
                    ):
                        key_node, value_node = child.children
                        key = str(key_node)
                        # 提取字符串值
                        if hasattr(value_node, "data") and value_node.data == "string":
                            value = str(value_node.children[0]).strip('"')
                        else:
                            value = str(value_node).strip('"')
                        if key in choices and value not in choices[key]:
                            self.errors.append(
                                f"{name} 的参数 `{key}` 不合法：{value}，应为 {choices[key]}"
                            )

        # 返回函数调用的返回类型
        return_type = op.get("return_type", "unknown")
        return {"type": "function_call", "name": name, "return_type": return_type}

    def field(self, token):
        field_name = str(token[0])

        # 检查字段名是否包含中文字符
        import re

        chinese_pattern = re.compile(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]")
        if chinese_pattern.search(field_name):
            self.errors.append(f"字段名 '{field_name}' 包含中文字符，不支持")

        # 处理布尔字面量
        if field_name in ["true", "false", "True", "False"]:
            return {"type": "boolean", "name": field_name, "return_type": "boolean"}

        # 首先检查是否是变量
        if field_name in self.variables:
            return {
                "type": "variable",
                "name": field_name,
                "return_type": self.variables[field_name],
            }
        elif field_name in self.valid_field_names:
            return {"type": "field", "name": field_name, "return_type": "field"}
        else:
            # 简洁错误信息，无建议
            error_msg = f"未知字段: {field_name}"
            self.errors.append(error_msg)
            return {"type": "field", "name": field_name, "return_type": "unknown"}

    def _is_type_compatible(self, expected, actual):
        """检查类型兼容性"""
        # 支持 expected 为数组（多类型兼容）
        if isinstance(expected, list):
            return any(self._is_type_compatible(e, actual) for e in expected)

        if expected == actual:
            return True

        # expr 兼容 field（表达式可以接受字段/变量）
        if expected == "expr" and actual == "field":
            return True

        # field 只兼容 field（字段参数不能接受表达式）
        if expected == "field" and actual == "field":
            return True

        # number 兼容 number
        if expected == "number" and actual == "number":
            return True

        # string 兼容 string
        if expected == "string" and actual == "string":
            return True

        # boolean 兼容 boolean
        if expected == "boolean" and actual == "boolean":
            return True

        # boolean 兼容 expr（布尔表达式可以接受任何表达式）
        if expected == "boolean" and actual in ["expr", "field", "number"]:
            return True

        return False

    def _get_node_type(self, node, visited=None):
        from lark.lexer import Token

        if visited is None:
            visited = set()

        if isinstance(node, Token):
            if node.type == "SIGNED_NUMBER":
                return "number"
            if node.type == "ESCAPED_STRING":
                return "string"
            if node.type == "BOOLEAN":
                return "boolean"
            if node.type == "CNAME":
                val = str(node)
                if val in ["true", "false", "True", "False"]:
                    return "boolean"
                # 检查是否是变量
                if hasattr(self, "variables") and val in self.variables:
                    t = self.variables[val]
                    if t == "unknown":
                        # 递归查找真实类型
                        return self._resolve_variable_type(val, visited)
                    return t
                # 检查是否是有效字段
                if hasattr(self, "valid_field_names") and val in self.valid_field_names:
                    return "field"
                # 不是有效字段名，返回 unknown
                return "unknown"
        elif hasattr(node, "data"):
            if node.data == "number":
                return "number"
            if node.data == "string":
                return "string"
            if node.data == "boolean":
                return "boolean"
            if node.data == "field":
                # field 规则下只有一个子节点，直接递归
                child_type = self._get_node_type(node.children[0], visited)
                # 如果子节点是布尔字面量，直接返回boolean
                if isinstance(node.children[0], Token) and str(node.children[0]) in [
                    "true",
                    "false",
                    "True",
                    "False",
                ]:
                    return "boolean"
                if child_type == "field":
                    return "field"
                elif child_type in ["expr", "number", "string", "boolean"]:
                    return child_type
                return child_type
            if node.data == "function":
                # 函数调用，返回其返回类型
                if hasattr(node, "return_type"):
                    return node.return_type
                if (
                    node.children
                    and hasattr(node.children[0], "type")
                    and node.children[0].type == "CNAME"
                ):
                    func_name = str(node.children[0])
                    if func_name in valid_ops:
                        return valid_ops[func_name].get("return_type", "unknown")
                return "unknown"
            # 处理嵌套的表达式节点
            if node.data in [
                "expr",
                "logic_or",
                "logic_and",
                "logic_not",
                "comparison",
                "unary_expr",
                "atom",
            ]:
                if node.children:
                    return self._get_node_type(node.children[0], visited)
            elif node.data in ["add_expr", "mul_expr"]:
                # 算术运算的类型推断
                if len(node.children) >= 3:  # 左操作数 操作符 右操作数
                    left_type = self._get_node_type(node.children[0], visited)
                    right_type = self._get_node_type(node.children[2], visited)
                    # 只要有一个是unknown，且另一个不是expr/field，结果unknown
                    if left_type == "unknown" and right_type == "unknown":
                        return "unknown"
                    # 只要有一个是expr或field，结果就是expr
                    if left_type in ["expr", "field"] or right_type in [
                        "expr",
                        "field",
                    ]:
                        return "expr"
                    # 如果都是number，结果是number
                    if left_type == "number" and right_type == "number":
                        return "number"
                    # 其它情况，返回expr
                    return "expr"
                elif node.children:
                    return self._get_node_type(node.children[0], visited)
            elif node.data in ["greater", "greater_eq", "less", "less_eq", "eq", "neq"]:
                # 比较操作符返回boolean类型
                return "boolean"
        elif isinstance(node, dict):
            # 处理函数调用返回的字典
            if node.get("type") == "function_call":
                return node.get("return_type", "unknown")
            elif node.get("type") == "field":
                return "field"
            elif node.get("type") == "variable":
                # 递归查找变量真实类型
                var_name = node.get("name")
                return self._resolve_variable_type(var_name, visited)
            elif node.get("type") == "boolean":
                return "boolean"
            else:
                return node.get("return_type", "unknown")
        return "unknown"


# ====== 4. 表达式验证器类 ======
class ExpressionValidator:
    """
    表达式验证器类

    初始化时设置地区、延迟和股票池参数，后续验证时只需传入表达式
    """

    def __init__(self, region: str, delay: int, universe: str):
        """
        初始化验证器

        :param region: 地区 (如 USA, CHN, EUR)
        :param delay: 延迟天数 (如 0, 1)
        :param universe: 股票池 (如 TOP500, TOP1000, TOP3000)
        """
        self.region = region
        self.delay = delay
        self.universe = universe
        self.combination_key = f"{region}_{delay}_{universe}"

        # 确保数据已加载
        _load_data()

        # 验证组合参数是否有效
        if self.combination_key not in data_fields_dict:
            # 获取可用的组合参数
            available_keys = list(data_fields_dict.keys())
            available_keys.sort()

            # 构建简洁的错误信息
            error_msg = f"无效参数组合: {self.combination_key}\n"
            error_msg += "可用组合:\n"

            # 按地区分组显示，更简洁
            regions = {}
            for key in available_keys:
                parts = key.split("_")
                if len(parts) >= 3:
                    r, d, u = parts[0], parts[1], "_".join(parts[2:])
                    if r not in regions:
                        regions[r] = []
                    regions[r].append(f"{d}/{u}")

            for region_name, configs in regions.items():
                error_msg += f"  {region_name}: {', '.join(configs)}\n"

            raise ValueError(error_msg)

        # 获取对应的数据字段
        self.valid_field_names = set(data_fields_dict[self.combination_key])

        # 初始化各个验证器
        self.character_validator = CharacterValidator()
        self.syntax_validator = SyntaxValidator()
        self.business_validator = BusinessRuleValidator()
        self.operator_validator = OperatorValidator(valid_ops)
        self.data_field_validator = DataFieldValidator(self.valid_field_names)

    def validate(self, expr: str):
        """
        验证表达式是否合法

        :param expr: 表达式字符串
        :return: (是否通过验证: bool, 错误列表: List[str])
        """
        all_errors = []

        # 1. 注释过滤 - 先过滤注释，再验证代码
        filtered_expr = filter_comments(expr)

        # 2. 字符验证
        char_errors = self.character_validator.validate(filtered_expr)
        all_errors.extend(char_errors)

        # 3. 标识符验证
        id_errors = self.character_validator._validate_identifiers(filtered_expr, 0)
        all_errors.extend(id_errors)

        # 4. 语法验证
        syntax_errors = self.syntax_validator.validate(filtered_expr)
        all_errors.extend(syntax_errors)

        # 5. 操作符验证
        op_errors = self.operator_validator.validate(filtered_expr)
        all_errors.extend(op_errors)

        # 6. 数据字段验证
        field_errors = self.data_field_validator.validate(filtered_expr)
        all_errors.extend(field_errors)

        # 7. 业务规则验证
        business_errors = self.business_validator.validate(filtered_expr)
        all_errors.extend(business_errors)

        # 如果有错误，返回错误信息
        if all_errors:
            error_messages = []
            for error in all_errors:
                error_msg = error.message
                if error.line and error.column:
                    error_msg = f"第{error.line}行第{error.column}列: {error.message}"
                if error.suggestion:
                    error_msg += f" ({error.suggestion})"
                error_messages.append(error_msg)
            return False, error_messages

        return True, []

    # 删除不再使用的方法

    def get_valid_fields(self):
        """
        获取当前配置下的有效字段列表

        :return: 有效字段集合
        """
        return self.valid_field_names.copy()

    def get_config(self):
        """
        获取当前验证器配置

        :return: 配置字典
        """
        return {
            "region": self.region,
            "delay": self.delay,
            "universe": self.universe,
            "combination_key": self.combination_key,
            "valid_fields_count": len(self.valid_field_names),
        }


# ====== 5. 向后兼容的函数 ======
def validate_expression(expr: str, region: str, delay: int, universe: str):
    """
    验证表达式是否合法（向后兼容函数）

    :param expr: 表达式字符串
    :param region: 地区 (如 USA, CHN, EUR)
    :param delay: 延迟天数 (如 0, 1)
    :param universe: 股票池 (如 TOP500, TOP1000, TOP3000)
    :return: (是否通过验证: bool, 错误列表: List[str])
    """
    validator = ExpressionValidator(region, delay, universe)
    return validator.validate(expr)
