#!/usr/bin/env python3
"""
WQB Expression Validator 基本使用示例
"""

from wqb_validator import ExpressionValidator

def basic_validation_example():
    """基本验证示例"""
    print("🔍 WQB表达式验证器 - 基本使用示例\n")
    
    # 创建验证器实例（需要指定地区、延迟和股票池）
    validator = ExpressionValidator(region="USA", delay=1, universe="TOP3000")
    
    # 要验证的表达式列表
    expressions = [
        "ts_mean(close, 20)",
        "ts_std(volume, 10)",
        "ts_rank(returns, 5)",
        "ts_corr(close, volume, 30)",
        "ts_cov(returns, volume, 15)"
    ]
    
    print("📝 验证以下表达式:")
    for i, expr in enumerate(expressions, 1):
        print(f"  {i}. {expr}")
    
    print("\n" + "="*50 + "\n")
    
    # 验证每个表达式
    for i, expr in enumerate(expressions, 1):
        print(f"🔍 验证表达式 {i}: {expr}")
        
        try:
            result = validator.validate(expr)
            
            if result.is_valid:
                print("  ✅ 有效")
            else:
                print("  ❌ 无效:")
                for error in result.errors:
                    print(f"    - {error.message}")
            
        except Exception as e:
            print(f"  ❌ 验证过程中发生错误: {e}")
        
        print()  # 空行分隔
    
    print("🎉 基本验证示例完成！")

if __name__ == "__main__":
    basic_validation_example()
