# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################

from odoo import models, fields, api
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import pytz
import calendar
from calendar import month


def start_end_date_global(start, end, tz):
    tz = pytz.timezone(tz) or 'UTC'
    current_time = datetime.now(tz)
    hour_tz = int(str(current_time)[-5:][:2])
    min_tz = int(str(current_time)[-5:][3:])
    sign = str(current_time)[-6][:1]
    sdate = start + " 00:00:00"
    edate = end + " 23:59:59"
    if sign == '-':
        start_date = (datetime.strptime(sdate, '%Y-%m-%d %H:%M:%S') + timedelta(hours=hour_tz,
                                                                                minutes=min_tz)).strftime(
            "%Y-%m-%d %H:%M:%S")
        end_date = (datetime.strptime(edate, '%Y-%m-%d %H:%M:%S') + timedelta(hours=hour_tz,
                                                                              minutes=min_tz)).strftime(
            "%Y-%m-%d %H:%M:%S")
    if sign == '+':
        start_date = (datetime.strptime(sdate, '%Y-%m-%d %H:%M:%S') - timedelta(hours=hour_tz,
                                                                                minutes=min_tz)).strftime(
            "%Y-%m-%d %H:%M:%S")
        end_date = (datetime.strptime(edate, '%Y-%m-%d %H:%M:%S') - timedelta(hours=hour_tz,
                                                                              minutes=min_tz)).strftime(
            "%Y-%m-%d %H:%M:%S")
    return start_date, end_date


class posSessions(models.Model):
    _inherit = "pos.session"

    @api.multi
    def convert_number(self, number):
        if number:
            if number < 1000:
                return number
            if number >= 1000 and number < 1000000:
                total = number / 1000
                return str("%.2f" % total) + 'K'
            if number >= 1000000:
                total = number / 1000000
                return str("%.2f" % total) + 'M'
        else:
            return 0

    @api.model
    def getCompany(self):
        return {'company': [{'id': alw_cmp.id, 'company': alw_cmp.name} for alw_cmp in self.env.user.company_ids],
                'company_id': self.env.user.company_id.id}

    @api.model
    def getActiveSession(self, start_date, end_date, company_id):
        if company_id:
            pass
        else:
            company_id = self.env.user.company_id.id
        current_time_zone = self.env.user.tz or 'UTC'
        s_date, e_date = start_end_date_global(start_date, end_date, current_time_zone)
        today_sales_sql = """SELECT 
                                SUM(po.amount_total) AS today_sales,
                                SUM (pol.qty) AS today_product
                                FROM pos_order as po
                                INNER JOIN pos_order_line AS pol ON po.id = pol.order_id
                                WHERE po.date_order >= '%s' 
                                AND po.date_order <= '%s' 
                                AND po.company_id = %s
                            """ % (s_date, e_date, company_id)
        self._cr.execute(today_sales_sql)
        today_sales_data = self._cr.dictfetchall()

        today_order_sql = """SELECT COUNT(id) AS today_order
                                FROM pos_order
                                WHERE date_order >= '%s' 
                                AND date_order <= '%s' 
                                AND company_id = %s
                            """ % (s_date, e_date, company_id)
        self._cr.execute(today_order_sql)
        today_order_data = self._cr.dictfetchall()

        SQL = """SELECT COUNT(*) AS session
                    FROM pos_session AS ps
                    LEFT JOIN pos_config AS pc ON pc.id = ps.config_id
                    WHERE ps.state = 'opened' AND pc.company_id = %s
                """ % (company_id)
        self._cr.execute(SQL)
        active_session = self._cr.dictfetchall()
        sale_data = self.get_total_sale_data_tiles(company_id)
        product_sold = self.convert_number(sale_data.get('product_count') if sale_data else 0)
        order_count = self.convert_number(sale_data.get('order_count') if sale_data else 0)
        total_amount = self.convert_number(sale_data.get('total_amount') if sale_data else 0)
        today_sales = self.convert_number(today_sales_data[0].get('today_sales') or 0)
        today_order = self.convert_number(today_order_data[0].get('today_order' or 0))
        today_product = self.convert_number(today_sales_data[0].get('today_product') or 0)

        return {'session': active_session[0]['session'] or 0,
                'order': order_count or 0,
                'total_sale': total_amount or 0,
                'product_sold': product_sold or 0,
                'currency': self.env.user.currency_id.symbol,
                'today_sales': today_sales or 0,
                'today_order': today_order or 0,
                'today_product': today_product or 0,
                'login_user': self.env.user.name,
                'login_user_img': self.env.user.image
                }

    @api.model
    def get_total_sale_data_tiles(self, company_id):
        if company_id:
            pass
        else:
            company_id = self.env.user.company_id.id
        query = """SELECT COUNT(order_detail.ord) AS order_count,
                    SUM(order_detail.prod) AS product_count,
                    SUM(order_detail.amount) AS total_amount
                    FROM 
                    (SELECT SUM(posl.qty) AS prod,
                        SUM(posl.price_subtotal_incl) AS amount,
                        posl.order_id AS ord
                        FROM pos_order_line AS posl
                        WHERE posl.company_id = %s
                        GROUP BY ord) AS order_detail;
                """ % company_id
        self._cr.execute(query)
        total_sale_data_query = self._cr.dictfetchall()
        return total_sale_data_query[0] if total_sale_data_query else 0

    @api.model
    def payment_by_journal_pie_chart(self, company_id):
        domain = []
        if company_id:
            domain += [('company_id', '=', int(company_id))]
        else:
            domain += [('company_id', '=', self.env.user.company_id.id)]

        pos_ids = self.env['pos.order'].search(domain).ids

        SQL = ""
        if len(pos_ids) > 1:
            SQL = "absl.pos_statement_id IN  %s" % str(tuple(pos_ids))
        else:
            if len(pos_ids) > 0:
                SQL = "absl.pos_statement_id =  %s" % pos_ids[0]
        if len(pos_ids) > 0:
            sql_query = """SELECT SUM(amount) AS amount, aj.name AS journal
                            FROM account_bank_statement_line AS absl
                            INNER JOIN account_bank_statement AS abs ON abs.id = absl.statement_id
                            INNER JOIN account_journal AS aj ON aj.id = abs.journal_id
                            WHERE %s
                            GROUP BY journal
                            """ % str(SQL)
            self._cr.execute(sql_query)
            journal_data = self._cr.dictfetchall()
            return journal_data

    @api.model
    def get_journal_line_chart_data(self, start_date, end_date, journal, company_id):
        current_time_zone = self.env.user.tz or 'UTC'
        s_date, e_date = start_end_date_global(start_date, end_date, current_time_zone)
        if company_id:
            pass
        else:
            company_id = self.env.user.company_id.id

        flag = False
        sql = ""
        if journal:
            sql = "AND aj.id = " + str(journal)
            flag_val = False
        else:
            sql = ""
            flag_val = True

        sql_query = """SELECT
                         SUM(amount) AS amount, extract(day from po.date_order AT TIME ZONE 'UTC' AT TIME ZONE '%s') AS time_duration,
                         aj.name AS journal, aj.id
                         FROM account_bank_statement_line AS absl
                         INNER JOIN account_bank_statement AS abs ON abs.id = absl.statement_id
                         INNER JOIN account_journal AS aj ON aj.id = abs.journal_id
                         INNER JOIN pos_order AS po ON po.id = absl.pos_statement_id
                         WHERE po.date_order >= '%s'
                         AND po.date_order <= '%s' %s
                         AND po.company_id = %s
                         GROUP BY time_duration, journal, aj.id ORDER BY extract(day from po.date_order AT TIME ZONE 'UTC' AT TIME ZONE '%s') ASC
                     """ % (current_time_zone, s_date, e_date, sql, company_id, current_time_zone)
        self._cr.execute(sql_query)
        month_data = self._cr.dictfetchall()

        option_list = [{'journal': i.get('journal'), 'id': i.get('id')} for i in month_data]
        option_final_list = [dict(tupleized) for tupleized in set(tuple(item.items()) for item in option_list)]

        final_list = []
        for i in month_data:
            if not final_list:
                s = i.get('journal')
                final_list.append({'Date': i.get('time_duration'),
                                   i.get('journal').replace(" ", "_"): i.get('amount')})
            else:
                flag = False
                for f_list in final_list:
                    if f_list.get('Date') == i.get('time_duration'):
                        f_list.update({i.get('journal').replace(" ", "_"): i.get('amount')})
                        flag = True
                if not flag:
                    final_list.append({'Date': i.get('time_duration'),
                                       i.get('journal').replace(" ", "_"): i.get('amount')})

        payment_name_list = []
        for l in final_list:
            payment_name_list += l.keys()
        payment_name_dict = dict([(i, 0) for i in set(payment_name_list)])
        for l in final_list:
            for p in payment_name_dict:
                if p not in l.keys():
                    l.update({p: 0.0})
        day_date_lst = [l.get('Date') for l in final_list]
        current_month_day_lst = [float(i) for i in range(1, int(datetime.today().day) + 1)]
        for j in list(set(current_month_day_lst) - set(day_date_lst)):
            payment_name_dict = dict([(i, 0) for i in set(payment_name_list)])
            payment_name_dict.update({'Date': j})
            final_list.append(payment_name_dict)
        return {'data': sorted(final_list, key=lambda i: i['Date']), 'journal': option_final_list, 'flag': flag_val}


class posOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def employee_work_hour(self, start, end, company_id):
        current_time_zone = self.env.user.tz or 'UTC'
        s_date, e_date = start_end_date_global(start, end, current_time_zone)
        if company_id:
            pass
        else:
            company_id = self.env.user.company_id.id
        query = """SELECT p.id AS eid, SUM(ha.worked_hours) AS total_time
                    FROM hr_attendance AS ha
                    INNER JOIN hr_employee AS p ON ha.employee_id = p.id
                    WHERE
                    ha.check_out > '%s'
                    AND ha.check_out <= '%s'
                    AND p.company_id = % s
                    GROUP BY eid;
                """ % (s_date, e_date, company_id)
        self._cr.execute(query)
        result = self._cr.dictfetchall()
        for each in result:
            each['total_time'] = int(each['total_time'])
            each['ename'] = self.env['hr.employee'].browse([int(each['eid'])]).name
            each['eimage'] = self.env['hr.employee'].browse([int(each['eid'])]).image
        return result

    @api.model
    def sales_data_per_week(self, start, end, company_id):
        if company_id:
            pass
        else:
            company_id = self.env.user.company_id.id
        current_time_zone = self.env.user.tz or 'UTC'
        s_date, e_date = start_end_date_global(start, end, current_time_zone)
        sday = datetime.strptime(s_date, '%Y-%m-%d %H:%M:%S').day
        eday = datetime.strptime(e_date, '%Y-%m-%d %H:%M:%S').day
        query = """
                SELECT
                extract(day from o.date_order AT TIME ZONE 'UTC' AT TIME ZONE '%s') AS dn,
                to_char(o.date_order AT TIME ZONE 'UTC' AT TIME ZONE '%s','DY') AS day,
                COUNT(o.id) AS total_order,
                SUM(pos.price_subtotal_incl) AS sale_total
                FROM pos_order_line AS pos
                INNER JOIN pos_order AS o ON pos.order_id=o.id
                INNER JOIN product_template AS prod ON pos.product_id=prod.id
                AND o.date_order > '%s'
                AND o.date_order <= '%s'
                AND o.company_id = %s
                GROUP BY dn,day;
            """ % (current_time_zone, current_time_zone, s_date, e_date, company_id)
        self._cr.execute(query)
        result = self._cr.dictfetchall()
        days = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
        final_data_list = []
        for d in days:
            order = 0.0
            amount = 0.0
            for each in result:
                if d == each.get('day'):
                    order = each.get('total_order')
                    amount = each.get('sale_total')
            final_data_list.append({'day': d, 'sale_total': amount or 0.0, 'count': order or 0.0})
        return final_data_list

    @api.model
    def staff_sale_info(self, s_date, e_date, company_id, limit):
        sql = ''
        if limit:
            sql = 'LIMIT 1'
        query = """SELECT ord.person_id As person_id ,count(ord.order_name) AS num_order, sum(ord.amount) AS amount FROM
                   (SELECT pos.user_id AS person_id, posl.order_id As order_name, 
                   SUM(posl.price_subtotal_incl) AS amount
                   FROM pos_order_line AS posl
                   LEFT JOIN pos_order AS pos ON pos.id = posl.order_id
                   WHERE pos.company_id = %s
                   AND pos.date_order >= '%s'
                   AND pos.date_order <= '%s'
                   GROUP BY order_name, person_id) AS ord
                   GROUP BY person_id
                   ORDER BY amount DESC %s 
           """ % (company_id, s_date, e_date, sql)
        self._cr.execute(query)
        return self._cr.dictfetchall()

    @api.model
    def sales_data_per_salesperson(self, start, end, company_id):
        current_time_zone = self.env.user.tz or 'UTC'
        s_date, e_date = start_end_date_global(start, end, current_time_zone)
        t_start_date, t_end_date = start_end_date_global(str(date.today()), str(date.today()), current_time_zone)
        if company_id:
            pass
        else:
            company_id = self.env.user.company_id.id
        top_sale_person_weekly = self.staff_sale_info(s_date, e_date, company_id, '')
        top_sale_person_today = self.staff_sale_info(t_start_date, t_end_date, company_id, 1)
        query = """SELECT ord.person_id As person_id ,count(ord.order_name) AS num_order, sum(ord.amount) AS amount FROM
                    (SELECT pos.user_id AS person_id, posl.order_id As order_name, 
                    SUM(posl.price_subtotal_incl) as amount
                    FROM pos_order_line AS posl
                    LEFT JOIN pos_order AS pos ON pos.id = posl.order_id
                    WHERE pos.company_id = %s
                    AND pos.date_order >= '%s'
                    AND pos.date_order <= '%s'
                    GROUP BY order_name, person_id) AS ord
                    GROUP BY person_id
                    ORDER BY amount DESC
            """ % (company_id, s_date, e_date)
        self._cr.execute(query)
        sale_per_salesperson = self._cr.dictfetchall()
        top_staff = {'top_staff': 'No data found', 'amount': 0.0}
        if top_sale_person_today:
            top_staff.update({'amount': top_sale_person_today[0].get('amount') or 0.0,
                              'top_staff': self.env['res.users'].browse(
                                  top_sale_person_today[0].get('person_id')).display_name})

        if len(sale_per_salesperson) > 0:
            for each in sale_per_salesperson:
                user_id = self.env['res.users'].browse([each['person_id']])
                each['person_name'] = user_id.display_name
                each['person_image'] = user_id.image
            return {'salesperson_data': sale_per_salesperson, 'top_staff': top_staff,
                    'currency': self.env.user.currency_id.symbol}

    @api.model
    def products_category(self, start, end, order, option, company_id):
        if company_id:
            pass
        else:
            company_id = self.env.user.company_id.id
        current_time_zone = self.env.user.tz or 'UTC'
        s_date, e_date = start_end_date_global(start, end, current_time_zone)
        query = """pcat.name AS category FROM pos_order_line AS pol
                    INNER JOIN pos_order AS po ON po.id = pol.order_id
                    INNER JOIN product_product AS pt ON pt.id = pol.product_id
                    INNER JOIN product_template AS ptt ON ptt.id = pt.product_tmpl_id
                    INNER JOIN pos_category AS pcat ON pcat.id= ptt.pos_categ_id
                    WHERE po.date_order > '%s' AND po.date_order <= '%s' AND po.company_id = %s
                    GROUP BY category
                """ % (s_date, e_date, company_id)
        if option == "Price":
            price = "SELECT ROUND(SUM(pol.price_subtotal_incl), 2) as value, "
            query = price + query
            if order == "Top":
                query += "ORDER BY value DESC LIMIT 5"
            else:
                query += "ORDER BY value ASC  LIMIT 5"
        else:
            quantity = "SELECT SUM(pol.qty) as value,"
            query = quantity + query
            if order == "Top":
                query += "ORDER BY value DESC LIMIT 5;"
            elif order == "Bottom":
                query += "ORDER BY value ASC LIMIT 5;"
        self._cr.execute(query)
        product_categories = self._cr.dictfetchall()

        final_list = []
        if product_categories:
            total = sum(item['value'] for item in product_categories)
            for each in product_categories:
                final_list.append({
                    'percentage': format((each.get('value') / total) * 100, '.2f'),
                    'category': each.get('category'),
                    'amount': "%.2f" % each.get('value')
                })
        return {'data_source': product_categories, 'categ_data': final_list}

    @api.model
    def top_items_by_sales(self, start, end, company_id):
        if company_id:
            pass
        else:
            company_id = self.env.user.company_id.id
        current_time_zone = self.env.user.tz or 'UTC'
        s_date, e_date = start_end_date_global(start, end, current_time_zone)
        sql_query = """SELECT 
                        SUM(pol.price_subtotal_incl) AS amount, 
                        pt.name AS product_name, pp.default_code AS code,
                        SUM(pol.qty) AS total_qty , pp.id AS product_id
                        FROM pos_order_line AS pol
                        INNER JOIN pos_order AS po ON po.id = pol.order_id
                        INNER JOIN product_product AS pp ON pol.product_id=pp.id
                        INNER JOIN product_template AS pt ON pt.id=pp.product_tmpl_id
                        WHERE po.date_order >= '%s'
                        AND po.date_order <= '%s'
                        AND po.company_id = %s
                        GROUP BY product_name, pp.id
                        ORDER BY amount DESC LIMIT 5
                    """ % (s_date, e_date, company_id)
        self._cr.execute(sql_query)
        result_top_product = self._cr.dictfetchall()
        data_source = []
        count = 0
        for each in result_top_product:
            count += 1
            data_source.append(['<strong>' + str(count) + '</strong>', each.get('product_name'),
                                self.env.user.currency_id.symbol + ' ' + str("%.2f" % each.get('amount')),
                                each.get('total_qty')])
        return data_source

    @api.model
    def sales_based_on_hours(self, start, end, company_id):
        res_pos_order = {'total_sales': 0, 'total_orders': 0}
        if company_id:
            pass
        else:
            company_id = self.env.user.company_id.id
        current_time_zone = self.env.user.tz or 'UTC'
        s_date, e_date = start_end_date_global(start, end, current_time_zone)
        query = """SELECT extract(hour from po.date_order AT TIME ZONE 'UTC' AT TIME ZONE '%s') AS date_order_hour,
                    SUM(pol.price_subtotal_incl) AS price_total
                    FROM pos_order_line AS pol
                    LEFT JOIN pos_order po ON (po.id=pol.order_id)
                    WHERE po.date_order >= '%s'
                    AND po.date_order <= '%s'
                    AND po.company_id = %s
                    GROUP BY extract(hour from po.date_order AT TIME ZONE 'UTC' AT TIME ZONE '%s')
                    ORDER BY price_total DESC
                """ % (current_time_zone, s_date, e_date, company_id, current_time_zone)

        self._cr.execute(query)
        result_data_hour = self._cr.dictfetchall()
        count = 0
        top_hour_dict = {'top_hour': 0, 'amount': 0.0}
        if result_data_hour:
            for each in result_data_hour:
                if count == 0:
                    top_hour_dict.update(
                        {'top_hour': each.get('date_order_hour'), 'amount': each.get('price_total') or 0.0})
                    count += 1
                    break
        hour_lst = [hrs for hrs in range(0, 24)]
        for each in result_data_hour:
            if each['date_order_hour'] != 23:
                each['date_order_hour'] = [each['date_order_hour'], each['date_order_hour'] + 1]
            else:
                each['date_order_hour'] = [each['date_order_hour'], 0]
            hour_lst.remove(int(each['date_order_hour'][0]))
        for hrs in hour_lst:
            hr = []
            if hrs != 23:
                hr += [hrs, hrs + 1]
            else:
                hr += [hrs, 0]
            result_data_hour.append({'date_order_hour': hr, 'price_total': 0.0})
        sorted_hour_data = sorted(result_data_hour, key=lambda l: l['date_order_hour'][0])
        res_pos_order['sales_based_on_hours'] = sorted_hour_data
        return {'pos_order': res_pos_order, 'top_hour': top_hour_dict, 'currency': self.env.user.currency_id.symbol}

    @api.model
    def sales_based_on_current_month(self, start, end, company_id):
        if company_id:
            pass
        else:
            company_id = self.env.user.company_id.id
        current_time_zone = self.env.user.tz or 'UTC'
        s_date, e_date = start_end_date_global(start, end, current_time_zone)
        query = """SELECT 
                    extract(day from po.date_order AT TIME ZONE 'UTC' AT TIME ZONE '%s') AS order_day,
                    SUM(pol.price_subtotal_incl) AS price_total
                    FROM pos_order_line AS pol
                    INNER JOIN pos_order po ON (po.id=pol.order_id)
                    WHERE 
                    po.date_order >= '%s'
                    AND po.date_order <= '%s'
                    AND po.company_id = %s
                    GROUP BY order_day
                    ORDER BY extract(day from po.date_order AT TIME ZONE 'UTC' AT TIME ZONE '%s') ASC
                """ % (current_time_zone, s_date, e_date, company_id, current_time_zone)
        self._cr.execute(query)
        result_data_month = self._cr.dictfetchall()
        final_list = []
        for each in range(1, int(datetime.today().day) + 1):
            total = 0
            for each_1 in result_data_month:
                if each == int(each_1.get('order_day')):
                    total += each_1.get('price_total')
                    break
            final_list.append({'days': each, 'price': total or 0.0})
        return {'final_list': final_list, 'currency': self.env.user.currency_id.symbol}

    @api.model
    def sales_based_on_current_year(self, start, end, company_id):
        if company_id:
            pass
        else:
            company_id = self.env.user.company_id.id
        current_time_zone = self.env.user.tz or 'UTC'
        s_date, e_date = start_end_date_global(start, end, current_time_zone)
        query = """SELECT
                    extract(month from o.date_order AT TIME ZONE 'UTC' AT TIME ZONE '%s') AS order_month,
                    SUM(pol.price_subtotal_incl) AS price_total
                    FROM pos_order_line AS pol
                    INNER JOIN pos_order o ON (o.id=pol.order_id)
                    AND o.date_order >= '%s'
                    AND o.date_order <= '%s'
                    AND o.company_id = %s
                    GROUP BY  order_month
                    ORDER BY extract(month from o.date_order AT TIME ZONE 'UTC' AT TIME ZONE '%s') ASC
                """ % (current_time_zone, s_date, e_date, company_id, current_time_zone)
        self._cr.execute(query)
        data_year = self._cr.dictfetchall()
        final_list = []
        for each in range(1, int(datetime.today().month) + 1):
            total = 0
            for each_1 in data_year:
                if each == int(each_1.get('order_month')):
                    total += each_1.get('price_total')
                    break
            final_list.append({'order_month': each, 'price_total': total or 0.0})
        for each in final_list:
            each['order_month'] = calendar.month_abbr[int(each['order_month'])]
        return {'final_list': final_list, 'currency': self.env.user.currency_id.symbol}

    @api.model
    def get_the_top_customer(self, start, end, company_id):
        if company_id:
            pass
        else:
            company_id = self.env.user.company_id.id
        current_time_zone = self.env.user.tz or 'UTC'
        s_date, e_date = start_end_date_global(start, end, current_time_zone)
        sql_query = """SELECT 
                        SUM(pol.price_subtotal_incl) AS amount, 
                        cust.name AS customer,
                        SUM(pol.qty) AS total_product
                        FROM pos_order_line AS pol
                        INNER JOIN pos_order AS po ON po.id = pol.order_id
                        INNER JOIN res_partner AS cust ON cust.id = po.partner_id
                        WHERE po.date_order >= '%s'
                        AND po.date_order <= '%s'
                        AND po.company_id = %s
                        GROUP BY cust.name
                        ORDER BY amount DESC LIMIT 10
                    """ % (s_date, e_date, company_id)
        self._cr.execute(sql_query)
        top_customer = self._cr.dictfetchall()
        return {'top_customer': top_customer, 'currency': self.env.user.currency_id.symbol}

    @api.model
    def get_daily_gross_sales_data(self, filter_date, company_id):
        current_time_zone = self.env.user.tz or 'UTC'
        s_date, e_date = start_end_date_global(filter_date, filter_date, current_time_zone)
        sql_query = """SELECT extract(hour from po.date_order AT TIME ZONE 'UTC' AT TIME ZONE '%s') AS date_order_hour,
                        SUM(pol.price_subtotal_incl) AS price_total
                        FROM pos_order_line AS pol
                        INNER JOIN pos_order po ON (po.id=pol.order_id)
                        WHERE
                        po.date_order BETWEEN '%s' AND '%s'
                        AND po.company_id = %s
                        GROUP BY extract(hour from po.date_order AT TIME ZONE 'UTC' AT TIME ZONE '%s')
                    """ % (current_time_zone, s_date, e_date, company_id, current_time_zone)
        self._cr.execute(sql_query)
        result_data_hour = self._cr.dictfetchall()
        return result_data_hour

    @api.model
    def daily_gross_sales(self, start, end, company_id):
        res_pos_order = {}
        if company_id:
            pass
        else:
            company_id = self.env.user.company_id.id
        current_day_data = self.get_daily_gross_sales_data(start, company_id)
        last_current_day_data = self.get_daily_gross_sales_data(end, company_id)
        final_dict = {}
        final_list = []
        for each in current_day_data:
            final_dict[each['date_order_hour']] = {'today': each.get('price_total') or 0, 'last': 0}
        for each in last_current_day_data:
            if each.get('date_order_hour') in final_dict:
                final_dict[each['date_order_hour']].update({'last': each.get('price_total') or 0})
            else:
                final_dict[each['date_order_hour']] = {'today': 0, 'last': each.get('price_total') or 0}
        for key, val in final_dict.items():
            final_list.append({'date_order_hour': key, 'today': val.get('today'), 'last': val.get('last')})
        hour_lst = [hrs for hrs in range(0, 24)]
        for each in final_list:
            if each['date_order_hour'] != 23:
                each['date_order_hour'] = [each['date_order_hour'], each['date_order_hour'] + 1]
            else:
                each['date_order_hour'] = [each['date_order_hour'], 0]
            hour_lst.remove(int(each['date_order_hour'][0]))
        for hrs in hour_lst:
            hr = []
            if hrs != 23:
                hr += [hrs, hrs + 1]
            else:
                hr += [hrs, 0]
            final_list.append({'date_order_hour': hr, 'last': 0.0, 'today': 0.0})
        sorted_hour_data = sorted(final_list, key=lambda l: l['date_order_hour'][0])
        res_pos_order['sales_based_on_hours'] = sorted_hour_data
        return res_pos_order

    @api.model
    def weekly_gross_sales_data(self, start, end, company_id):
        current_time_zone = self.env.user.tz or 'UTC'
        start_date, end_date = start_end_date_global(start, end, current_time_zone)
        sql_query = """SELECT extract(day from o.date_order AT TIME ZONE 'UTC' AT TIME ZONE '%s') AS day_name,
                        to_char(o.date_order AT TIME ZONE 'UTC' AT TIME ZONE '%s','DY') AS day,
                        SUM(pos.price_subtotal_incl) AS sale_total
                        FROM pos_order_line AS pos
                        INNER JOIN pos_order AS o ON pos.order_id=o.id
                        INNER JOIN product_template AS prod ON pos.product_id=prod.id
                        AND o.date_order >= '%s'
                        AND o.date_order <= '%s'
                        AND o.company_id = %s
                        GROUP BY day_name, day;
                """ % (current_time_zone, current_time_zone, start_date, end_date, company_id)
        self._cr.execute(sql_query)
        return {'week_data': self._cr.dictfetchall()}

    @api.model
    def weekly_gross_sales(self, current_week_start_date, current_week_end_date, last_week_start_date,
                           last_week_end_date, company_id):
        if company_id:
            pass
        else:
            company_id = self.env.user.company_id.id
        current_week = self.weekly_gross_sales_data(current_week_start_date, current_week_end_date, company_id)
        last_week = self.weekly_gross_sales_data(last_week_start_date, last_week_end_date, company_id)
        final_dict = {}
        final_list = []
        for each in current_week['week_data']:
            final_dict[each['day']] = {'current_week': each.get('sale_total') or 0, 'last_week': 0}
        for each in last_week['week_data']:
            if each.get('day') in final_dict:
                final_dict[each['day']].update({'last_week': each.get('sale_total') or 0})
            else:
                final_dict[each['day']] = {'current_week': 0, 'last_week': each.get('sale_total') or 0}
        for key, val in final_dict.items():
            final_list.append({'day': key, 'current_week': val.get('current_week'), 'last_week': val.get('last_week')})
        final_data_list = []
        days = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']

        for each_day in days:
            this_week = 0.0
            last_week = 0.0
            for each in final_list:
                if each_day == each.get('day'):
                    this_week = each.get('current_week')
                    last_week = each.get('last_week')
            final_data_list.append({'day': each_day, 'current_week': this_week or 0.0, 'last_week': last_week or 0.0})
        return {'weekly_compare_sales': final_data_list}

    @api.model
    def customer_avg_spent_per_visit(self, start, end, company_id):
        if company_id:
            pass
        else:
            company_id = self.env.user.company_id.id
        current_time_zone = self.env.user.tz or 'UTC'
        start_date, end_date = start_end_date_global(start, end, current_time_zone)
        cust_data = self.env['pos.order'].search(
            [('date_order', '>=', start_date), ('date_order', '>=', end_date),
             ('company_id', '=', company_id)])
        total_amount = 0.0
        for eaach in cust_data:
            total_amount += eaach.amount_total
        return {'cust_avg_spent_per_visit': total_amount / 30 if total_amount else 0,
                'currency_icon': self.env.user.currency_id.symbol}

    @api.model
    def customer_avg_visit(self, company_id):
        if company_id:
            pass
        else:
            company_id = self.env.user.company_id.id
        sql_query = "SELECT COUNT(partner_id) AS customer FROM pos_order WHERE company_id = %s AND date_order > current_date - 30" % company_id
        self._cr.execute(sql_query)
        cust_data = self._cr.dictfetchall()
        cust_avg = cust_data[0]['customer'] / 30
        return {'cust_avg_visit': cust_avg if cust_avg else 0}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
