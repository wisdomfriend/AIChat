"""Agent 工具类 - 提供时间和计算工具"""
from datetime import datetime
import pytz
import re


def calculate(expression: str) -> str:
    """
    计算数学表达式
    
    支持基本的数学运算：加减乘除、幂运算、括号等
    安全限制：只允许数字、运算符和括号，不允许执行任意代码
    
    Args:
        expression: 数学表达式字符串，例如 "3 + 5 * 2" 或 "(10 + 5) / 3"
        
    Returns:
        计算结果字符串
    """
    try:
        # 移除空格
        expression = expression.strip().replace(' ', '')
        
        # 安全检查：只允许数字、运算符、括号和小数点
        if not re.match(r'^[0-9+\-*/().\s]+$', expression):
            return f"错误：表达式包含非法字符。只支持数字、+、-、*、/、() 和 ."
        
        # 检查括号是否匹配
        if expression.count('(') != expression.count(')'):
            return "错误：括号不匹配"
        
        # 使用 eval 计算
        result = eval(expression)
        
        # 处理结果
        if isinstance(result, float):
            # 如果是整数，返回整数格式
            if result.is_integer():
                return str(int(result))
            # 保留合理的小数位数
            return f"{result:.10f}".rstrip('0').rstrip('.')
        else:
            return str(result)
            
    except ZeroDivisionError:
        return "错误：除数不能为零"
    except Exception as e:
        return f"计算错误: {str(e)}"


def get_time_info() -> str:
    """
    获取详细的时间信息
    
    不需要任何参数。
    
    Returns:
        包含当前时间、日期、星期等信息的字符串
    """
    try:
        tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(tz)
        
        # 星期几
        weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        weekday = weekdays[now.weekday()]
        
        # 格式化信息
        date_str = now.strftime("%Y年%m月%d日")
        time_str = now.strftime("%H:%M:%S")
        
        return f"当前时间：{date_str} {time_str} {weekday} "
    except Exception as e:
        return f"获取时间信息失败: {str(e)}"

