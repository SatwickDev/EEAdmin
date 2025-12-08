"""
Analytics Routes Module
Contains all routes for analytics dashboards, compliance analytics,
module performance metrics, and data export functionality
"""

from flask import request, jsonify, render_template, Response
from datetime import datetime, timedelta
from typing import Dict, Any
import json
import uuid
import csv
import io


def register_analytics_routes(app, timing_aspect, logger, db):
    """
    Register all analytics routes
    
    Args:
        app: Flask application instance
        timing_aspect: Timing decorator for performance monitoring
        logger: Logger instance
        db: MongoDB database instance
    """

    # ==================== Analytics Page Routes ====================

    @app.route("/analytics", methods=["GET"])
    @timing_aspect
    def analytics():
        """Analytics Category Selector"""
        return render_template("analytics_category_selector.html")

    @app.route("/analytics/trade-finance", methods=["GET"])
    @timing_aspect
    def analytics_trade_finance():
        """Trade Finance Analytics Dashboard"""
        return render_template("analytics_trade_finance.html")

    @app.route("/analytics/cash-management", methods=["GET"])
    @timing_aspect
    def analytics_cash_management():
        """Cash Management Analytics Dashboard"""
        return render_template("analytics_cash_management.html")

    @app.route("/analytics/treasury-management", methods=["GET"])
    @timing_aspect
    def analytics_treasury_management():
        """Treasury Management Analytics Dashboard"""
        return render_template("analytics_treasury_management.html")

    @app.route("/analytics_improved", methods=["GET"])
    @timing_aspect
    def analytics_improved():
        """Improved Analytics Dashboard"""
        return render_template("analytics_improved.html")

    # ==================== Compliance Analytics API Routes ====================

    @app.route('/api/compliance/analytics', methods=['GET'])
    def get_compliance_analytics():
        """Get compliance analytics and statistics"""
        try:
            user_id = request.args.get('user_id')
            date_range = request.args.get('date_range', '30')  # days

            # Mock analytics data - replace with actual database queries
            analytics = {
                'total_checks_performed': 147,
                'average_compliance_score': 87.3,
                'total_documents_processed': 441,
                'compliance_trend': [
                    {'date': (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d'),
                     'score': 85 + (i % 10)} for i in range(int(date_range))
                ],
                'document_type_distribution': {
                    'invoice': 35,
                    'purchase_order': 28,
                    'shipping_document': 22,
                    'sales_contract': 15
                },
                'risk_distribution': {
                    'low': 65,
                    'medium': 25,
                    'high': 10
                },
                'common_issues': [
                    {'issue': 'Amount discrepancy', 'count': 23},
                    {'issue': 'Date mismatch', 'count': 18},
                    {'issue': 'Party information inconsistent', 'count': 15},
                    {'issue': 'Goods description unclear', 'count': 12}
                ]
            }

            return jsonify({
                'success': True,
                'analytics': analytics
            })

        except Exception as e:
            logger.error(f"Error retrieving compliance analytics: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/compliance/dashboard', methods=['GET'])
    def get_compliance_dashboard():
        """Get compliance dashboard data"""
        try:
            # Mock dashboard data - replace with actual database queries
            dashboard_data = {
                'summary_stats': {
                    'total_checks_today': 23,
                    'average_score_today': 89.2,
                    'critical_issues_today': 3,
                    'documents_processed_today': 67
                },
                'recent_checks': [
                    {
                        'id': str(uuid.uuid4()),
                        'timestamp': (datetime.now() - timedelta(minutes=i * 15)).isoformat(),
                        'swift_type': f'MT70{i}',
                        'score': 85 + (i * 3),
                        'status': 'PASS' if (85 + (i * 3)) >= 80 else 'FAIL',
                        'critical_issues': max(0, 3 - i)
                    }
                    for i in range(5)
                ],
                'system_health': {
                    'api_status': 'healthy',
                    'database_status': 'healthy',
                    'processing_queue': 2,
                    'average_response_time': 1.8
                },
                'alerts': [
                    {
                        'type': 'warning',
                        'message': 'High volume of amount discrepancies detected in last hour',
                        'timestamp': (datetime.now() - timedelta(minutes=45)).isoformat()
                    },
                    {
                        'type': 'info',
                        'message': 'System maintenance scheduled for tonight',
                        'timestamp': (datetime.now() - timedelta(hours=2)).isoformat()
                    }
                ]
            }

            return jsonify({
                'success': True,
                'dashboard': dashboard_data
            })

        except Exception as e:
            logger.error(f"Error retrieving compliance dashboard: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # ==================== Analytics Dashboard API Routes ====================

    @app.route('/api/analytics/dashboard', methods=['GET'])
    def get_analytics_dashboard():
        """Get comprehensive analytics data for the dashboard"""
        try:
            # Get date range from request
            date_from = request.args.get('date_from')
            date_to = request.args.get('date_to')

            # Build query
            query = {}
            if date_from and date_to:
                query['timestamp'] = {
                    '$gte': datetime.strptime(date_from, '%Y-%m-%d'),
                    '$lte': datetime.strptime(date_to, '%Y-%m-%d')
                }

            # Aggregate metrics from different collections
            # Transaction metrics
            transaction_metrics = db.chat_messages_collection.aggregate([
                {'$match': query},
                {'$group': {
                    '_id': '$module_type',
                    'count': {'$sum': 1},
                    'total_value': {'$sum': '$transaction_value'}
                }}
            ])

            # Status distribution
            status_metrics = db.chat_messages_collection.aggregate([
                {'$match': query},
                {'$group': {
                    '_id': '$status',
                    'count': {'$sum': 1}
                }}
            ])

            # Time series data
            time_series = db.chat_messages_collection.aggregate([
                {'$match': query},
                {'$group': {
                    '_id': {
                        'year': {'$year': '$timestamp'},
                        'month': {'$month': '$timestamp'},
                        'day': {'$dayOfMonth': '$timestamp'}
                    },
                    'count': {'$sum': 1},
                    'value': {'$sum': '$transaction_value'}
                }},
                {'$sort': {'_id': 1}}
            ])

            # Process results
            modules_data = list(transaction_metrics)
            status_data = list(status_metrics)
            trends_data = list(time_series)

            # Calculate KPIs
            total_transactions = sum(m['count'] for m in modules_data)
            total_value = sum(m.get('total_value', 0) for m in modules_data)
            pending_count = next((s['count'] for s in status_data if s['_id'] == 'Awaiting Corporate Approval'), 0)
            approved_count = next((s['count'] for s in status_data if s['_id'] == 'Authorised'), 0)

            # Mock data for demonstration (replace with real data)
            analytics_data = {
                'kpis': {
                    'total_transactions': total_transactions or 630,
                    'total_value': total_value or 5040000000000,
                    'pending_count': pending_count or 235,
                    'approved_count': approved_count or 208,
                    'success_rate': 96.2,
                    'avg_processing_time': 2.8
                },
                'modules': {
                    'names': ['IMCO', 'IMLC', 'INFI', 'MESG', 'OWGT', 'SHGT'],
                    'transactions': [117, 362, 4, 16, 113, 18],
                    'values': [41465111.23, 5000036735852.06, 0, 0, 7623010, 0],
                    'efficiency': [85, 92, 78, 65, 88, 72]
                },
                'statuses': {
                    'Authorised': 208,
                    'Awaiting Corporate Approval': 235,
                    'Rejected by Supervisor': 4,
                    'Released': 147,
                    'Saved': 36
                },
                'trends': {
                    'months': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
                    'transactions': [450, 520, 480, 630, 580, 620, 630],
                    'values': [2.1, 2.8, 2.5, 5.04, 4.2, 4.8, 5.04]
                }
            }

            return jsonify({
                'success': True,
                'data': analytics_data,
                'generated_at': datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"Error fetching analytics dashboard: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/analytics/module-performance', methods=['GET'])
    def get_module_performance():
        """Get detailed module performance metrics"""
        try:
            module = request.args.get('module')
            period = request.args.get('period', '30d')

            # Calculate date range based on period
            end_date = datetime.now()
            if period == '7d':
                start_date = end_date - timedelta(days=7)
            elif period == '30d':
                start_date = end_date - timedelta(days=30)
            elif period == '90d':
                start_date = end_date - timedelta(days=90)
            else:
                start_date = end_date - timedelta(days=30)

            query = {
                'timestamp': {'$gte': start_date, '$lte': end_date}
            }
            if module:
                query['module_type'] = module

            # Aggregate performance metrics
            performance_data = db.metrics_collection.aggregate([
                {'$match': query},
                {'$group': {
                    '_id': {
                        'module': '$module_type',
                        'date': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$timestamp'}}
                    },
                    'avg_response_time': {'$avg': '$response_time'},
                    'transaction_count': {'$sum': 1},
                    'error_count': {'$sum': {'$cond': [{'$eq': ['$status', 'error']}, 1, 0]}},
                    'success_count': {'$sum': {'$cond': [{'$eq': ['$status', 'success']}, 1, 0]}}
                }},
                {'$sort': {'_id.date': 1}}
            ])

            return jsonify({
                'success': True,
                'data': list(performance_data),
                'period': period,
                'module': module
            })

        except Exception as e:
            logger.error(f"Error fetching module performance: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # ==================== Analytics Export Routes ====================

    @app.route('/api/analytics/export', methods=['POST'])
    def export_analytics_data():
        """Export analytics data in various formats"""
        try:
            export_format = request.json.get('format', 'csv')
            data_type = request.json.get('data_type', 'summary')
            filters = request.json.get('filters', {})

            # Fetch analytics data based on filters
            analytics_data = {
                'summary': {
                    'total_transactions': 630,
                    'total_value': 5040000000000,
                    'modules': ['IMCO', 'IMLC', 'INFI', 'MESG', 'OWGT', 'SHGT'],
                    'period': f"{filters.get('date_from', 'Start')} to {filters.get('date_to', 'End')}"
                },
                'details': []
            }

            # Generate export based on format
            if export_format == 'csv':
                csv_data = generate_analytics_csv(analytics_data)
                return Response(
                    csv_data,
                    mimetype='text/csv',
                    headers={
                        'Content-Disposition': f'attachment; filename=analytics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
                )
            elif export_format == 'excel':
                excel_data = generate_analytics_excel(analytics_data)
                return Response(
                    excel_data,
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={
                        'Content-Disposition': f'attachment; filename=analytics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'}
                )
            elif export_format == 'pdf':
                pdf_data = generate_analytics_pdf(analytics_data)
                return Response(
                    pdf_data,
                    mimetype='application/pdf',
                    headers={
                        'Content-Disposition': f'attachment; filename=analytics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'}
                )
            else:
                return jsonify({
                    'success': False,
                    'error': 'Unsupported export format'
                }), 400

        except Exception as e:
            logger.error(f"Error exporting analytics data: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    logger.info("Analytics routes registered successfully")


# ==================== Utility Functions ====================

def generate_analytics_csv(data: Dict[str, Any]) -> str:
    """Generate CSV for analytics data"""
    output = io.StringIO()
    writer = csv.writer(output)

    # Write summary
    writer.writerow(['Analytics Summary'])
    writer.writerow(['Metric', 'Value'])
    writer.writerow(['Total Transactions', data['summary']['total_transactions']])
    writer.writerow(['Total Value (AED)', data['summary']['total_value']])
    writer.writerow(['Period', data['summary']['period']])
    writer.writerow([''])

    # Write module breakdown
    writer.writerow(['Module Breakdown'])
    writer.writerow(['Module', 'Transactions', 'Value (AED)'])
    # Add module data here

    return output.getvalue()


def generate_analytics_excel(data: Dict[str, Any]) -> bytes:
    """Generate Excel for analytics data"""
    # Placeholder - implement with openpyxl
    return b"Excel content placeholder"


def generate_analytics_pdf(data: Dict[str, Any]) -> bytes:
    """Generate PDF for analytics data"""
    # Placeholder - implement with reportlab
    return b"PDF content placeholder"
