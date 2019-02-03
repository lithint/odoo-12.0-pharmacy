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
import ast

from odoo import models, api, fields, _
from datetime import datetime
from datetime import datetime, date, timedelta
from itertools import groupby
import copy
import barcode

from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def create(self, vals):
        res = super(ProductTemplate, self).create(vals)
        if res:
            param_obj = self.env['ir.config_parameter'].sudo()
            gen_barcode = param_obj.get_param('gen_barcode')
            barcode_selection = param_obj.get_param('barcode_selection')
            gen_internal_ref = param_obj.get_param('gen_internal_ref')

            if not vals.get('barcode') and gen_barcode:
                if barcode_selection == 'code_39':
                    barcode_code = barcode.codex.Code39(str(res.id) + datetime.now().strftime("%S%M%H%d%m%y"))
                if barcode_selection == 'code_128':
                    barcode_code = barcode.codex.Code39(str(res.id) + datetime.now().strftime("%S%M%H%d%m%y"))
                if barcode_selection == 'ean_13':
                    barcode_code = barcode.ean.EuropeanArticleNumber13(
                        str(res.id) + datetime.now().strftime("%S%M%H%d%m%y"))
                if barcode_selection == 'ean_8':
                    barcode_code = barcode.ean.EuropeanArticleNumber8(
                        str(res.id) + datetime.now().strftime("%S%M%H%d%m%y"))
                if barcode_selection == 'isbn_13':
                    barcode_code = barcode.isxn.InternationalStandardBookNumber13(
                        '978' + str(res.id) + datetime.now().strftime("%S%M%H%d%m%y"))
                if barcode_selection == 'isbn_10':
                    barcode_code = barcode.isxn.InternationalStandardBookNumber10(
                        str(res.id) + datetime.now().strftime("%S%M%H%d%m%y"))
                if barcode_selection == 'issn':
                    barcode_code = barcode.isxn.InternationalStandardSerialNumber(
                        str(res.id) + datetime.now().strftime("%S%M%H%d%m%y"))
                if barcode_selection == 'upca':
                    barcode_code = barcode.upc.UniversalProductCodeA(
                        str(res.id) + datetime.now().strftime("%S%M%H%d%m%y"))
                if barcode_selection == 'issn':
                    res.write({'barcode': barcode_code})
                else:
                    res.write({'barcode': barcode_code.get_fullcode()})
            # generate internal reference
            if not vals.get('default_code') and gen_internal_ref:
                res.write({'default_code': (str(res.id).zfill(6) + str(datetime.now().strftime("%S%M%H")))[:8]})
        return res

    @api.model
    def create_from_ui(self, product):
        if product.get('image'):
            product['image'] = product['image'].split(',')[1]
        id = product.get('id')
        if id:
            product_tmpl_id = self.env['product.product'].browse(id).product_tmpl_id
            if product_tmpl_id:
                product_tmpl_id.write(product)
        else:
            id = self.env['product.product'].create(product).id
        return id

    is_packaging = fields.Boolean("Is Packaging")
    loyalty_point = fields.Integer("Loyalty Point")
    is_dummy_product = fields.Boolean("Is Dummy Product")
    non_refundable = fields.Boolean(string="Non Refundable")
    return_valid_days = fields.Integer(string="Return Valid Days")


class ProductProduct(models.Model):
    _inherit = "product.product"

    near_expire = fields.Integer(string='Near Expire', compute='check_near_expiry')
    expired = fields.Integer(string='Expired', compute='check_expiry')

    def get_current_company(self):
        current_user = self.env.user.id
        user_id = self.env['res.users'].search([('id', '=', int(current_user))])
        return user_id.company_id.id

    def get_near_expiry(self):
        stock_production_lot_obj = self.env['stock.production.lot']
        if self.tracking != 'none':
            today_date = date.today()
            stock_lot = stock_production_lot_obj.search([('product_id', 'in', self.ids)])
            for each_stock_lot in stock_lot.filtered(lambda l: l.alert_date):
                alert_date = datetime.strptime(str(each_stock_lot.alert_date), '%Y-%m-%d %H:%M:%S').date()
                if each_stock_lot.life_date:
                    life_date = datetime.strptime(str(each_stock_lot.life_date), '%Y-%m-%d %H:%M:%S').date()
                    if life_date >= today_date:
                        stock_production_lot_obj |= each_stock_lot
        return stock_production_lot_obj

    def get_expiry(self):
        stock_production_lot_obj = self.env['stock.production.lot']
        if self.tracking != 'none':
            today_date = date.today()
            stock_lot = self.env['stock.production.lot'].search([('product_id', 'in', self.ids)])
            for each_stock_lot in stock_lot.filtered(lambda l: l.life_date):
                life_date = datetime.strptime(str(each_stock_lot.life_date), '%Y-%m-%d %H:%M:%S').date()
                if life_date <= today_date:
                    stock_production_lot_obj |= each_stock_lot
        return stock_production_lot_obj

    @api.one
    def check_near_expiry(self):
        stock_production_lot_obj = self.get_near_expiry()
        self.near_expire = len(stock_production_lot_obj)

    @api.one
    def check_expiry(self):
        stock_production_lot_obj = self.get_expiry()
        self.expired = len(stock_production_lot_obj)

    @api.multi
    def nearly_expired(self):
        stock_production_lot_obj = self.get_near_expiry()
        action = self.env.ref('stock.action_production_lot_form').read()[0]
        action['domain'] = [('id', 'in', [each_lot.id for each_lot in stock_production_lot_obj])]
        return action

    @api.multi
    def product_expired(self):
        stock_production_lot_obj = self.get_expiry()
        action = self.env.ref('stock.action_production_lot_form').read()[0]
        action['domain'] = [('id', 'in', [each_lot.id for each_lot in stock_production_lot_obj])]
        return action

    @api.model
    def category_expiry(self, company_id, from_pos_cate_id):
        data_list = []
        today_date = date.today()
        domain = [('tracking', '!=', 'none')]
        if from_pos_cate_id:
            domain += [('categ_id', '=', from_pos_cate_id)]
        product_expiry_detail = self.search(domain)
        if product_expiry_detail:
            for each_product in product_expiry_detail:
                quant_detail = self.env['stock.quant'].search([('product_id', '=', each_product.id),
                                                               ('lot_id.life_date', '!=', False),
                                                               ('state_check', '=', 'near_expired'),
                                                               ('company_id.id', '=', company_id)])
                for each_quant in quant_detail:
                    life_date = datetime.strptime(str(each_quant.lot_id.life_date), '%Y-%m-%d %H:%M:%S').date()
                    if not life_date < today_date:
                        if from_pos_cate_id:
                            data_list.append(each_quant.read()[0])
                        else:
                            data_list.append({'name': each_quant.product_id.name, 'qty': each_quant.quantity,
                                              'catid': each_quant.product_id.categ_id.id,
                                              'categ_name': each_quant.product_id.categ_id.name})
        return data_list

    @api.multi
    def category_expiry_data(self, company_id):
        sql = '''SELECT pt.name as name, sq.quantity as qty, pc.id as catid,pc.name as categ_name, spl.id as lot_id 
                FROM stock_quant sq
                LEFT JOIN stock_production_lot spl on spl.id = sq.lot_id
                LEFT JOIN product_product pp on pp.id = sq.product_id
                LEFT JOIN product_template pt on pt.id = pp.product_tmpl_id
                LEFT JOIN product_category pc on pc.id = pt.categ_id
                WHERE pt.tracking != 'none'
                AND spl.life_date is not NULL 
                AND sq.state_check = 'near_expired'
                AND sq.company_id = %s
                AND spl.life_date::Date >= current_date;
                        ''' % (company_id)
        self._cr.execute(sql)
        data_list = self._cr.dictfetchall()
        return data_list

    @api.model
    def search_product_expiry(self):
        today = datetime.today()
        today_end_date = datetime.strftime(today, "%Y-%m-%d 23:59:59")
        today_date = datetime.strftime(today, "%Y-%m-%d 00:00:00")
        company_id = self.get_current_company()
        categ_nearexpiry_data = self.category_expiry_data(company_id)
        location_obj = self.env['stock.location']
        location_detail = location_obj.get_location_detail(company_id)
        warehouse_detail = location_obj.get_warehouse_expiry_detail(company_id)

        exp_in_day = {}
        product_expiry_days_ids = self.env['product.expiry.config'].search([('active', '=', True)])
        if product_expiry_days_ids:
            for each in product_expiry_days_ids:
                exp_in_day[int(each.no_of_days)] = 0
        exp_in_day_detail = copy.deepcopy(exp_in_day)
        date_add = datetime.today() + timedelta(days=1)
        today_date_exp = datetime.strftime(date_add, "%Y-%m-%d 00:00:00")
        today_date_end_exp = datetime.strftime(date_add, "%Y-%m-%d 23:59:59")

        for exp_day in exp_in_day:
            product_id_list = []
            exp_date = datetime.today() + timedelta(days=exp_day)
            today_exp_date = datetime.strftime(exp_date, "%Y-%m-%d 23:59:59")
            if today_date_end_exp == today_exp_date:
                self._cr.execute("select sq.lot_id "
                                 "from stock_quant sq left join stock_production_lot spl on spl.id = sq.lot_id "
                                 "where spl.life_date >= '%s'" % today_date_exp + " and"
                                                                                  " spl.life_date <= '%s'" % today_exp_date + "and"
                                                                                                                              " sq.company_id = '%s'" % company_id + "group by sq.lot_id")
            else:
                self._cr.execute("select sq.lot_id "
                                 "from stock_quant sq left join stock_production_lot spl on spl.id = sq.lot_id "
                                 "where spl.life_date >= '%s'" % today_date + " and"
                                                                              " spl.life_date <= '%s'" % today_exp_date + "and"
                                                                                                                          " sq.company_id = '%s'" % company_id + "group by sq.lot_id")
            result = self._cr.fetchall()
            for each in result:
                for each_in in each:
                    product_id_list.append(each_in)
            product_config_color_id = self.env['product.expiry.config'].search(
                [('no_of_days', '=', exp_day), ('active', '=', True)], limit=1)
            exp_in_day_detail[exp_day] = {'product_id': product_id_list, 'color': product_config_color_id.block_color,
                                          'text_color': product_config_color_id.text_color}
            exp_in_day[exp_day] = len(result)
        category_list = copy.deepcopy(categ_nearexpiry_data)
        category_res = []
        key = lambda x: x['categ_name']
        for k, v in groupby(sorted(category_list, key=key), key=key):
            qty = 0
            stock_lot = []
            categ_id = False
            for each in v:
                qty += float(each['qty'])
                categ_id = each['catid']
                stock_lot.append(each['lot_id'])
            category_res.append({'categ_id': categ_id, 'categ_name': k, 'qty': qty, 'id': stock_lot})

        expire_product = self.env['stock.production.lot'].search([('state_check', '=', 'expired')])
        exp_in_day['expired'] = len(expire_product)
        list_near_expire = []
        quant_sql = '''SELECT sq.lot_id as lot_id
                        FROM stock_quant sq
                        LEFT JOIN stock_production_lot spl on spl.id = sq.lot_id
                        WHERE sq.state_check = 'near_expired'
                        AND sq.company_id = %s
                        AND spl.life_date >= '%s' 
                        AND spl.life_date <= '%s' 
                    ''' % (company_id, today_date, today_end_date)
        self._cr.execute(quant_sql)
        quant_detail = self._cr.dictfetchall()

        for each_quant in quant_detail:
            list_near_expire.append(each_quant.get('lot_id'))
        exp_in_day['day_wise_expire'] = exp_in_day_detail
        exp_in_day['near_expired'] = len(set(list_near_expire))
        exp_in_day['near_expire_display'] = list_near_expire
        exp_in_day['category_near_expire'] = category_res
        exp_in_day['location_wise_expire'] = location_detail
        exp_in_day['warehouse_wise_expire'] = warehouse_detail
        return exp_in_day

    @api.model
    def front_search_product_expiry(self):
        company_id = self.get_current_company()
        categ_nearexpiry_data = self.category_expiry(company_id, False)
        location_obj = self.env['stock.location']
        location_detail = location_obj.get_location_detail(company_id)
        warehouse_detail = location_obj.get_warehouse_expiry_detail(company_id)
        exp_in_day = {60: 0, 30: 0, 15: 0, 10: 0, 5: 0, 1: 0}
        for exp_day in exp_in_day:
            exp_date = datetime.today() + timedelta(days=exp_day)
            self._cr.execute("select sq.product_id, sq.lot_id, sq.company_id, sq.id "
                             "from stock_quant sq left join stock_production_lot spl on spl.id = sq.lot_id "
                             "where spl.life_date >= '%s'" % datetime.today().strftime("%Y-%m-%d %H:%M:%S") + " and"
                                                                                                              " spl.life_date <= '%s'" % exp_date + "and"
                                                                                                                                                    " sq.company_id = '%s'" % company_id + "group by "
                                                                                                                                                                                           "sq.product_id, sq.lot_id, sq.company_id, sq.id order by sq.product_id")
            result = self._cr.fetchall()
            exp_in_day[exp_day] = len(result)

        category_list = copy.deepcopy(categ_nearexpiry_data)
        category_res = []
        key = lambda x: x['categ_name']
        for k, v in groupby(sorted(category_list, key=key), key=key):
            qty = 0
            categ_id = False
            for each in v:
                qty += float(each['qty'])
                categ_id = each['catid']
            category_res.append({'categ_id': categ_id, 'categ_name': k, 'qty': qty})
        expire_product = self.env['stock.production.lot'].search([('state_check', '=', 'expired')])
        exp_in_day['expired'] = len(expire_product)
        list_near_expire = []
        quant_detail = self.env['stock.quant'].search(
            [('state_check', '=', 'near_expired'), ('company_id.id', '=', company_id)])
        for each_quant in quant_detail:
            list_near_expire.append(each_quant.lot_id.id)
        exp_in_day['near_expired'] = len(set(list_near_expire))
        exp_in_day['near_expire_display'] = list_near_expire
        exp_in_day['category_near_expire'] = category_res
        exp_in_day['location_wise_expire'] = location_detail
        exp_in_day['warehouse_wise_expire'] = warehouse_detail
        return exp_in_day

    @api.model
    def get_expire_data_near_by_day(self, company_id, exp_in_day):
        exp_date = datetime.today() + timedelta(days=exp_in_day)
        self._cr.execute("select sq.product_id, sq.lot_id, sq.company_id, sq.id "
                         "from stock_quant sq left join stock_production_lot spl on spl.id = sq.lot_id "
                         "where spl.life_date >= '%s'" % datetime.today().strftime("%Y-%m-%d %H:%M:%S") + " and"
                                                                                                          " spl.life_date <= '%s'" % exp_date + "and"
                                                                                                                                                " sq.company_id = '%s'" % company_id + "group by "
                                                                                                                                                                                       "sq.product_id, sq.lot_id, sq.company_id,sq.id order by sq.product_id")
        result = self._cr.fetchall()
        stock_q_obj = self.env['stock.quant']
        records = []
        if result:
            for stock_q_id in result:
                stock_rec = stock_q_obj.browse(stock_q_id[3])
                records.append(stock_rec.read()[0])
        return records

    @api.multi
    def graph_date(self, start, end):
        company_id = self.get_current_company()
        start_date = datetime.strptime(start, '%Y-%m-%d').date()
        new_start_date = datetime.strftime(start_date, "%Y-%m-%d %H:%M:%S")
        end_date = datetime.strptime(end, '%Y-%m-%d').date()
        new_end_date = datetime.strftime(end_date, "%Y-%m-%d 23:59:59")
        sql = '''SELECT pt.name as product_name, sum(sq.quantity) AS qty
                FROM stock_quant sq
                LEFT JOIN stock_production_lot spl on spl.id = sq.lot_id
                LEFT JOIN product_product AS pp ON pp.id = spl.product_id
                LEFT JOIN product_template AS pt ON pt.id = pp.product_tmpl_id
                WHERE sq.company_id = %s
                AND sq.state_check is NOT NULL
                AND pt.tracking != 'none'
                AND spl.life_date BETWEEN '%s' AND '%s'
                GROUP BY pt.name;
            ''' % (company_id, new_start_date, new_end_date)
        self._cr.execute(sql)
        data_res = self._cr.dictfetchall()
        return data_res

    @api.model
    def expiry_product_alert(self):
        email_notify_date = None
        notification_days = self.env['ir.config_parameter'].sudo().get_param('email_notification_days')
        if notification_days:
            email_notify_date = date.today() + timedelta(days=int(notification_days))
            start_email_notify_date = datetime.strftime(email_notify_date, "%Y-%m-%d %H:%M:%S")
            end_email_notify_date = datetime.strftime(email_notify_date, "%Y-%m-%d 23:59:59")

            res_user_ids = ast.literal_eval(
                self.env['ir.config_parameter'].sudo().get_param('res_user_ids'))

            SQL = """SELECT sl.name AS stock_location, pt.name AS Product,pp.id AS product_id, 
                            CAST(lot.life_date AS DATE),lot.name lot_number, sq.quantity AS Quantity
                            FROM stock_quant AS sq
                            INNER JOIN stock_production_lot AS lot ON lot.id = sq.lot_id 
                            INNER JOIN stock_location AS sl ON sl.id = sq.location_id
                            INNER JOIN product_product AS pp ON pp.id = lot.product_id
                            INNER JOIN product_template AS pt ON pt.id = pp.product_tmpl_id
                            WHERE sl.usage = 'internal' AND pt.tracking != 'none' AND 
                            lot.life_date BETWEEN '%s' AND '%s'
                        """ % (start_email_notify_date, end_email_notify_date)
            self._cr.execute(SQL)
            near_expiry_data_list = self._cr.dictfetchall()
            email_list = []
            template_id = self.env.ref('flexipharmacy.email_template_product_expiry_alert')
            res_user_ids = self.env['res.users'].browse(res_user_ids)
            email_list = [x.email for x in res_user_ids if x.email]
            email_list_1 = ', '.join(map(str, email_list))
            company_name = self.env['res.company']._company_default_get('your.module')
            if res_user_ids and template_id and near_expiry_data_list:
                # template_id.send_mail(int(near_expiry_data_list[0]['product_id']), force_send=True)
                template_id.with_context({'company': company_name, 'email_list': email_list_1, 'from_dis': True,
                                          'data_list': near_expiry_data_list}).send_mail(
                    int(near_expiry_data_list[0]['product_id']), force_send=True)
        return True

    @api.model
    def graph_date_on_canvas(self, start, end):
        company_id = self.get_current_company()
        graph_data_list = []
        domain = [('state_check', '!=', False), ('company_id.id', '=', company_id)]
        if start:
            domain += [('lot_id.life_date', '>=', start)]
        if end:
            domain += [('lot_id.life_date', '<=', end)]
        filter_date_record = self.env['stock.quant'].search(domain)
        for each_filter in filter_date_record.filtered(lambda l: l.quantity):
            graph_data_list.append({'product_name': each_filter.product_id.name, 'qty': each_filter.quantity})
        data_res = []
        key = lambda x: x['product_name']
        for k, v in groupby(sorted(graph_data_list, key=key), key=key):
            qty = 0
            for each in v:
                qty += float(each['qty'])
            data_res.append({'product_name': k, 'qty': qty})
        return data_res

    @api.model
    def create(self, vals):
        if vals.get('uom_id'):
            vals['uom_po_id'] = vals.get('uom_id')
        res = super(ProductProduct, self).create(vals)
        if res:
            param_obj = self.env['ir.config_parameter'].sudo()
            gen_barcode = param_obj.get_param('gen_barcode')
            barcode_selection = param_obj.get_param('barcode_selection')
            gen_internal_ref = param_obj.get_param('gen_internal_ref')

            if not vals.get('barcode') and gen_barcode:
                if barcode_selection == 'code_39':
                    barcode_code = barcode.codex.Code39(str(res.id) + datetime.now().strftime("%S%M%H%d%m%y"))
                if barcode_selection == 'code_128':
                    barcode_code = barcode.codex.Code39(str(res.id) + datetime.now().strftime("%S%M%H%d%m%y"))
                if barcode_selection == 'ean_13':
                    barcode_code = barcode.ean.EuropeanArticleNumber13(
                        str(res.id) + datetime.now().strftime("%S%M%H%d%m%y"))
                if barcode_selection == 'ean_8':
                    barcode_code = barcode.ean.EuropeanArticleNumber8(
                        str(res.id) + datetime.now().strftime("%S%M%H%d%m%y"))
                if barcode_selection == 'isbn_13':
                    barcode_code = barcode.isxn.InternationalStandardBookNumber13(
                        '978' + str(res.id) + datetime.now().strftime("%S%M%H%d%m%y"))
                if barcode_selection == 'isbn_10':
                    barcode_code = barcode.isxn.InternationalStandardBookNumber10(
                        str(res.id) + datetime.now().strftime("%S%M%H%d%m%y"))
                if barcode_selection == 'issn':
                    barcode_code = barcode.isxn.InternationalStandardSerialNumber(
                        str(res.id) + datetime.now().strftime("%S%M%H%d%m%y"))
                if barcode_selection == 'upca':
                    barcode_code = barcode.upc.UniversalProductCodeA(
                        str(res.id) + datetime.now().strftime("%S%M%H%d%m%y"))
                if barcode_selection == 'issn':
                    res.write({'barcode': barcode_code})
                else:
                    res.write({'barcode': barcode_code.get_fullcode()})
            # generate internal reference
            if not vals.get('default_code') and gen_internal_ref:
                res.write({'default_code': (str(res.id).zfill(6) + str(datetime.now().strftime("%S%M%H")))[:8]})
        return res

    @api.model
    def calculate_product(self, config_id):
        user_allowed_company_ids = self.env.user.company_ids.ids
        config = self.env['pos.config'].browse(config_id)
        product_ids = False
        setting = self.env['res.config.settings'].search([], order='id desc', limit=1, offset=0)
        pos_session = self.env['pos.session'].search([('config_id', '=', config.id), ('state', '=', 'opened')], limit=1)
        if pos_session and config.multi_shop_id and pos_session.shop_id:
            product_ids = pos_session.get_products_category_data(config_id)
            return product_ids
        else:
            if setting and setting.group_multi_company and not setting.company_share_product:
                product_ids = self.with_context({'location': config.stock_location_id.id}).search(
                    [('product_tmpl_id.sale_ok', '=', True), ('active', '=', True),
                     ('product_tmpl_id.active', '=', True),
                     '|', ('product_tmpl_id.company_id', 'in', user_allowed_company_ids),
                     ('product_tmpl_id.company_id', '=', False),
                     ('available_in_pos', '=', True)])
            else:
                product_ids = self.with_context({'location': config.stock_location_id.id}).search(
                    [('product_tmpl_id.sale_ok', '=', True), ('active', '=', True),
                     ('product_tmpl_id.active', '=', True),
                     ('available_in_pos', '=', True)])
        if product_ids:
            return product_ids.ids
        else:
            return []


class ProductExpiryConfig(models.Model):
    _name = "product.expiry.config"
    _description = "product expiry configuration"

    name = fields.Char(string="Name", compute="_change_name", store=True)
    no_of_days = fields.Char(string="Number Of Days")
    active = fields.Boolean(string="Active")
    block_color = fields.Char(string="Block Color")
    text_color = fields.Char(string="Text Color")

    @api.model
    def create(self, vals):
        if vals.get('no_of_days') and vals.get('no_of_days').isdigit():
            vals['name'] = 'Expire In ' + vals.get('no_of_days') + ' Days'
        else:
            raise ValidationError(_('Enter only number of days'))
        return super(ProductExpiryConfig, self).create(vals)

    @api.depends('no_of_days')
    def _change_name(self):
        for each in self:
            if each.no_of_days:
                each.name = 'Expire In ' + each.no_of_days + ' Days'


class product_category(models.Model):
    _inherit = "pos.category"

    loyalty_point = fields.Integer("Loyalty Point")
    return_valid_days = fields.Integer("Return Valid Days")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
