#!/usr/bin/env python3
"""
WQB Expression Validator Web API 示例
"""

from flask import Flask, request, jsonify
from wqb_validator import ExpressionValidator, DataManager
import json

app = Flask(__name__)

# 初始化验证器和数据管理器
validator = ExpressionValidator()
data_manager = DataManager()

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({
        'status': 'healthy',
        'service': 'WQB Expression Validator',
        'version': '1.0.0'
    })

@app.route('/validate', methods=['POST'])
def validate_expression():
    """验证alpha表达式的API端点"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': '请求体不能为空'}), 400
        
        expression = data.get('expression')
        region = data.get('region', 'USA')
        delay = data.get('delay', 1)
        universe = data.get('universe', 'TOP3000')
        
        if not expression:
            return jsonify({'error': '表达式不能为空'}), 400
        
        # 验证表达式
        result = validator.validate(expression, region=region, delay=delay, universe=universe)
        
        response = {
            'expression': expression,
            'config': {
                'region': region,
                'delay': delay,
                'universe': universe
            },
            'is_valid': result.is_valid,
            'errors': []
        }
        
        if not result.is_valid:
            response['errors'] = [
                {
                    'type': error.error_type,
                    'message': error.message,
                    'position': error.position,
                    'suggestion': getattr(error, 'suggestion', None)
                }
                for error in result.errors
            ]
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/validate/batch', methods=['POST'])
def validate_batch():
    """批量验证表达式的API端点"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': '请求体不能为空'}), 400
        
        expressions = data.get('expressions', [])
        region = data.get('region', 'USA')
        delay = data.get('delay', 1)
        universe = data.get('universe', 'TOP3000')
        
        if not expressions:
            return jsonify({'error': '表达式列表不能为空'}), 400
        
        if not isinstance(expressions, list):
            return jsonify({'error': 'expressions必须是列表'}), 400
        
        results = []
        valid_count = 0
        invalid_count = 0
        
        for expr in expressions:
            try:
                result = validator.validate(expr, region=region, delay=delay, universe=universe)
                
                expr_result = {
                    'expression': expr,
                    'is_valid': result.is_valid,
                    'errors': []
                }
                
                if not result.is_valid:
                    expr_result['errors'] = [
                        {
                            'type': error.error_type,
                            'message': error.message,
                            'position': error.position,
                            'suggestion': getattr(error, 'suggestion', None)
                        }
                        for error in result.errors
                    ]
                    invalid_count += 1
                else:
                    valid_count += 1
                
                results.append(expr_result)
                
            except Exception as e:
                expr_result = {
                    'expression': expr,
                    'is_valid': False,
                    'errors': [{
                        'type': 'EXCEPTION',
                        'message': str(e),
                        'position': None,
                        'suggestion': None
                    }]
                }
                results.append(expr_result)
                invalid_count += 1
        
        response = {
            'config': {
                'region': region,
                'delay': delay,
                'universe': universe
            },
            'summary': {
                'total': len(expressions),
                'valid': valid_count,
                'invalid': invalid_count,
                'success_rate': valid_count / len(expressions) * 100
            },
            'results': results
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/data/status', methods=['GET'])
def get_data_status():
    """获取数据状态"""
    try:
        # 这里可以返回数据状态信息
        # 由于data_manager.show_status()是打印到控制台，我们需要获取状态信息
        return jsonify({
            'message': '数据状态信息已显示在控制台',
            'endpoint': '/data/status',
            'note': '使用 wqb-data status 命令查看详细状态'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/data/update', methods=['POST'])
def update_data():
    """更新数据"""
    try:
        # 这里可以触发数据更新
        # 由于data_manager.update_data()是同步操作，在生产环境中应该异步处理
        return jsonify({
            'message': '数据更新请求已接收',
            'note': '使用 wqb-data update 命令手动更新数据',
            'endpoint': '/data/update'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '端点不存在'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': '内部服务器错误'}), 500

if __name__ == '__main__':
    print("🚀 启动WQB Expression Validator Web API...")
    print("📖 可用端点:")
    print("  GET  /health          - 健康检查")
    print("  POST /validate        - 验证单个表达式")
    print("  POST /validate/batch  - 批量验证表达式")
    print("  GET  /data/status     - 获取数据状态")
    print("  POST /data/update     - 更新数据")
    print("\n🌐 服务将在 http://localhost:5000 启动")
    print("💡 使用 Ctrl+C 停止服务")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
