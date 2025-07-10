import json
import pandas as pd
from lark import Lark, Transformer, exceptions
import re
import os

from utils.fetch_data import DATA_DIR

# ====== 2. 加载权限数据 ======
with open("validator/valid_ops.json", "r") as f:
    valid_ops = json.load(f)

# 全局变量，将在首次使用时初始化
operators_df = None
valid_operator_names = None
data_fields_dict = None
OP_PARAM_TYPES = None

# ====== 1. 加载 grammar 文件 ======
with open("validator/grammar.lark", "r") as f:
    grammar = f.read()

parser = Lark(grammar, start="start", parser="lalr")


def _load_data():
    """加载必要的数据文件"""
    global operators_df, valid_operator_names, data_fields_dict

    if operators_df is None:
        operators_file = f"{DATA_DIR}/operators.csv"
        if not os.path.exists(operators_file):
            raise FileNotFoundError(f"操作符文件不存在: {operators_file}")
        operators_df = pd.read_csv(operators_file)
        valid_operator_names = set(operators_df["name"].dropna().unique())

    if data_fields_dict is None:
        data_fields_file = f"{DATA_DIR}/data_fields.json"
        if not os.path.exists(data_fields_file):
            raise FileNotFoundError(f"数据字段文件不存在: {data_fields_file}")
        with open(data_fields_file, "r") as f:
            data_fields_dict = json.load(f)


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
            # 提供简洁的错误信息
            error_msg = f"未知操作符: {name}"

            # 查找相似的操作符名
            similar_ops = []
            for op_name in valid_ops.keys():
                if name.lower() in op_name.lower() or op_name.lower() in name.lower():
                    similar_ops.append(op_name)
                    if len(similar_ops) >= 3:  # 最多显示3个建议
                        break

            if similar_ops:
                error_msg += f" (建议: {', '.join(similar_ops)})"

            self.errors.append(error_msg)
            return {"type": "function_call", "name": name, "return_type": "unknown"}

        op = valid_ops[name]
        min_args = op["min_args"]
        max_args = op.get("max_args")

        pos_types = op.get("arg_types", [])
        kw_types = op.get("kwarg_types", {})

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
                expect_type = pos_types[i]
                actual_type = self._get_node_type(node)
                if not self._is_type_compatible(expect_type, actual_type):
                    self.errors.append(
                        f"{name} 的第{i+1}个位置参数类型应为 {expect_type}，实际为 {actual_type}"
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
            # 提供简洁的错误信息
            error_msg = f"未知字段: {field_name}"

            # 如果是变量名，提供建议
            if field_name not in self.variables:
                # 查找相似的字段名
                similar_fields = []
                for valid_field in self.valid_field_names:
                    if (
                        field_name.lower() in valid_field.lower()
                        or valid_field.lower() in field_name.lower()
                    ):
                        similar_fields.append(valid_field)
                        if len(similar_fields) >= 3:  # 最多显示3个建议
                            break

                if similar_fields:
                    error_msg += f" (建议: {', '.join(similar_fields)})"

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
            if node.data == "field":
                # field 规则下只有一个子节点，直接递归
                child_type = self._get_node_type(node.children[0], visited)
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

    def validate(self, expr: str):
        """
        验证表达式是否合法

        :param expr: 表达式字符串
        :return: (是否通过验证: bool, 错误列表: List[str])
        """
        # 检查中文字符
        chinese_errors = self._check_chinese_characters(expr)
        if chinese_errors:
            return False, chinese_errors

        # 只保留非空、非注释行
        lines = expr.splitlines()
        filtered_lines = []
        for line in lines:
            l = line.strip()
            if l == "" or l.startswith("#"):
                continue
            filtered_lines.append(line)
        filtered_expr = "\n".join(filtered_lines)

        # 支持多行注释过滤
        import re

        filtered_expr = re.sub(r"/\*.*?\*/", "", filtered_expr, flags=re.DOTALL)

        # 业务规则校验：检查赋值语句
        if filtered_lines:
            # 按分号分割语句
            all_statements = []
            for line_idx, line in enumerate(filtered_lines):
                statements = [s.strip() for s in line.split(";") if s.strip()]
                for stmt in statements:
                    all_statements.append((line_idx + 1, stmt))

            if len(all_statements) > 1:
                # 检查非最后一条语句 - 允许表达式语句（带分号）
                for line_idx, stmt in all_statements[:-1]:
                    # 非最后一条语句可以是赋值语句或表达式语句
                    pass
            # 检查最后一条语句（无论多少条）
            last_line_idx, last_stmt = all_statements[-1]
            # 更精确地检查是否为赋值语句：变量名 = 表达式
            # 排除函数调用中的命名参数
            if "=" in last_stmt:
                # 检查是否是函数调用中的命名参数
                # 如果等号前有左括号，说明是函数调用中的命名参数
                equal_pos = last_stmt.find("=")
                if equal_pos > 0:
                    before_equal = last_stmt[:equal_pos].strip()
                    # 检查等号前是否有左括号，如果有则不是赋值语句
                    if "(" in before_equal:
                        # 这是函数调用中的命名参数，不是赋值语句
                        pass
                    else:
                        # 检查等号左边是否是有效的变量名
                        if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", before_equal):
                            error_lines = filtered_expr.splitlines()
                            if last_line_idx <= len(error_lines):
                                error_line = error_lines[last_line_idx - 1]
                                stmt_start = error_line.find(last_stmt)
                                if stmt_start >= 0:
                                    marker = " " * stmt_start + "^"
                                    return False, [
                                        f"'{last_stmt}' 不能是赋值语句",
                                        error_line,
                                        marker,
                                    ]
                            return False, [f"'{last_stmt}' 不能是赋值语句"]

        # 语法和字符检查都通过，进行语义检查
        try:
            tree = parser.parse(filtered_expr)
            validator = ExprValidator(self.valid_field_names)
            # 使用 transform 处理整个程序，保证变量作用域正确
            result = validator.transform(tree)

            if validator.errors:
                return False, validator.errors
            return True, []

        except exceptions.LarkError as e:
            msg = str(e)
            import re

            m = re.search(r"at line (\d+), column (\d+)", msg)
            line_no = col_no = None
            if m:
                line_no = int(m.group(1))
                col_no = int(m.group(2))
            else:
                # 尝试用 Lark 的异常属性
                if hasattr(e, "line") and hasattr(e, "column"):
                    line_no = e.line
                    col_no = e.column
            if line_no and col_no:
                error_lines = filtered_expr.splitlines()
                if line_no <= len(error_lines):
                    error_line = error_lines[line_no - 1]
                    # 根据错误类型给出更准确的提示
                    if "Expected one of:" in msg and "* SEMICOLON" in msg:
                        error_msg = f"第{line_no}行缺少分号"
                    elif "Expected one of:" in msg and "CNAME" in msg and "(" in msg:
                        error_msg = f"第{line_no}行函数调用语法错误"
                    elif "Expected one of:" in msg and "RPAR" in msg:
                        error_msg = f"第{line_no}行括号不匹配"
                    elif "Expected one of:" in msg and "EQUAL" in msg:
                        error_msg = f"第{line_no}行赋值语句语法错误"
                    else:
                        error_msg = f"第{line_no}行语法错误"
                    # 生成位置标记
                    marker_pos = min(max(col_no - 1, 0), len(error_line))
                    marker = " " * marker_pos + "^"
                    return False, [error_msg, error_line, marker]
            # 如果还是没有行号列号，直接显示原始错误
            return False, [f"语法错误: {msg}"]

        except Exception as e:
            return False, [f"验证过程中发生错误: {str(e)}"]

    def _check_chinese_characters(self, expr: str):
        """
        检查表达式中是否包含非法字符和格式（忽略注释）

        :param expr: 表达式字符串
        :return: 错误列表
        """
        import re

        # 先去除多行注释
        expr = re.sub(r"/\*.*?\*/", "", expr, flags=re.DOTALL)

        errors = []

        # 定义允许的字符模式
        # 允许：字母数字、下划线、等号、操作符符号、分号、空格、点号、逗号、引号
        allowed_pattern = re.compile(r'[a-zA-Z0-9_\s=+\-*/()><=!;.,"\'#]')

        # 按行检查
        lines = expr.splitlines()
        for line_idx, line in enumerate(lines):
            line = line.rstrip()  # 保留前导空格，去除尾随空格
            if line == "":
                continue

            # 检查是否是注释行
            stripped_line = line.strip()
            if stripped_line.startswith("#"):
                continue  # 跳过注释行

            # 检查行内注释，只检查注释前的部分
            comment_pos = line.find("#")
            if comment_pos != -1:
                # 只检查注释前的部分
                code_part = line[:comment_pos]
            else:
                code_part = line

            # 1. 查找非法字符
            for i, char in enumerate(code_part):
                if not allowed_pattern.match(char):
                    # 生成位置标记
                    marker_pos = min(max(i, 0), len(line))
                    marker = " " * marker_pos + "^"
                    errors.append(f"不支持字符 '{char}' 在位置 ({line_idx + 1}:{i+1})")
                    errors.append(line)
                    errors.append(marker)

            # 2. 检查变量名/字段名/函数名规则
            # 不能以数字开头，不能包含连续下划线
            identifier_pattern = re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b")
            identifiers = identifier_pattern.finditer(code_part)
            for match in identifiers:
                identifier = match.group()
                # 检查是否以数字开头
                if identifier[0].isdigit():
                    marker_pos = min(max(match.start(), 0), len(line))
                    marker = " " * marker_pos + "^"
                    errors.append(f"标识符 '{identifier}' 不能以数字开头")
                    errors.append(line)
                    errors.append(marker)
                # 检查是否包含连续下划线
                if "__" in identifier:
                    marker_pos = min(max(match.start(), 0), len(line))
                    marker = " " * marker_pos + "^"
                    errors.append(f"标识符 '{identifier}' 不能包含连续下划线")
                    errors.append(line)
                    errors.append(marker)

            # 额外检查：查找以数字开头的标识符（不在单词边界内）
            digit_start_pattern = re.compile(r"\b\d+[a-zA-Z_][a-zA-Z0-9_]*\b")
            for match in digit_start_pattern.finditer(code_part):
                identifier = match.group()
                marker_pos = min(max(match.start(), 0), len(line))
                marker = " " * marker_pos + "^"
                errors.append(f"标识符 '{identifier}' 不能以数字开头")
                errors.append(line)
                errors.append(marker)

            # 3. 检查数字格式
            # 不能有多个小数点
            number_pattern = re.compile(r"\b\d+\.\d+\.\d+\b")
            for match in number_pattern.finditer(code_part):
                number = match.group()
                marker_pos = min(max(match.start(), 0), len(line))
                marker = " " * marker_pos + "^"
                errors.append(f"数字 '{number}' 格式错误，不能有多个小数点")
                errors.append(line)
                errors.append(marker)

            # 4. 检查字符串格式
            # 检查未闭合的字符串
            quote_count = code_part.count('"') + code_part.count("'")
            if quote_count % 2 != 0:
                # 找到最后一个引号位置
                last_quote_pos = max(code_part.rfind('"'), code_part.rfind("'"))
                if last_quote_pos != -1:
                    marker_pos = min(max(last_quote_pos, 0), len(line))
                    marker = " " * marker_pos + "^"
                    errors.append(f"第{line_idx + 1}行字符串未闭合")
                    errors.append(line)
                    errors.append(marker)

            # 5. 检查操作符使用
            # 检查连续的操作符（除了比较操作符）
            op_pattern = re.compile(r"[+\-*/]{2,}")
            for match in op_pattern.finditer(code_part):
                op = match.group()
                marker_pos = min(max(match.start(), 0), len(line))
                marker = " " * marker_pos + "^"
                errors.append(f"连续操作符 '{op}' 不合法")
                errors.append(line)
                errors.append(marker)

            # 6. 检查赋值语句中的字符用法（优先于括号检查）
            # 检查等号前后的字符是否合法
            equal_pattern = re.compile(r"(\S+)\s*=\s*(\S.*)")
            for match in equal_pattern.finditer(code_part):
                left_part = match.group(1).strip()
                right_part = match.group(2).strip()

                # 检查等号左边是否有非法字符
                if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", left_part):
                    # 找到等号位置
                    equal_pos = code_part.find("=", match.start())
                    if equal_pos != -1:
                        # 找到等号左边第一个非法字符
                        for i in range(match.start(), equal_pos):
                            char = code_part[i]
                            if not re.match(r"[a-zA-Z0-9_\s]", char):
                                marker_pos = min(max(i, 0), len(line))
                                marker = " " * marker_pos + "^"
                                errors.append(
                                    f"第{line_idx + 1}行赋值语句中变量名包含非法字符 '{char}'"
                                )
                                errors.append(line)
                                errors.append(marker)
                                # 找到赋值语句错误后，跳过后续检查
                                return errors

                # 检查等号右边是否以左括号开头（可能是语法错误）
                if right_part.startswith("("):
                    # 检查是否是函数调用格式
                    if not re.match(r"^\([a-zA-Z_][a-zA-Z0-9_]*\s*\(", right_part):
                        # 检查是否是简单的括号表达式，如 (close + volume)
                        # 如果括号内包含操作符，则认为是合法的表达式
                        if re.search(r"[+\-*/]", right_part):
                            # 合法的括号表达式，跳过检查
                            pass
                        else:
                            equal_pos = code_part.find("=", match.start())
                            if equal_pos != -1:
                                # 找到等号右边的左括号位置
                                left_paren_pos = code_part.find("(", equal_pos)
                                if left_paren_pos != -1:
                                    marker_pos = min(max(left_paren_pos, 0), len(line))
                                    marker = " " * marker_pos + "^"
                                    errors.append(
                                        f"第{line_idx + 1}行赋值语句语法错误，等号后不应直接跟左括号"
                                    )
                                    errors.append(line)
                                    errors.append(marker)
                                    # 找到赋值语句错误后，跳过后续检查
                                    return errors

            # 7. 检查括号匹配
            # 使用栈来检查括号匹配
            stack = []
            bracket_positions = []

            for i, char in enumerate(code_part):
                if char == "(":
                    stack.append(("(", i))
                elif char == ")":
                    if stack and stack[-1][0] == "(":
                        stack.pop()
                    else:
                        # 多余的右括号
                        marker_pos = min(max(i, 0), len(line))
                        marker = " " * marker_pos + "^"
                        errors.append(f"第{line_idx + 1}行括号不匹配，多余的右括号")
                        errors.append(line)
                        errors.append(marker)
                        break

            # 检查未闭合的左括号
            if stack:
                # 找到最后一个未匹配的左括号位置
                last_open_pos = stack[-1][1]
                marker_pos = min(max(last_open_pos, 0), len(line))
                marker = " " * marker_pos + "^"
                errors.append(f"第{line_idx + 1}行括号不匹配，缺少右括号")
                errors.append(line)
                errors.append(marker)

        return errors

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
