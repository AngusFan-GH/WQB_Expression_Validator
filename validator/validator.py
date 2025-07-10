import json
import pandas as pd
from lark import Lark, Transformer, exceptions
import re

from utils.fetch_data import DATA_DIR

# ====== 1. 加载 grammar 文件 ======
with open("validator/grammar.lark", "r") as f:
    grammar = f.read()

parser = Lark(grammar, start="start", parser="lalr")

# ====== 2. 加载权限数据 ======
with open("validator/valid_ops.json", "r") as f:
    valid_ops = json.load(f)

operators_df = pd.read_csv(f"{DATA_DIR}/operators.csv")
valid_operator_names = set(operators_df["name"].dropna().unique())

with open(f"{DATA_DIR}/data_fields.json", "r") as f:
    data_fields_dict = json.load(f)


# ====== 参数类型推断辅助 ======
def parse_param_type(param):
    param = param.strip()
    # 形如 x, y, z, input, group, field, alpha 等，视为 field/number
    if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", param):
        return "field_or_number"
    # 形如 "abc" 或 'abc'，视为 string
    if re.match(r'^".*"$|^\  .*$', param):
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
    mapping = {}
    for _, row in operators_df.iterrows():
        name = row["name"]
        definition = str(row["definition"])
        pos_types, kw_types = parse_operator_param_types(definition)
        mapping[name] = {"pos": pos_types, "kw": kw_types}
    return mapping


OP_PARAM_TYPES = operator_param_types_map()


# ====== 3. 验证器类（用于 AST 遍历） ======
# ====== 3. 验证器类（用于 AST 遍历） ======
class ExprValidator(Transformer):
    def __init__(self, valid_field_names):
        super().__init__()
        self.errors = []
        self.valid_field_names = valid_field_names

    def function(self, args):
        name = str(args[0])

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
            self.errors.append(f"未知操作符: {name}")
        else:
            op = valid_ops[name]
            min_args = op["min_args"]
            max_args = op["max_args"]
            if num_args < min_args:
                self.errors.append(
                    f"{name} 参数不足: 至少需要 {min_args} 个，实际为 {num_args}"
                )
            if max_args is not None and num_args > max_args:
                self.errors.append(
                    f"{name} 参数过多: 最多允许 {max_args} 个，实际为 {num_args}"
                )

            pos_types = op.get("arg_types", [])
            kw_types = op.get("kwarg_types", {})

            for i, node in enumerate(arg_nodes):
                if hasattr(node, "data") and node.data == "kwarg":
                    key = str(node.children[0])
                    value_node = node.children[1]
                    expect_type = kw_types.get(key)
                    actual_type = self._get_node_type(value_node)
                    if expect_type:
                        if expect_type in (
                            "field",
                            "field_or_number",
                        ) and actual_type in ("field_or_number", "field", "number"):
                            continue
                        if actual_type != expect_type:
                            self.errors.append(
                                f"{name} 的参数 `{key}` 类型应为 {expect_type}，实际为 {actual_type}"
                            )
                else:
                    if i < len(pos_types):
                        expect_type = pos_types[i]
                        actual_type = self._get_node_type(node)
                        if expect_type in (
                            "field",
                            "field_or_number",
                        ) and actual_type in ("field_or_number", "field", "number"):
                            continue
                        if expect_type and actual_type != expect_type:
                            self.errors.append(
                                f"{name} 的第{i+1}个参数类型应为 {expect_type}，实际为 {actual_type}"
                            )

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
                            if (
                                hasattr(value_node, "data")
                                and value_node.data == "string"
                            ):
                                value = str(value_node.children[0]).strip('"')
                            else:
                                value = str(value_node).strip('"')
                            if key in choices and value not in choices[key]:
                                self.errors.append(
                                    f"{name} 的参数 `{key}` 不合法：{value}，应为 {choices[key]}"
                                )
        return name

    def field(self, token):
        field_name = str(token[0])
        if field_name not in self.valid_field_names:
            self.errors.append(f"未知字段: {field_name}")
        return field_name

    def _get_node_type(self, node):
        from lark.lexer import Token

        if isinstance(node, Token):
            if node.type == "SIGNED_NUMBER":
                return "number"
            if node.type == "ESCAPED_STRING":
                return "string"
            if node.type == "CNAME":
                val = str(node)
                if val in ["true", "false", "True", "False"]:
                    return "boolean"
                # 判断是否为字段
                if hasattr(self, "valid_field_names") and val in self.valid_field_names:
                    return "field"
                return "field_or_number"
        if hasattr(node, "data"):
            if node.data == "number":
                return "number"
            if node.data == "string":
                return "string"
            if node.data == "field":
                # field 规则下只有一个子节点，直接递归
                child_type = self._get_node_type(node.children[0])
                # 如果子节点是字段，优先返回 field
                if child_type == "field":
                    return "field"
                return child_type
            # 处理嵌套的表达式节点
            if node.data in [
                "expr",
                "logic_or",
                "logic_and",
                "logic_not",
                "comparison",
                "add_expr",
                "mul_expr",
                "unary_expr",
                "atom",
            ]:
                if node.children:
                    return self._get_node_type(node.children[0])
        return "unknown"


# ====== 4. 公共导出函数 ======
def validate_expression(expr: str, region: str, delay: int, universe: str):
    """
    验证表达式是否合法

    :param expr: 表达式字符串
    :param region: 地区 (如 USA, CHN, EUR)
    :param delay: 延迟天数 (如 0, 1)
    :param universe: 股票池 (如 TOP500, TOP1000, TOP3000)
    :return: (是否通过验证: bool, 错误列表: List[str])
    """
    try:
        # 构建组合键
        combination_key = f"{region}_{delay}_{universe}"

        print(f"combination_key: {combination_key}")

        # 获取对应的数据字段
        if combination_key not in data_fields_dict:
            return False, [f"无效的组合参数: {combination_key}"]

        valid_field_names = set(data_fields_dict[combination_key])

        tree = parser.parse(expr)
        validator = ExprValidator(valid_field_names)
        validator.transform(tree)
        if validator.errors:
            return False, validator.errors
        return True, []
    except exceptions.LarkError as e:
        return False, [f"语法错误: {str(e)}"]
