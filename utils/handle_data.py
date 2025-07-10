import os
import json

from utils.fetch_data import DATA_DIR
from .logger import print_log
from tqdm import tqdm


def handle_data_fields():
    """处理数据字段文件，按文件后缀名分组提取id"""
    data_dir = "data"
    grouped_data = {}

    # 获取所有data_fields开头的JSON文件
    data_files = [
        f
        for f in os.listdir(data_dir)
        if f.startswith("data_fields_") and f.endswith(".json")
    ]

    # print_log(f"找到 {len(data_files)} 个数据字段文件")

    # 使用进度条显示处理进度
    with tqdm(data_files, desc="处理数据字段", unit="个文件") as pbar:
        for file in pbar:
            file_path = os.path.join(data_dir, file)

            # 提取文件后缀名（去掉data_fields_前缀和.json后缀）
            suffix = file.replace("data_fields_", "").replace(".json", "")

            # 更新进度条描述
            pbar.set_description(f"正在处理 {suffix}")

            try:
                # 检查文件是否为空
                if os.path.getsize(file_path) == 0:
                    pbar.write(f"跳过空文件: {file}")
                    continue

                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                    if isinstance(data, dict) and "results" in data:
                        # 提取results中的id字段
                        ids = []
                        for item in data["results"]:
                            if isinstance(item, dict) and "id" in item:
                                ids.append(item["id"])

                        grouped_data[suffix] = ids

                    else:
                        pbar.write(f"! 文件 {file} 格式不符合预期，缺少results字段")

            except json.JSONDecodeError as e:
                pbar.write(f"✗ JSON解析失败: {file} - {e}")
            except Exception as e:
                pbar.write(f"✗ 处理文件失败: {file} - {e}")

    # 保存分组后的数据
    output_file = f"{DATA_DIR}/data_fields.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(grouped_data, f, ensure_ascii=False, indent=2)

    total_ids = sum(len(ids) for ids in grouped_data.values())
