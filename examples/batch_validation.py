#!/usr/bin/env python3
"""
WQB Expression Validator 批量验证示例
"""

from wqb_validator import ExpressionValidator
from pathlib import Path
import json

def batch_validation_example():
    """批量验证示例"""
    print("🔍 WQB表达式验证器 - 批量验证示例\n")
    
    # 创建验证器实例
    validator = ExpressionValidator()
    
    # 模拟从文件读取的表达式
    expressions = [
        "ts_mean(close, 20)",
        "ts_std(volume, 10)",
        "ts_rank(returns, 5)",
        "ts_corr(close, volume, 30)",
        "ts_cov(returns, volume, 15)",
        "ts_sum(volume, 5)",
        "ts_min(close, 10)",
        "ts_max(high, 15)"
    ]
    
    print(f"📝 批量验证 {len(expressions)} 个表达式\n")
    
    # 验证结果统计
    results = {
        'total': len(expressions),
        'valid': 0,
        'invalid': 0,
        'errors': []
    }
    
    # 验证每个表达式
    for i, expr in enumerate(expressions, 1):
        print(f"🔍 [{i:2d}/{len(expressions)}] 验证: {expr}")
        
        try:
            result = validator.validate(expr)
            
            if result.is_valid:
                print("  ✅ 有效")
                results['valid'] += 1
            else:
                print("  ❌ 无效:")
                error_count = len(result.errors)
                results['invalid'] += 1
                
                for j, error in enumerate(result.errors, 1):
                    print(f"    {j}. {error.message}")
                    results['errors'].append({
                        'expression': expr,
                        'error_type': error.error_type,
                        'message': error.message,
                        'position': error.position
                    })
            
        except Exception as e:
            print(f"  ❌ 验证过程中发生错误: {e}")
            results['invalid'] += 1
            results['errors'].append({
                'expression': expr,
                'error_type': 'EXCEPTION',
                'message': str(e),
                'position': None
            })
        
        print()  # 空行分隔
    
    # 显示统计结果
    print("="*50)
    print("📊 批量验证结果统计:")
    print(f"  📈 总表达式数: {results['total']}")
    print(f"  ✅ 有效表达式: {results['valid']}")
    print(f"  ❌ 无效表达式: {results['invalid']}")
    print(f"  📊 成功率: {results['valid']/results['total']*100:.1f}%")
    
    if results['errors']:
        print(f"\n❌ 错误详情 ({len(results['errors'])} 个):")
        for i, error in enumerate(results['errors'], 1):
            print(f"  {i}. {error['expression']}")
            print(f"     类型: {error['error_type']}")
            print(f"     消息: {error['message']}")
            if error['position']:
                print(f"     位置: {error['position']}")
            print()
    
    print("🎉 批量验证示例完成！")
    
    return results

def save_results_to_file(results, filename="validation_results.json"):
    """保存验证结果到文件"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"💾 验证结果已保存到: {filename}")
    except Exception as e:
        print(f"❌ 保存结果失败: {e}")

if __name__ == "__main__":
    # 运行批量验证
    results = batch_validation_example()
    
    # 保存结果到文件
    save_results_to_file(results)
