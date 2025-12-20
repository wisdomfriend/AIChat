"""统计服务"""
from datetime import datetime, timedelta
from sqlalchemy import func
from ..database import get_session
from ..models import TokenUsage, ApiKey


class StatsService:
    """统计相关业务逻辑"""
    
    @staticmethod
    def get_user_stats(user_id):
        """获取用户token使用统计"""
        db = get_session()
        try:
            today = datetime.utcnow().date()
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)
            
            today_usage = db.query(func.sum(TokenUsage.total_tokens)).filter(
                TokenUsage.user_id == user_id,
                func.date(TokenUsage.request_time) == today
            ).scalar() or 0
            
            week_usage = db.query(func.sum(TokenUsage.total_tokens)).filter(
                TokenUsage.user_id == user_id,
                TokenUsage.request_time >= week_ago
            ).scalar() or 0
            
            month_usage = db.query(func.sum(TokenUsage.total_tokens)).filter(
                TokenUsage.user_id == user_id,
                TokenUsage.request_time >= month_ago
            ).scalar() or 0
            
            total_usage = db.query(func.sum(TokenUsage.total_tokens)).filter(
                TokenUsage.user_id == user_id
            ).scalar() or 0
            
            return {
                'today': today_usage,
                'week': week_usage,
                'month': month_usage,
                'total': total_usage
            }
        except Exception as e:
            print(f"Get user stats error: {e}")
            return {'today': 0, 'week': 0, 'month': 0, 'total': 0}
        finally:
            db.close()
    
    @staticmethod
    def get_admin_stats():
        """获取管理员统计信息"""
        db = get_session()
        try:
            today = datetime.utcnow().date()
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)
            
            # 今日统计
            today_stats = db.query(
                func.sum(TokenUsage.prompt_tokens).label('prompt'),
                func.sum(TokenUsage.completion_tokens).label('completion'),
                func.sum(TokenUsage.total_tokens).label('total'),
                func.count(TokenUsage.id).label('count')
            ).filter(
                func.date(TokenUsage.request_time) == today
            ).first()
            
            # 本周统计
            week_stats = db.query(
                func.sum(TokenUsage.prompt_tokens).label('prompt'),
                func.sum(TokenUsage.completion_tokens).label('completion'),
                func.sum(TokenUsage.total_tokens).label('total'),
                func.count(TokenUsage.id).label('count')
            ).filter(
                TokenUsage.request_time >= week_ago
            ).first()
            
            # 本月统计
            month_stats = db.query(
                func.sum(TokenUsage.prompt_tokens).label('prompt'),
                func.sum(TokenUsage.completion_tokens).label('completion'),
                func.sum(TokenUsage.total_tokens).label('total'),
                func.count(TokenUsage.id).label('count')
            ).filter(
                TokenUsage.request_time >= month_ago
            ).first()
            
            # 总统计
            total_stats = db.query(
                func.sum(TokenUsage.prompt_tokens).label('prompt'),
                func.sum(TokenUsage.completion_tokens).label('completion'),
                func.sum(TokenUsage.total_tokens).label('total'),
                func.count(TokenUsage.id).label('count')
            ).first()
            
            # 最近10条使用记录
            recent_usage = db.query(TokenUsage).order_by(
                TokenUsage.request_time.desc()
            ).limit(10).all()
            
            # 获取当前API key
            # API Key 管理已移除，不再返回
            
            return {
                'stats': {
                    'today': {
                        'prompt': today_stats.prompt or 0,
                        'completion': today_stats.completion or 0,
                        'total': today_stats.total or 0,
                        'count': today_stats.count or 0
                    },
                    'week': {
                        'prompt': week_stats.prompt or 0,
                        'completion': week_stats.completion or 0,
                        'total': week_stats.total or 0,
                        'count': week_stats.count or 0
                    },
                    'month': {
                        'prompt': month_stats.prompt or 0,
                        'completion': month_stats.completion or 0,
                        'total': month_stats.total or 0,
                        'count': month_stats.count or 0
                    },
                    'total': {
                        'prompt': total_stats.prompt or 0,
                        'completion': total_stats.completion or 0,
                        'total': total_stats.total or 0,
                        'count': total_stats.count or 0
                    }
                },
                'recent_usage': recent_usage
            }
        except Exception as e:
            print(f"Get admin stats error: {e}")
            return {
                'stats': {
                    'today': {'prompt': 0, 'completion': 0, 'total': 0, 'count': 0},
                    'week': {'prompt': 0, 'completion': 0, 'total': 0, 'count': 0},
                    'month': {'prompt': 0, 'completion': 0, 'total': 0, 'count': 0},
                    'total': {'prompt': 0, 'completion': 0, 'total': 0, 'count': 0}
                },
                'recent_usage': []
            }
        finally:
            db.close()

